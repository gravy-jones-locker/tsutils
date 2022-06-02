"""
This module contains the abstract Source class for site-specific scraping 
configurations.
"""
from __future__ import annotations

import re

from ..common.datautils import update_defaults
from .scrapers import Requester, Driver, Scraper, APIRequester
from .utils.field import HTMLField, APIField
from .utils.response import Response

class BaseSource:
    """
    Interface for configuring source-specific scraping and data retrieval.

    This class is purely abstract. Concrete instances are supplied by the 
    Source, DriverSource and APISource subclasses.
    """
    # Any additional (non-default) scraper settings are passed here
    scraper_settings = {}

    # Fields for scraping can either be stored here or passed at runtime
    field_dict = {}
    
    def __init__(self) -> None:
        self._configure_scraper_settings()
        self.specificity = self._calculate_specificity()

        self.fields = self._compile_fields(self.field_dict)

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
        prefix = 'http(?:s)*://(?:www.)*'
        for patt in self.urls:
            if re.findall(prefix + patt, url, re.I):
                return True
        return False
    
    def scrape_url(self, url: str, ad_fields: dict, **kwargs) -> dict:
        """
        Call the URL given and extract available field data.
        :param url: the URL to call.
        :param ad_fields: any additional fields to retrieve.
        :param kwargs: bespoke request arguments.
        :return: a dictionary of values found for each field.
        """
        return self._extract_data(self.scraper.get(url, **kwargs), ad_fields)

    def _compile_fields(self, fields: dict) -> None:
        return [self._field_cls(k, v) for k, v in fields.items()]

    def _extract_data(self, resp: Response, ad_fields: dict) -> dict:
        out = {}
        if resp is not None:
            for field in [*self.fields, *self._compile_fields(ad_fields)]:
                out[field.name] = field.extract(resp)
        return out

    @property
    def scraper(self) -> Scraper:
        if self._scraper is False:
            self._scraper = self._scraper_cls.get_or_create(
                **self.scraper_settings)
        return self._scraper

    def _calculate_specificity(self) -> int:
        return max([len(x) for x in self.urls])

class HTMLSource(BaseSource):
    """
    HTMLSource objects correspond to navigable URLs which return structured HTML.
    """
    # The source is applied to all URLs matching these patterns
    urls = ['.*']

    _field_cls = HTMLField
    
class Source(HTMLSource):
    """
    The default Source object uses the Requester interface for making calls.
    """
    _scraper_cls = Requester

class DriverSource(HTMLSource):
    """
    DriverSource objects execute requests via the Selenium Webdriver interface.
    """
    _scraper_cls = Driver

class Endpoint(BaseSource):
    """
    Endpoint objects use the APIRequester interface for making calls and 
    APIField objects for data extraction.
    """
    _field_cls = APIField  # This is the only source with an alternate Field

    _scraper_cls = APIRequester

    base = ''

    def __init__(self) -> None:
        """
        Convert the endpoint base string into a URL and add to list.
        """
        self.urls = [self._convert_base()]
        self.keys = self._get_endpoint_keys()
        super().__init__()
    
    def _get_endpoint_keys(self) -> str:
        out = []
        for key in re.findall(r'{.*}', self.base):
            out.append(key.strip('{}'))
        return out

    def _convert_base(self) -> str:
        return re.sub('http(s)*://', '', re.sub(r'{.*?}', '.*', self.base))

    def _calculate_specificity(self) -> int:  # Ranks above any HTMLSource
        return 999 + super()._calculate_specificity()
    
    def call(self, **kwargs) -> dict:
        """
        Call the Endpoint with the given arguments.
        :return: a dictionary of values found for each field.
        """
        url = self.base  # Immutable --> copies by default
        for key in self.keys:
            url = url.format(**{key: kwargs.pop(key)})
        return self._extract_data(self.scraper.get(url, **kwargs), {})

class DualSource:
    """
    DualSource objects execute Driver-based scraping if Requester fails.
    """
    pass  # TODO implement - or not?