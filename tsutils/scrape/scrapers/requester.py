"""
This module contains the Requester class for making simple calls to online
resources. It adds useful scraping functionality to the underlying Requests
interface.
"""
from __future__ import annotations

import cloudscraper
import requests
import logging

from ..scrapers.scraper import Scraper
from ..models.response import Response
from ..models.hosts import Host

# Requester instances are shared between Sources wherever possible (i.e. when
# their settings match).
_instances = []

logger = logging.getLogger('tsutils')

class Requester(Scraper):
    """
    This class integrates concurrency, host/proxy rotation and other common
    scraping helpers into a quasi-Requests interface.
    """
    defaults = {
        **Scraper.defaults,
        "timeout": 5,
        "content_types": [
            'text/html'
        ],
        "use_session": False
    }

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
        if self._host is False:
            self._host = next(self._hosts)
        return self._host

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
        self._host = next(self._hosts)
    
class StaticRequester(Requester):
    """
    The StaticRequester interface is replica of the usual Requester
    class for sources which prefer a static connection.
    """
    defaults = {
        **Requester.defaults,
        "rotate_host": False,
    }

class DefensiveRequester(StaticRequester):
    """
    The DefensiveRequester interface is a subclass of the StaticRequester class
    for DefensiveSource objects which persist a Selenium session.
    """
    defaults = {
        **StaticRequester.defaults,
        "request_retries": 3,
    }

class APIRequester(StaticRequester):
    """
    The APIRequester interface is a subclass of the StaticRequester class for
    APISource objects.
    """
    defaults = {
        **StaticRequester.defaults,
        "content_types": [],
    }