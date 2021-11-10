"""
This module constitutes the high-level interface for centralising and 
(hopefully) simplifying scraping operations in the TS codebase.
"""
from __future__ import annotations

import logging
import time

from .host import Hosts
from .response import Response
from .scrapers.scraper import Scraper
from .scrapers.requester import Requester
from .scrapers.driver import Driver
from .exceptions import ClientSideError, RetryNeededError, RetriesExhaustedError
from ..common.exceptions import InvalidSettingError, SkipIterationError
from ..config import scrape as default_config

logger = logging.getLogger('tsutils')

class Session:
    """
    This class is the intended entry point for any scraping operation. It
    facilitates:
        - Intelligent client/server-side request error-handling
        - Automated rotation of client hosts (user-agent/proxy combinations)
        - Easy configuration of pageload flows etc.

    All actual requests are handled by the private _scraper attribute. This 
    corresponds either to an extended webdriver. Chrome instance or requests
    module depending on the value of the use_driver argument in the class
    constructor.

    Example Usage:
        >>> sess = Session()
        >>> resp = sess.get('http://google.com')
        [TIME DATE] ERROR: Clientside error; rotating host
        [TIME DATE] INFO: Request successful
        >>> print(resp)
        Response(status_code=200, content='...', error=None)
        ...
        >>> sess = Session(use_driver=True)
        >>> scrape_res = sess.iter_urls(urls, field_mapping)
        >>> print(scrape_res)
        [TIME DATE] INFO: Processing url 1/10
        [TIME DATE] INFO: All urls successfully processed
        {url1: {field1: value, field2: value, field3: value}, url2...}
    """

    def __init__(self, session_config: dict=None, scraper: Scraper=None, 
        use_driver: bool=False) -> None:
        """
        Configure connection details.
        :param session_config: a dictionary containing session settings.
            Available fields are:
                USER_AGENTS: list
                PROXIES: list
                HEADERS: dictionary
                COOKIES: dictionary
                HEADLESS: bool 
                POST_LOAD_WAIT: int
                ROTATE_SESSION_WAIT: int
                RETRIES: int
                CHROMEDRIVER_PATH: str
                CAPTCHA_TXT: list
            N.B. defaults for each of these are in tsutils/input/config/
            scrape.json - please check before overriding.
        :param scraper: a preconfigured scraper instance to use (or None).
        :param use_driver: toggles whether to use a Driver scraper instance.
        """
        self.config = default_config.copy()
        for key, value in session_config.items():
            if key not in default_config:
                raise InvalidSettingError(key, default_config)
            self.config[key] = value
        self.hosts = Hosts(self.config["PROXIES"], self.config["USER_AGENTS"])
        if scraper is not None:
            if not isinstance(scraper, Scraper):
                raise TypeError('scraper must be a Scraper class or None')
            self._scraper = scraper
        elif use_driver:
            self._scraper = Driver.from_session(self.config)
        else:
            self._scraper = Requester()

    def iter_urls(self, urls: list, fields: dict) -> dict:
        """
        Iterates over a list of urls and extracts the information specified in
        the fields dictionary.
        :param urls: the list of urls from which to fetch field data.
        :param fields: a dictionary of field spec indexed by field name. E.g.:
        ```
            {'author': {[
                {'xpath': '//div[@class="author"]/text()',
                 'patt': '\w+\s\w+'},
                {'xpath': '(//div[@class="info-pane"]/span)[2]/text()',
                 'patt': 'author: \w+\s\w+'}
                 ]},
            'publication_name': ...
            }
        ```
        :return dict: a dictionary of results indexed by url.
        """
        out = {}
        for url in urls:
            resp = self.get(url)
            for field_name, field_spec in fields.items():
                out[field_name] = resp.extract_data(**field_spec)
        return out

    class Router:
        """
        This class handles the flow of any scraping action and thereby 
        introduces all the core features of the Session class (retry, error 
        handling; automated host rotation).
        """
        @classmethod
        def route(router, fn):
            """
            Guide a scraping action through the execution pipeline.
            :param fn: the action to route.
            """
            def inner(sess: Session, *args, **scrape_params):
                sess._scraper._prime_session_request(sess.config)
                logger.debug(f'Executing {fn} with {", ".join(args)}')
                attempts = 0
                while sess.config["RETRIES"] - attempts >= 0:
                    attempts += 1
                    try:
                        return router.execute(fn, sess, *args)
                    except RetryNeededError as exc:
                        if isinstance(exc, ClientSideError):
                            sess._scraper._rotate_host()
                        continue
                    except SkipIterationError:
                        break
                raise RetriesExhaustedError('Request failed')
            return inner

        def execute(fn: function, session: Session, *args) -> Response:
            """
            Execute and inspect the action being routed.
            :param fn: the method corresponding to the action to carry out.
            :param session: the Session instance from which the action originates.
            """
            resp_raw = fn(session, *args)
            time.sleep(session.config["WAIT_PAGELOAD"])
            resp = session._scraper._compose_response(resp_raw)
            return resp
        
    ### The key (low-level) scraping methods all alias underlying scraper 
    ### methods. This exposes their decorated counterparts through a Session 
    ### instance.

    @Router.route
    def get(self, *args, **kwargs) -> Response:
        return self._scraper.get(*args, **kwargs)

    @Router.route
    def click(self, *args, **kwargs) -> Response:
        return self._scraper.click(*args, **kwargs)