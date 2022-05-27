"""
This module contains an extended ChromeDriver instance for programmatic control
of a desktop browser.
"""
from __future__ import annotations

import os
import shutil
import undetected_chromedriver as uc

from seleniumwire import webdriver as webdriver
from seleniumwire.request import Request
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
from typing import Union

from ...common.datautils import update_defaults
from ...common.exceptions import NotificationError
from .hosts import Host, LocalHost
from .response import Response
from ... import ROOT_DIR

DATA_DIR = f'{ROOT_DIR}/input/data/chrome'

class NoRequestError(NotificationError):
    pass

class Chrome:
    """
    This is the entry point for using the ChromeDriver/Selenium interface. Call
    Chrome.load to return either a WiredChrome or StealthChrome instance.
    """
    @classmethod
    def load(cls, stealth: bool=False, **settings) -> Chrome:
        """
        Configure and return a Selenium ChromeDriver instance.
        :param settings: override defaults by passing values here.
        :return: a fully configured Chrome instance.
        """
        if stealth:
            return StealthChrome(**settings)
        return WiredChrome(**settings)

class ExtendedChrome:
    """
    This is an abstract class which shares resources between the concrete 
    WiredChrome and StealthChrome classes.
    """
    defaults = {
        "headless": True,
        "chromedriver_path": None,
        "incognito": False,
        "page_load_timeout": 15,
        "host": None,
        "load_args": [
            '--log-level=2',
            '--no-first-run',
            '--no-service-autorun',
            '--disable-dev-shm-usage',
            '--window-size=1920,1080'
            ]}

    def __init__(self, **settings) -> None:
        """
        Compile settings then load ChromeDriver instance and set important
        settings.
        """
        self._settings = update_defaults(self.defaults, settings)
        if self._settings["incognito"]:
            self.reset()
        self._init_driver()
        self.set_page_load_timeout(self._settings["page_load_timeout"])
    
    def click_xpath(self, xpath: str) -> None:
        """
        Performs a click action on the element at the xpath given.
        :param xpath: an xpath statement.
        """
        self.execute_script(
            'arguments[0].click()',
            self.find_element(By.XPATH, xpath))
        
    def check_xpath(self, xpath: str) -> bool:
        """
        Checks whether an element at the xpath given is loaded.
        :param xpath: an xpath statement.
        :return: True if the element is present otherwise False.
        """
        try:
            self.find_element(By.XPATH, xpath)
            return True
        except NoSuchElementException:
            return False
    
    @classmethod
    def reset_profile(cls) -> None:
        """
        Deletes the contents of the Chrome configuration folder to remove any
        persistent data.
        """
        for f in os.listdir(DATA_DIR):
            if f != '.gitkeep':
                path = '/'.join([DATA_DIR, f])
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

    def _init_driver(self) -> None:
        chrome_cls = type(self).__bases__[-1]
        chrome_cls.__init__(self, **self._configure_init_kwargs())

    def _configure_init_kwargs(self) -> dict:
        out = {"options": self._configure_options()}
        if self._settings["chromedriver_path"] is not None:
            out["executable_path"] = self._settings["chromedriver_path"]
        return out
    
    def _configure_options(self) -> Union[webdriver.ChromeOptions,
    uc.ChromeOptions]:
        options = self._init_options()
        for arg in self._settings["load_args"]:
            options.add_argument(arg)
        if self._settings["headless"]:
            options.add_argument('--headless')
        if not self._settings["incognito"]:
            options.add_argument(self._get_user_data_dir())
        return options

class WiredChrome(ExtendedChrome, webdriver.Chrome):
    """
    This class integrates SeleniumWire request/response logic and host rotation
    into the generic Selenium interface.
    """
    def __init__(self, **settings) -> None:
        """
        Do usual construction + host configuration.
        """
        super().__init__(**settings)
        self._configure_host(self._settings["host"])
        self.request_interceptor = self._intercept_requests

    def compose_response(self) -> Response:
        """
        Build a response object out of the window/request contents.
        :return: a tsutils.scraper.utils.Response object.
        """
        try:
            return Response._from_chrome(
                self._get_main_request(),
                self.get_cookies())
        except NoRequestError:
            return Response._from_details(status_code=404, url=self.current_url)
        
    def _intercept_requests(self, request: Request) -> None:
        if self.host.user_agent is not None:
            del request.headers["User-Agent"]
            request.headers["User-Agent"] = self.host.user_agent
    
    def _configure_host(self, host: Host=None) -> None:
        if host is None:
            host = LocalHost()
        self.proxy = host.proxy_dict
        self.host  = host
    
    def _get_main_request(self) -> Request:
        for request in self.requests:
            if request.url == self.current_url:
                return request
        raise NoRequestError(f'No requests could be made to {self.current_url}')
    
    def _init_options(self) -> webdriver.ChromeOptions:
        return webdriver.ChromeOptions()

    def _get_user_data_dir(self) -> str:
        return f'user-data-dir={DATA_DIR}'

class StealthChrome(ExtendedChrome, uc.Chrome):
    """
    This class facilitates stealth browsing using the undetected_chromedriver
    patch.
    """
    def compose_response(self) -> Response:
        """
        Build a response object out of the window/request contents.
        :return: a tsutils.scraper.utils.Response object.
        """
        return Response._from_chrome_src(
            self.page_source,
            self.get_cookies(),
            url=self.current_url)

    def _init_options(self) -> uc.ChromeOptions:
        return uc.ChromeOptions()

    def _get_user_data_dir(self) -> str:
        return f'--user-data-dir={DATA_DIR}'