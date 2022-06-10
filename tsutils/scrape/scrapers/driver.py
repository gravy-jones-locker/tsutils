"""
This module contains the Driver interface for browser-based scraping.

It unifies the advantages of Selenium scraping (lower detection rates; page 
interactivity) with the Response/Request, object-based logic of typical scraping
flows.
"""
from __future__ import annotations

import time
import logging

from typing import Callable
from selenium.webdriver.common.by import By
from datetime import datetime as dt

from .scraper import Scraper
from ..models.response import Response as Response
from ..utils.chrome import Chrome
from ..utils.functions import compare_urls, is_url
from ..exceptions import *

logger = logging.getLogger('tsutils')

# This variable keeps track of live driver instances to prevent multiple from
# running (or trying to run...) at once.
_instances = []

class Driver(Scraper):
    """
    The Driver class integrates proxy/header rotation etc. into the browser
    actions exposed by the Chrome/WebDriver class.
    """
    defaults = {
        **Scraper.defaults,
        "headless": True,  # The top five are Chrome defaults
        "incognito": False,
        "ignore_images": True,
        "ignore_scripts": False,
        "chrome_version": 102,
        "load_timeout": 30,
        "load_retries": 3,
        "post_load_wait": 1,
        "request_retries": 3,
        "request_retry_interval": 1
    }
    class Decorators:
    
        @classmethod
        def execute_request(decs, func: Callable) -> Callable:
            """
            Wrap the given function in retry/loading logic and return Response.
            """
            def inner(driver, *args, wait_xpath: str=None, **kwargs) -> Response:

                start_url = driver._chrome.current_url  # Store for validation
                tstamp = dt.now()

                func(driver, *args, **kwargs)

                # Extract a target URL from the function args - if available
                url = args[0] if is_url(args[0]) else None
                driver._do_loading(start_url, url, wait_xpath, tstamp)

                return driver._chrome.compose_response()
            return inner

    def __init__(self, **settings) -> None:
        """
        Start the driver instance with all the configured settings.
        :param settings: override DEFAULTs by passing values here.
        """
        super().__init__(**settings)
        self._chrome = Chrome(**self._settings, host=next(self._hosts))

    @classmethod
    def get_or_create(cls, **settings) -> Driver:
        """
        Return an existing Driver instance or create a new one.
        :param settings: the settings to be passed to the driver.
        :return a live driver instance.
        """
        global _instances

        if len(_instances) == 0:
            _instances.append(cls(**settings))

        driver = _instances[0]  # Take the first live instance

        if not all([v == driver._settings[k] for k, v in settings.items()]):
            # True if the settings passed do not match those of the live driver
            raise LiveDriverError('Cannot start mismatched Driver instance')

        return driver

    @Scraper.Decorators.handle_response
    @Decorators.execute_request
    def get(self, url: str, wait_xpath: str=None) -> Response:
        """
        Retrieve data at url and return Response. 
        """
        self._chrome.get(url)
    
    @Scraper.Decorators.handle_response
    @Decorators.execute_request
    def click_xpath(self, xpath: str, wait_xpath: str=None) -> Response:
        """
        Click xpath and return Response.
        """
        self._chrome.click_xpath(xpath)
    
    def quit(self) -> None:
        """
        Send quit signal to underlying Chrome instance.
        """
        self._chrome.quit()
        global _instances

        if self in _instances:
            _instances.remove(self)

    def restart(self) -> None:
        """
        Close and restart the underlying browser instance in case of critical 
        disconnects.
        """
        self._chrome.quit()
        self._chrome = Chrome(self._settings)
    
    def reset_profile(self) -> None:
        """
        Remove any persistent Chrome data.
        """
        self._chrome.reset_profile()

    def _do_loading(self, start_url: str, url: str, wait_xpath: str, 
    tstamp: dt) -> None:
        """
        Execute loading checks continuously until either they all pass or
        retries are exhausted.
        """
        attempts = 0  # Keep loading attempts below retries value

        while attempts - 1 < self._settings["load_retries"]:
            time.sleep(self._settings["post_load_wait"])

            resp = getattr(self._chrome._get_main_request(), 'response', None)

            if resp and not self._check_new_response(tstamp, resp):
                logger.debug('Request not executed yet')
            elif self._dismiss_alert():
                logger.debug('Dismissed alert')
            elif url and not self._loaded_url(start_url, url, resp):
                logger.debug(f'URL did not load')
            elif wait_xpath and not self._chrome.check_xpath(wait_xpath):
                logger.debug(f'Xpath not found ({wait_xpath})')
            else:  # True if all the checks pass
                logger.debug('Loading checks all passed. Returning')
                return  

            logger.debug('Page not loaded. Retrying')
            attempts += 1

        # If all attempts fail then raise PageLoadFailedError
        raise PageLoadFailedError('Page failed to load')
    
    def _check_new_response(self, tstamp: dt, resp: Response) -> bool:
        if resp is None:
            return False
        return tstamp < resp.date

    def _dismiss_alert(self) -> bool:
        if not self._chrome.find_elements(By.NAME, 'alert'):
            return False
        self._chrome.switch_to.alert.accept()
        return True
    
    def _loaded_url(self, start_url: str, url: str,
    resp: Response) -> bool:
        """
        Check whether there has been an expected change in URL (ideal); no 
        change and no redirect (failure) or an unexpected change (hard to track 
        - accepted).
        """
        current_url = self._chrome.current_url

        if compare_urls(current_url, url):
            return True  # True if on the desired URL
        redirect = 299 < resp.status_code < 400
        if compare_urls(start_url, current_url) and not redirect:
            return False  # True if no change and no redirect

        logger.debug('Driver URL has changed but could not be verified')

        return True  # True if change to some unexpected page
    
    def _rotate_host(self) -> None:
        self._chrome._configure_host(next(self._hosts), del_data=True)

class DefensiveDriver(Driver):
    """
    DefensiveDriver is a subclass of the main Driver interface for opening 
    sessions with sites that have aggressive anti-scraping measures.
    """
    defaults = {
        **Driver.defaults,
        "ignore_scripts": True,
        "request_retries": 5,
        "post_load_wait": 5,
        "incognito": True,
        "proxy_type": "static",
    }