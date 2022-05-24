"""
This module contains the abstract Scraper class for interaction with target 
scraping sites by the Driver and Requester subclasses. 
"""
import logging
import time

from typing import Callable

from ...common.datautils import update_defaults
from ..utils.response import Response
from ..utils.hosts import Hosts
from ..exceptions import *

logger = logging.getLogger('tsutils')

class Scraper:
    """
    A Scraper instance is an interface through which individual calls are made 
    and responses parsed then returned.
    """
    DEFAULTS = {
        "request_retries": 0,
        "request_retry_interval": 1,
        "rotate_host": False
    }
    class Decorators:
    
        @classmethod
        def handle_response(decs, func: Callable) -> Callable:
            """
            Wrap the given function in response/error parsing logic and return 
            output.
            """
            def inner(scraper, *args, **kwargs) -> Response:
                iteration = 0
                while iteration - 1 < scraper._settings["request_retries"]:
                    try:
                        resp = func(scraper, *args, **kwargs)
                        return scraper._parse_response(resp)
                    except Exception as e:
                        scraper._handle_error(e, iteration)
                    time.sleep(scraper._settings["request_retry_interval"])
                    iteration += 1
            return inner

    def __init__(self, proxy_file: str=None, **settings) -> None:
        self._hosts = Hosts(proxy_file)
        self._settings = update_defaults(self.DEFAULTS, settings)
    
    @Decorators.handle_response
    def get(self, url: str, *args, **kwargs) -> Response:
        raise NotImplementedError

    def _parse_response(self, resp: Response) -> Response:
        if resp.status_code == 404:
            raise ResourceNotFoundError(resp.url)
        # TODO might want to be able to handle redirect handling - need concrete
        # use case.
        if resp.captchaed:
            resp = self._solve_captcha(resp)
            if resp.captchaed:
                raise CaptchaHitError(resp)
        if not resp.ok:
            raise RequestFailedError(resp)
        return resp
    
    def _handle_error(self, exc: Exception, iteration: int) -> None:
        if self._settings["rotate_host"]:
            self._rotate_host()
        if iteration == self._settings["request_retries"]:
            raise exc