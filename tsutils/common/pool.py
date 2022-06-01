"""
This module contains an interface for executing tasks with optional threading/
logging settings. 
"""
from __future__ import annotations

import logging
import os

from typing import Callable, Any, Union
from bdb import BdbQuit
from threading import Lock
from concurrent.futures import Executor, ThreadPoolExecutor
from concurrent.futures import wait, FIRST_COMPLETED

from ..common.exceptions import StopPoolExecutionError

logger = logging.getLogger('tsutils')

class Pool:
    """
    Iterates over function/iterable pairs with standardised logging.
    """
    def __init__(self, num_threads: int=1, log_step: int=10, 
    raise_errs: bool=True, stop_early: bool=False) -> None:
        """
        :param num_threads: if 1 multi-threading is not used.
        :param log_step: the interval at which to log progress messages.
        :param raise_errs: raise errors as they arise (vs. just logging)
        :param stop_early: stop after one successful execution.
        """
        self.num_threads = self._configure_num_threads(num_threads)
        self.log_step = log_step
        self.raise_errs = raise_errs
        self.stop_early = stop_early

        # Tasks are **always** executed from this list
        self.tasks = []

        # Whenever shared resources are edited this lock must be invoked
        self.lock = Lock()
    
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
    
    def _do_sequential_execution(self) -> Any:
        out = []
        for (func, args, kwargs) in self.tasks:
            res, minor_exc = self._handle_task(func, *args, **kwargs)
            if self.stop_early and minor_exc is None:
                return res  # True if there were no errors at all
            if not self.stop_early:
                out.append(res)
            if self._check_for_poolstopper([res]):
                break
        return out  # True when all the tasks are completed

    def _handle_task(self, func: Callable, *args, **kwargs) -> tuple:
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
        if self.raise_errs:
            return True
        if self.stop_early and self.tasks_completed + 1 == self.tasks_total:
            return True
        if isinstance(exc, KeyboardInterrupt):
            return True
        if isinstance(exc, BdbQuit):
            return True
        return False

    def _check_for_poolstopper(self, results: list) -> bool:
        for res in results:
            if isinstance(getattr(res, 'exc', None), StopPoolExecutionError):
                return True
        return False

    def _do_parallel_execution(self) -> Any:
        with ThreadPoolExecutor(self.num_threads) as executor:
            futures = self._configure_threads(executor)
            try:
                out = []
                while futures:
                    done, futures = self._parse_completing_threads(futures)
                    if self.stop_early and done[1] is None:
                        return done[0]  # Returns result of a successful thread
                    if not self.stop_early and self._check_for_poolstopper(out):
                        break
                    out.extend(done)
                return out  # Returns a list of outputs
            finally:
                self._terminate_threads(futures)

    def _configure_threads(self, executor: Executor) -> list:
        out = []
        for (func, args, kwargs) in self.tasks:
            f = executor.submit(self._handle_task, func, *args, **kwargs)
            out.append(f)
        return out

    def _parse_completing_threads(self, futures: list) -> Any:
        done, futures = wait(futures, return_when=FIRST_COMPLETED)
        for f in done:
            if f.exception() is not None:
                raise f.exception()  # Only True if a **stopping* exception
            res, minor_exc = f.result()
            if self.stop_early and minor_exc is None:
                break  # True if a thread succesfully executed
        if self.stop_early:
            return (res, minor_exc), futures
        return [x.result()[0] for x in done], futures
    
    def _terminate_threads(self, futures: list) -> None:
        for waiting in futures:
            waiting.cancel()

    def _log_error(self, exc) -> None:
        if not self.stop_early and not self.raise_errs:
            logger.info(f'{exc} raised while processing item')
            logger.debug('Check traceback', exc_info=1)
    
    def _log_progress(self) -> None:
        if self.log_step == 0:
            return  # True if logging Un-configured
        if self.tasks_completed % self.log_step == 0:
            logger.info(f'Processing #{self.tasks_completed}/{self.tasks_total}')