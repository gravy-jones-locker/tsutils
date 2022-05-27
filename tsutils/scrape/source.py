"""
This module contains the abstract Source class for site-specific scraping 
configurations.
"""
from __future__ import annotations

import re

from ..common.datautils import update_defaults
from .scrapers import Requester, Driver, Scraper

class BaseSource:
    """
    Source objects are passed to Session objects for site-specific scraping 
    configurations.
    """
    # The source is applied to all URLs matching these patterns
    urls = ['.*']

    # Any additional (non-default) scraper settings are passed here
    scraper_settings = {}

    def __init__(self) -> None:
        self._configure_scraper_settings()
        self.specificity = self.calculate_specificity()

        # Only initialise Scraper class on demand
        self._scraper = False
    
    def _configure_scraper_settings(self) -> None:
        self.scraper_settings = update_defaults(
            self._scraper_cls.defaults, 
            self.scraper_settings
            )
    
    def match_url(self, url: str) -> bool:
        """
        Indicate whether a URL matches the patterns specified for this source.
        :param url: the URL to process.
        :return: True if the URL is a match otherwise False.
        """
        for patt in self.urls:
            if patt == '*':
                return True
            if re.findall(patt, url, re.I):
                return True
        return False
    
    @property
    def scraper(self) -> Scraper:
        if self._scraper is False:
            self._scraper = self._scraper_cls(**self.scraper_settings)
        return self._scraper
    
    def calculate_specificity(self) -> int:
        return max([len(x) for x in self.urls])
    
class Source(BaseSource):
    """
    The default Source object uses the Requester interface for making calls.
    """
    _scraper_cls = Requester

class DriverSource(BaseSource):
    """
    DriverSource objects execute requests via the Selenium Webdriver interface.
    """
    _scraper_cls = Driver

class DualSource:
    """
    DualSource objects execute Driver-based scraping if Requester fails.
    """
    pass  # TODO implement - or not?