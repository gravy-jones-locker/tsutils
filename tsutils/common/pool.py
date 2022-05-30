"""
This module contains an interface for executing tasks with optional threading/
logging settings. 
"""
from __future__ import annotations

import logging
import os

from typing import Callable, Any, Union
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, Future, wait, FIRST_COMPLETED

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
        if os.environ["TSUTILS_DEBUG"]:
            return 1
        return num_threads
    
    @classmethod
    def configure(cls, application: str, settings: dict) -> Pool:
        """
        Return an initialised Pool instance for the relevant application.
        :param application: one of 'requests'/...
        :param settings: a dictionary containing Pool-relevant settings.
        """
        if application == 'requests':
            return cls._configure_for_requests(settings)

    @classmethod
    def _configure_for_requests(cls, settings: dict) -> Pool:
        return cls(
            num_threads=settings["num_threads"],
            stop_early=True,
            raise_errs=False,
            log_step=0)
    
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
        self._set_counters()
        if self.num_threads == 1:
            return self._do_sequential_execution()
        return self._do_parallel_execution()

    def _set_counters(self) -> None:
        self.tasks_completed = 0
        self.tasks_total = len(self.tasks)

    def _do_sequential_execution(self) -> Union[list, Any]:
        """
        Carry out sequential execution (i.e. single-threaded) of the tasks in
        self.tasks.
        """
        out = []
        for (func, args, kwargs) in self.tasks:
            res, exc = self._handle_task(func, *args, **kwargs)
            if self.stop_early and exc is None:
                return res
            out.append(res)
        if self.stop_early:
            raise exc
        return out

    def _handle_task(self, func: Callable, *args, **kwargs) -> tuple:
        try:
            return func(*args, **kwargs), None
        except Exception as e:
            self._log_error()
            if self.raise_errs:
                raise e
            return None, e
        finally:  # Add done counter and log progress in any case
            with self.lock:
                self.tasks_completed += 1
            self._log_progress()

    def _do_parallel_execution(self) -> list:
        """
        Carry out parallel execution of the tasks in self.tasks.
        """
        with ThreadPoolExecutor(self.num_threads) as executor:
            futures = self._configure_threads(executor)
            if self.stop_early:
                return self._parse_completing_threads(futures)
        return [x.result()[0] for x in futures]

    def _configure_threads(self, executor: ThreadPoolExecutor) -> list:
        out = []
        for (func, args, kwargs) in self.tasks:
            f = executor.submit(self._handle_task, func, *args, **kwargs)
            f.add_done_callback(self._process_done_thread)
            out.append(f)
        return out
    
    def _parse_completing_threads(self, futures: list) -> Any:
        while self.tasks_completed != self.tasks_total:
            done, not_done = wait(futures, return_when=FIRST_COMPLETED)
            for f in done:
                res, exc = f.result()
                if exc is not None:
                    continue
                self._terminate_threads(not_done)
                return res
        raise exc

    def __enter__(self) -> Pool:
        return self
    def __exit__(self, *args, **kwargs) -> None:
        return

    def _terminate_threads(self, not_done: list) -> None:
        for waiting in not_done:
            waiting.cancel()
    
    def _process_done_thread(self, future: Future):
        if future.exception() and self.raise_errs:
            raise future.exception()
        
    def _log_error(self) -> None:
        logger.debug('Error raised while processing item', exc_info=1)
    
    def _log_progress(self) -> None:
        if self.log_step == 0:
            return  # True if logging Un-configured
        if self.tasks_completed % self.log_step == 0:
            logger.info(f'Processing #{self.tasks_completed}/{self.tasks_total}')