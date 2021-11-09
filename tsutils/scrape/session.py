import logging
import time

from .host import Hosts
from .response import Response
from .scrapers.scraper import Scraper
from .scrapers.requester import Requester
from .scrapers.driver import Driver
from .exceptions import ClientSideError, RetryNeededError, RetriesExhaustedError
from ..common.exceptions import SkipIterationError, InvalidSettingError
from ..config import scrape as default_config

logger = logging.getLogger('tsutils')

class Session:

    def __init__(self, session_config: dict, scraper: Scraper=None, 
        use_driver: bool=False) -> None:
        """
        Configure connection details.
        :param proxies: a list of proxies through which to rotate if necessary.
        :param cookies: a dictionary of cookie key/value pairs to configure.
        :param headers: a dictionary of header key/value pairs to configure.
        :param session_config: a dictionary of other session settings. 
        :param scraper: a preconfigured scraper instance to use (or None).
        :param use_driver: toggles whether to use a Driver scraper instance.
        """
        self.config = self._process_config(session_config)
        self.scraper = self._configure_scraper(scraper, use_driver)
        self.hosts = Hosts(self.config["PROXIES"], self.config["USER_AGENTS"])
        
    def _configure_scraper(self, scraper: Scraper, use_driver: bool) -> Scraper:
        if scraper is None:
            if use_driver:
                return Driver(self.config["HEADLESS"],
                              self.config["CHROMEDRIVER_PATH"])
            else:
                return Requester()
        elif not isinstance(scraper, Scraper):
            raise TypeError('scraper must be a Scraper class or None')
        return scraper

    @staticmethod
    def _process_config(session_config: dict) -> dict:
        out = default_config.copy()
        for key, value in session_config.items():
            if key not in default_config:
                raise InvalidSettingError(key, default_config)
            out[key] = value
        return out

    @classmethod
    def _route_request(cls, fn):
        def inner(scraper, *args, **scrape_params):
            scraper._prime_request()
            logger.debug(f'Executing {fn} with {", ".join(args)}')
            attempts = 0
            while scraper.config["RETRIES"] - attempts >= 0:
                attempts += 1
                try:
                    resp_raw = fn(scraper, *args)
                    time.sleep(scraper.config["WAIT_PAGELOAD"])
                    resp = scraper._compose_response(resp_raw)
                    if resp.error is not None:
                        raise resp.error.exception
                    return resp
                except RetryNeededError as exc:
                    if isinstance(exc, ClientSideError):
                        scraper._rotate_host()
                    continue
                except SkipIterationError:
                    break
            raise RetriesExhaustedError('Request failed')
        return inner

    def _rotate_host(self):
        self.hosts.rotate()
        self.headers['User-Agent'] = self.hosts.current_host.user_agent
        self.proxy = self.hosts.current_host.proxy
        time.sleep(self.config["ROTATE_SESSION_WAIT"])

    def _prime_request() -> None:
        """Required for configuring immediately pre-request settings"""
        raise NotImplementedError
    def _compose_response(out) -> Response:
        """Required for building a Response object after making a request"""
        raise NotImplementedError