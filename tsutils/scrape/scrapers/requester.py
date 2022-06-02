"""
This module contains the Requester class for making simple calls to online
resources. It adds useful scraping functionality to the underlying Requests
interface.
"""
from __future__ import annotations

import cloudscraper
import requests

from typing import Callable

from ..scrapers.scraper import Scraper
from ..models.response import Response
from ..models.hosts import Host
from ...common.pool import Pool

# Requester instances are shared between Sources wherever possible (i.e. when
# their settings match).
_instances = []

class Requester(Scraper):
    """
    This class integrates concurrency, host/proxy rotation and other common
    scraping helpers into a quasi-Requests interface.
    """
    defaults = {
        **Scraper.defaults,
        "num_threads": 3,
        "timeout": 5,
        "prongs": 3,
        "spin_hosts": True,
        "content_types": [
            'text/html'
        ],
        "use_session": False
    }
    class Decorators:
        
        @classmethod
        def thread_request(decs, func: Callable) -> Callable:
            """
            Execute the given request with appropriate threading.
            """
            def inner(requester, *args, **kwargs) -> Response:
                with requester._configure_pool() as pool:
                    prongs = requester._settings["prongs"]
                    if not requester._settings["spin_hosts"]:
                        prongs = 1
                    for _ in range(prongs):
                        pool.submit(func, requester, *args, **kwargs)
                    return pool.execute()
            return inner

    def __init__(self, **settings) -> None:
        """
        Do usual construction and bind private '_sess' attribute.
        """
        super().__init__(**settings)
        self._sess = False
        self._host = False

    @classmethod
    def get_or_create(cls, **settings) -> Requester:
        """
        Return an existing Requester instance or create a new one.
        :param settings: the settings to be passed to the requester.
        :return a live requester instance.
        """
        global _instances

        for rqstr in _instances:
            if rqstr._settings == settings:
                return rqstr
        _instances.append(cls(**settings))
        return _instances[-1]  # Return the instance that was just created

    @property
    def sess(self) -> cloudscraper.CloudScraper:
        """
        Return either the persisted Session or a one-off CloudScraper instance.
        """
        if not self._settings["use_session"]:
            with cloudscraper.create_scraper() as sess:
                return sess
        if not self._sess:
            self._sess = cloudscraper.create_scraper()
        return self._sess

    @property
    def host(self) -> Host:
        if self._settings["spin_hosts"] or self._host is False:
            self._host = next(self._hosts)
        return self._host

    @Decorators.thread_request
    @Scraper.Decorators.handle_response
    def get(self, url: str, **kwargs) -> Response:
        """
        Execute a GET request to the given URL and return a Response object.
        :param url: the URL from which to retrieve a response.
        :param kwargs: any combination of kwargs compatible with `requests.get`.
        :return: the Response object returned from the URL.
        """
        kwargs = self._get_kwargs(self.host, kwargs)
        try:  # SSLErrors are sometimes raised when using CloudScraper
            resp = self.sess.get(url, **kwargs)
        except requests.exceptions.SSLError:
            resp = requests.get(url, verify=False, **kwargs)
        return Response._from_requester(resp)
    
    def _get_kwargs(self, host: Host, user_kwargs: dict) -> dict:
        return {
        "headers": self._get_headers(user_kwargs.pop('headers', {}), host),
        "proxies": self._get_proxies(user_kwargs.pop('proxies', {}), host),
        "timeout": self._settings["timeout"],
        "stream": True,
        **user_kwargs}

    def _get_headers(self, user_headers: dict, host: Host) -> None:
        return {
            "User-Agent": host.user_agent, 
            **self._settings["headers"],
            **user_headers
            }
    
    def _get_proxies(self, user_proxies: dict, host: Host) -> None:
        return {**host.proxy_dict, **user_proxies}
    
    def _rotate_host(self) -> None:
        if self._settings["spin_hosts"]:
            return
        self._host = next(self._hosts)
    
    def _configure_pool(self) -> Pool:
        return Pool(
            num_threads=self._settings["num_threads"],
            stop_early=True,
            raise_errs=False,
            log_step=0)

class APIRequester(Requester):
    """
    The APIRequester interface is a replica of the usual Requester class with
    different presets/defaults.
    """
    defaults = {
        **Requester.defaults,
        "num_threads": 1,
        "rotate_host": False,
        "spin_hosts": False,
        "content_types": [],
        "prongs": 1
    }