"""
This module contains the abstract Scraper class for interaction with target 
scraping sites by the Driver and Requester subclasses. 
"""
import logging
import time

from typing import Callable
from requests.exceptions import Timeout

from ...common.datautils import update_defaults
from ..models.response import Response
from ..models.hosts import Hosts
from ..exceptions import *
from ..utils.constants import CAPTCHA_STRS

logger = logging.getLogger('tsutils')

CATCH_EXCEPTIONS = (
    RequestFailedError, 
    Timeout,
    *PROXY_EXCEPTIONS,
    )

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
        "headers": {},
    }
    class Decorators:
    
        @classmethod
        def handle_response(decs, func: Callable) -> Callable:
            """
            Wrap the given function in response/error parsing logic and return 
            output.
            """
            def inner(scraper, url, *args, **kwargs) -> Response:
                it = 0
                while True:
                    try:
                        resp = func(scraper, url, *args, **kwargs)
                        return scraper._parse_response(resp)
                    except Exception as exc:
                        it = scraper._handle_error(exc, url, it)
                        time.sleep(scraper._settings["request_retry_interval"])
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
        """
        Parse the response for errors - if None found then return.
        """
        if self._detect_captcha(resp):
            logger.debug(f'Hit captcha on {resp.url}')
            raise CaptchaHitError(f'Captcha hit on {resp.url}')

        if resp.status_code == 404:
            logger.debug(f'404 raised at {resp.url}')
            raise ResourceNotFoundError(resp.url)

        if not resp.ok:
            logger.debug(f'{resp.status_code} raised at {resp.url}')
            raise RequestFailedError(resp.msg)

        return resp

    def _detect_captcha(self, resp: Response) -> bool:
        """
        Look for captcha strings in the response text.
        """
        captchas = CAPTCHA_STRS + self._settings["captcha_strs"]
        if any([x in resp.text for x in captchas]):
            return True
        return False
    
    def _handle_error(self, exc: Exception, url: str, it: int) -> int:
        """
        Handle any errors raised during a scraping action and return the
        number of iteration 'tokens' left.
        """
        if isinstance(exc, ResourceNotFoundError):
            raise exc

        if self._stop_scraping(exc, it):
            logger.debug('Raising ScrapeFailedError', exc_info=1)
            raise ScrapeFailedError(f'All requests to {url} failed') from exc

        if isinstance(exc, PROXY_EXCEPTIONS):
            # Give proxy connection errors a bit of time to resolve
            logger.debug(f'Proxy error connecting to {url}')
            time.sleep(self._settings["request_retry_interval"])

            return it + 1  # These errors only use up one iteration token...

        if self._settings["rotate_host"]:
            logger.debug('Rotating host')
            self._rotate_host()
        
        return it + 2  # All other errors use up two iteration tokens
    
    def _stop_scraping(self, exc: Exception, it: int) -> bool:
        """
        Return True if an Exception has been raised which should stop scraping.
        """
        if it >= self._settings["request_retries"] * 2:
            return True
        if not isinstance(exc, CATCH_EXCEPTIONS):
            return True
        return False