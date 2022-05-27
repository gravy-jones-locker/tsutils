"""
This module contains the Driver interface for browser-based scraping.

It unifies the advantages of Selenium scraping (lower detection rates; page 
interactivity) with the Response/Request, object-based logic of typical scraping
flows.
"""
from __future__ import annotations

import time
import logging

from selenium.webdriver.common.by import By
from typing import Callable

from .scraper import Scraper
from ..utils.response import Response as Response
from ..utils.chrome import Chrome
from ..exceptions import *

logger = logging.getLogger('tsutils')

class Driver(Scraper):
    """
    The Driver class integrates proxy/header rotation etc. into the browser
    actions exposed by the Chrome/WebDriver class.
    """
    defaults = {
        **Scraper.defaults,
        "headless": True,  # The top three are Chrome defaults
        "chromedriver_path": None,
        "incognito": False,
        "stealth": False,
        "load_timeout": 15,
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
            def inner(driver, *args, wait_xpath: str=None, load_secs: int=None,
            **kwargs) -> Response:
                func(driver, *args, **kwargs)
                driver._do_loading(wait_xpath, load_secs)
                return driver._chrome.compose_response()
            return inner

    def __init__(self, **settings) -> None:
        """
        Start the driver instance with all the configured settings.
        :param proxy_file: the path to a list of proxy values.
        :param settings: override DEFAULTs by passing values here.
        """
        super().__init__(**settings)
        self._chrome = Chrome.load(**self._settings, host=next(self._hosts))

    @Scraper.Decorators.handle_response
    @Decorators.execute_request
    def get(self, url: str, wait_xpath: str=None, 
    load_secs: int=None) -> Response:
        """
        Retrieve data at url and return Response. 
        """
        self._chrome.get(url)
    
    @Scraper.Decorators.handle_response
    @Decorators.execute_request
    def click_xpath(self, xpath: str, wait_xpath: str=None, 
    load_secs: int=None) -> Response:
        """
        Click xpath and return Response.
        """
        self._chrome.click_xpath(xpath)
    
    def quit(self) -> None:
        """
        Send quit signal to underlying Chrome instance.
        """
        self._chrome.quit()
    
    def reset_profile(self) -> None:
        """
        Remove any persistent Chrome data.
        """
        self._chrome.reset_profile()

    def _do_loading(self, wait_xpath: str=None, load_secs: int=None) -> None:
        attempts = 0
        while attempts < self._settings["load_retries"]:
            if load_secs is None:
                load_secs = self._settings["post_load_wait"]
            time.sleep(load_secs)
            if self._verify_loaded(wait_xpath):
                return
            attempts += 1
        raise PageLoadFailedError

    def _rotate_host(self) -> None:
        self._chrome.configure_host(next(self._hosts))
    
    def _restart(self):  # In case of critical webdriver disconnects
        self._chrome.quit()
        self._chrome = Chrome(self._settings)
    
    def _verify_loaded(self, wait_xpath: str) -> bool:
        if self._dismiss_alert():
            return False  # True if a popup was dismissed
        if wait_xpath is None:
            return True
        return self._chrome.check_xpath(wait_xpath)
    
    def _dismiss_alert(self) -> bool:
        if not self._chrome.find_elements(By.NAME, 'alert'):
            return False
        self._chrome.switch_to.alert.accept()
        return True
    
    def _rotate_host(self) -> None:
        self._chrome.configure_host(next(self._hosts))

    def _solve_captcha(self, resp: Response) -> Response:
        if not self._settings["headless"]:
            return resp  # True if not possible to solve the captcha
        logger.info('CAPTCHA HIT - please solve. Hit any key when done')
        input()
        logger.info('Loading....')
        self._do_loading()
        return self._chrome.compose_response()