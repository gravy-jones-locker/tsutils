"""
This module contains an interface for executing tasks with optional threading/
logging settings. 
"""
from __future__ import annotations

import logging
import os

from typing import Callable, Any, Union
from threading import Lock
from concurrent.futures import Executor, ThreadPoolExecutor, Future, wait
from concurrent.futures import FIRST_COMPLETED

from ..common.exceptions import StopPoolExecutionError, STOP_EXCEPTIONS

logger = logging.getLogger('tsutils')

class Pool:
    """
    Iterates over function/iterable pairs with standardised logging.
    """
    def __init__(self, num_threads: int=1, log_step: int=10, 
    raise_errs: bool=True) -> None:
        """
        Bind configuration attrs and initialise empty .tasks/.lock values.
        """
        self.num_threads = self._configure_num_threads(num_threads)
        self.log_step = log_step
        self.raise_errs = raise_errs

        # Tasks are **always** executed from this list
        self.tasks = []

        # Whenever shared resources are edited this lock must be invoked
        self.lock = Lock()
    
    @classmethod
    def setup(self, num_threads: int=1, log_step: int=10, raise_errs: bool=True,
    stop_early: bool=False) -> Union[RunThreadsPool, StopEarlyPool]:
        """
        :param num_threads: if 1 multi-threading is not used.
        :param log_step: the interval at which to log progress messages.
        :param raise_errs: raise errors as they arise (vs. just logging)
        :param stop_early: stop after one successful execution.
        """
        pool_cls = RunThreadsPool  # Run threads by default
        if stop_early:
            pool_cls = StopEarlyPool
        return pool_cls(num_threads, log_step, raise_errs)
    
    def _configure_num_threads(self, num_threads: int) -> int:
        if os.environ["TSUTILS_DEBUG"] == 'True':
            return 1
        return num_threads

    def __enter__(self) -> Pool:  # Allow use as a context manager
        return self
    def __exit__(self, *args, **kwargs) -> None:
        return
    
    def submit(self, func, *args, **kwargs) -> None:
        """
        Add a job to the list of tasks to be executed.
        :param func: the function to apply to the given arguments.
        """
        self.tasks.append((func, args, kwargs))
    
    def map(self, func: Callable, arg_ls: list) -> Union[list, Any]:
        """
        Map the given function to the iterables passed.
        :param func: the function to map.
        :param arg_ls: a list of arguments to provide for each execution.
        :return: list of outputs OR an individual output (as per .stop_early).
        """
        for args in arg_ls:
            self.submit(func, *args)
        return self.execute()
    
    def execute(self) -> Any:
        """
        Execute the tasks in self.tasks with the preset configuration.
        :return: the output of the given function.
        """
        # These are used to record progress and track completed threads
        self.tasks_completed = 0
        self.tasks_total = len(self.tasks)

        if self.num_threads == 1:
            return self._do_sequential_execution()
        return self._do_parallel_execution()

    def _handle_task(self, func: Callable, *args, **kwargs) -> tuple:
        """
        Execute the given function. If an error is raised then EITHER raise it
        (if .raise_errs is True; if in STOP_EXCEPTIONS) or log and return.

        :return: a tuple containing the function output (or None) and the 
        Exception raised (or None).
        """
        try:
            return func(*args, **kwargs), None
        except Exception as exc:
            if self._is_stopping_exception(exc):
                raise exc
            self._log_error(exc)
            return None, exc
        finally:  # Add done counter and log progress in any case
            with self.lock:
                self.tasks_completed += 1
            self._log_progress()

    def _is_stopping_exception(self, exc) -> bool:
        """
        Return True if an Exception raised in _handle_task should cause
        execution to stop.
        """
        if self.raise_errs:
            return True
        if isinstance(exc, STOP_EXCEPTIONS):
            return True
        return False

    def _check_for_poolstopper(self, results: list) -> bool:
        for res in results:
            if isinstance(getattr(res, 'exc', None), StopPoolExecutionError):
                return True
        return False

    def _do_parallel_execution(self) -> Any:
        """
        Configure threads and pass output processing to subclasses. If a
        stopping exception occurs it will be raised by this function.
        """
        with ThreadPoolExecutor(self.num_threads) as executor:
            futures = self._configure_threads(executor)
            try:
                return self._get_threaded_output(futures)
            finally:
                self._terminate_threads(futures, executor)
    
    def _parse_completing_threads(self, futures: list) -> tuple:
        """
        Yield thread results and remaining futures as they arise
        """
        results = []
        done, not_done = wait(futures, return_when=FIRST_COMPLETED)
        for f in done:
            if f.exception():
                raise f.exception()
            results.append(f.result())
        return results, not_done

    def _configure_threads(self, executor: Executor) -> list:
        out = []
        for (func, args, kwargs) in self.tasks:
            f = executor.submit(self._handle_task, func, *args, **kwargs)
            out.append(f)
        return out
    
    def _terminate_threads(self, futures: list, 
    executor: ThreadPoolExecutor) -> None:
        for waiting in futures:
            waiting.cancel()
        executor.shutdown(wait=True)

    def _log_progress(self) -> None:
        if self.log_step == 0:
            return  # True if logging Un-configured
        if self.tasks_completed % self.log_step == 0:
            logger.info(f'Processing #{self.tasks_completed}/{self.tasks_total}')

class RunThreadsPool(Pool):
    """
    RunThreadsPool waits for all the running threads to execute before returning
    the results as a list.
    """
    def _do_sequential_execution(self) -> Any:
        out = []
        for (func, args, kwargs) in self.tasks:
            res, _ = self._handle_task(func, *args, **kwargs)
            out.append(res)
            if self._check_for_poolstopper([res]):
                break
        return out  # True when all the tasks are completed
    
    def _get_threaded_output(self, futures: list) -> list:
        """
        Compile completed threads into a list of results.
        """
        out = []
        while futures:
            done, futures = self._parse_completing_threads(futures)
            for res, _ in done:
                out.append(res)
        return out

    def _log_error(self, exc) -> None:
        logger.error(exc)
        logger.debug('Check traceback', exc_info=1)

class StopEarlyPool(Pool):
    """
    StopeEarlyPool waits for the first successfully executed thread and returns
    the result. In case none are successful it raises the most recent error.
    """
    def _do_sequential_execution(self) -> Any:
        for (func, args, kwargs) in self.tasks:
            res, minor_exc = self._handle_task(func, *args, **kwargs)
            if minor_exc is None:
                return res  # True if there were no errors at all
            if self._check_for_poolstopper([res]):
                return
    
    def _get_threaded_output(self, futures: list) -> Any:
        """
        Return the first successfully completed thread.
        """
        while futures:
            done, futures = self._parse_completing_threads(futures)
            for res, minor_exc in done:
                if minor_exc is not None:
                    continue
                return res
        raise minor_exc

    def _is_stopping_exception(self, exc) -> bool:
        """
        Add condition to usual stopping_exception criteria: stop and raise if
        the task currently being executed is the last in the pool.
        """
        if super()._is_stopping_exception(exc):
            return True
        if self.tasks_completed + 1 == self.tasks_total:
            return True
        return False

    def _log_error(self, exc) -> None:
        pass  # Errors are raised at the end of execution - don't log here