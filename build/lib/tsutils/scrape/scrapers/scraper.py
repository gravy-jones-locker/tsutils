"""
This module contains the abstract Scraper class for interaction with target 
scraping sites by the Driver and Requester subclasses. 
"""
import logging
import time

from typing import Callable
from bdb import BdbQuit

from ...common.datautils import update_defaults
from ..models.response import Response
from ..models.hosts import Hosts
from ..exceptions import *
from ..utils.constants import CAPTCHA_STRS

logger = logging.getLogger('tsutils')

class Scraper:
    """
    A Scraper instance is an interface through which individual calls are made 
    and responses parsed then returned.
    """
    defaults = {
        "proxy_file": None,
        "proxy_type": "all",
        "captcha_strs": [],
        "request_retries": 1,
        "request_retry_interval": 1,
        "rotate_host": True,
        "headers": {}
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

    def __init__(self, **settings) -> None:
        self._settings = update_defaults(self.defaults, settings)
        self._hosts = Hosts(
            self._settings["proxy_file"], 
            self._settings["proxy_type"])
    
    @Decorators.handle_response
    def get(self, url: str, *args, **kwargs) -> Response:
        raise NotImplementedError

    def _parse_response(self, resp: Response) -> Response:
        if resp.status_code == 404:
            raise ResourceNotFoundError(resp.url)

        # TODO might want to be able to do redirect handling - need concrete
        # use case.
        if self._detect_captcha(resp):
            resp = self._solve_captcha(resp)
            if self._detect_captcha(resp):
                raise CaptchaHitError(resp.url)

        if not resp.ok:
            raise RequestFailedError(resp.msg)
        return resp
    
    def _handle_error(self, exc: Exception, iteration: int) -> None:
        if isinstance(exc, (KeyboardInterrupt, BdbQuit, ResourceNotFoundError)):
            raise exc
        if self._settings["rotate_host"]:
            logger.debug(f'Rotating host ({exc})')
            self._rotate_host()
        if iteration == self._settings["request_retries"]:
            raise exc

    def _detect_captcha(self, resp: Response) -> bool:
        captchas = CAPTCHA_STRS + self._settings["captcha_strs"]
        if any([x in resp.text for x in captchas]):
            return True
        return False