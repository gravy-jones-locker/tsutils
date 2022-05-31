"""
This module contains an interface for executing tasks with optional threading/
logging settings. 
"""
from __future__ import annotations

import logging
import os

from typing import Callable, Any, Union
from threading import Lock
from concurrent.futures import Executor, ThreadPoolExecutor, Future
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

        try:
            if self.num_threads == 1:
                return self._do_sequential_execution()
            return self._do_parallel_execution()
        except KeyboardInterrupt:
            self._terminate_threads()
    
    def _do_sequential_execution(self) -> Any:
        out = []
        for (func, args, kwargs) in self.tasks:
            res, exc = self._handle_task(func, *args, **kwargs)
            if exc is None and self.stop_early:
                return res
            out.append(res)
            if self._check_for_poolstopper(res):
                break
        if self.stop_early:  # True if all attempts failed
            raise exc
        return out
    
    def _do_parallel_execution(self) -> Any:
        with ThreadPoolExecutor(self.num_threads) as executor:
            futures = self._configure_threads(executor)
            while futures:
                out, futures = self._parse_completing_threads(futures)
                if self._stop_execution(out):
                    self._terminate_threads(futures)
                    break
            return out

    def _configure_threads(self, executor: Executor) -> list:
        out = []
        for (func, args, kwargs) in self.tasks:
            f = executor.submit(self._handle_task, func, *args, **kwargs)
            f.add_done_callback(self._process_done_thread)
            out.append(f)
        return out

    def _handle_task(self, func: Callable, *args, **kwargs) -> tuple:
        try:
            return func(*args, **kwargs), None
        except Exception as exc:
            self._log_error(exc)
            if self.raise_errs or isinstance(exc, KeyboardInterrupt):
                raise exc
            return None, exc
        finally:  # Add done counter and log progress in any case
            with self.lock:
                self.tasks_completed += 1
            self._log_progress()
    
    def _parse_completing_threads(self, futures: list) -> Any:
        done, futures = wait(futures, return_when=FIRST_COMPLETED)
        if self.stop_early:
            for f in done:
                if f.exception() is not None:
                    continue
                return f.result()[0], futures
            return None, futures
        return [x.result()[0] for x in done], futures
    
    def _stop_execution(self, out: Any) -> bool:
        if self.stop_early:
            return out is not None
        for res in out:
            if self._check_for_poolstopper(res):
                return True
        return False
    
    def _check_for_poolstopper(self, res: Any) -> bool:
        return isinstance(getattr(res, 'exc', None), StopPoolExecutionError)

    def _terminate_threads(self, futures: list) -> None:
        for waiting in futures:
            waiting.cancel()
    
    def _process_done_thread(self, future: Future):
        exc = future.exception()
        if exc is None:
            return
        if self.raise_errs:
            raise exc
        if self.stop_early and self.tasks_completed == self.tasks_total:
            raise exc
        
    def _log_error(self, exc: Exception) -> None:
        logger.info(f'{exc} raised while processing item')
        logger.debug('See traceback', exc_info=1)
    
    def _log_progress(self) -> None:
        if self.log_step == 0:
            return  # True if logging Un-configured
        if self.tasks_completed % self.log_step == 0:
            logger.info(f'Processing #{self.tasks_completed}/{self.tasks_total}')