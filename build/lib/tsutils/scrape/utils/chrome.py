"""
This module contains an extended ChromeDriver instance for programmatic control
of a desktop browser.
"""
from __future__ import annotations

import os
import shutil

from seleniumwire import undetected_chromedriver as uc
from seleniumwire.request import Request
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *

from ...common.datautils import update_defaults
from ...common.exceptions import NotificationError
from ..models.hosts import Host, LocalHost
from ..models.response import Response
from .constants import IMG_EXTENSIONS
from ... import ROOT_DIR

DATA_DIR = f'{ROOT_DIR}/input/data/chrome'

class NoRequestError(NotificationError):
    pass

class Chrome(uc.Chrome):
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
        "ignore_images": True,
        "ignore_scripts": False,
        "load_args": [
            '--log-level=2',
            '--no-first-run',
            '--no-service-autorun',
            '--disable-dev-shm-usage',
            '--window-size=1280,1024'
            ]}

    def __init__(self, **settings) -> None:
        """
        Compile settings then load ChromeDriver instance and set important
        settings.
        """
        self._settings = update_defaults(self.defaults, settings)
        self._init_driver()
        self._configure_host(settings.get('host', self._settings["host"]))
        self.request_interceptor = self._intercept_requests

    def _init_driver(self) -> None:
        chrome_cls = type(self).__bases__[-1]
        chrome_cls.__init__(self, **self._configure_init_kwargs())

    def _configure_init_kwargs(self) -> dict:
        out = {"options": self._configure_options()}
        if self._settings["chromedriver_path"] is not None:
            out["executable_path"] = self._settings["chromedriver_path"]
        return out
    
    def _configure_options(self) -> uc.ChromeOptions:
        options = uc.ChromeOptions()
        for arg in self._settings["load_args"]:
            options.add_argument(arg)
        if self._settings["headless"]:
            options.add_argument('--headless')
        if not self._settings["incognito"]:
            options.add_argument(f'--user-data-dir={DATA_DIR}')
        return options

    def _intercept_requests(self, request: Request) -> None:
        if self._ban_request(request):
            request.abort()
        elif self.host.user_agent is not None:
            del request.headers["User-Agent"]
            request.headers["User-Agent"] = self.host.user_agent
    
    def _ban_request(self, request: Request) -> bool:
        if self._settings["ignore_images"]:
            if request.path.endswith(tuple(IMG_EXTENSIONS)):
                return True
        if self._settings["ignore_scripts"]:
            if request.path.endswith('js'):
                return True
        return False
    
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
        
    def _configure_host(self, host: Host=None, del_data: bool=False) -> None:
        if host is None:
            host = LocalHost()
        self.proxy = host.proxy_dict_prefixed
        self.host  = host
        if del_data:
            self._delete_session_data()
    
    def _delete_session_data(self) -> None:
        self.delete_all_cookies()
    
    def _get_main_request(self) -> Request:
        for request in self.requests:
            if self.current_url.startswith(request.url):
                return request
        raise NoRequestError(f'No requests could be made to {self.current_url}')
    
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