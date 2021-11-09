"""
This module contains an extended webdriver.Chrome subclass. The main extension
features are abbreviated configuration/methods and integration into the unified
tsutils interface (e.g. tsutils.scrape.response.Response objects).
"""

import logging

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from seleniumwire.request import Request

from ..host import Host
from ..response import Response

logger = logging.getLogger('tsutils')

class Driver(webdriver.Chrome):
    """
    An extended seleniumwire webdriver.Chrome instance for programmatic 
    interaction with dynamic webpages.
    """
    def __init__(self, headless: bool=True, chromedriver_path: str=None) -> None:
        """
        Starts webdriver instance with config specified.
        :param headless: toggles whether to use a headless driver.
        :param chromedriver_path: specifies a non-PATH chromedriver location.
        """
        if chromedriver_path is None:
            super().__init__(options=self._configure_options(headless))
        else: 
            # Handles chromedriver binaries which are not in PATH
            super().__init__(options=self._configure_options(headless),
                             executable_path=self.config["CHROMEDRIVER_PATH"])
        self.request_interceptor = self._interceptor
        
    def find_xpath(self, xpath: str) -> WebElement:
        """Abbreviates base find_element(By.Xpath, ...) method"""
        return self.find_element(By.XPATH, xpath)

    def _configure_options(self, headless: bool) -> webdriver.ChromeOptions:
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('headless')
        for arg in ['log-level=3', 'no-sandbox', 'disable-dev-shm-usage']:
            options.add_argument(arg)
        return options

    def _interceptor(self, request: Request) -> None:
        for key, value in self.headers.items():
            del request.headers[key]  # Has to be deleted first
            request.headers[key] = value

    def _prime_session_request(self, headers: dict, cookies: dict, 
        host: Host) -> None:
        self.headers.update(headers)
        for key, cookie in cookies.items():
            self.add_cookie({"name": key, **cookie})
        self.proxy, self.headers['User-Agent'] = host.proxy, host.user_agent