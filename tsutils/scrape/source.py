"""
This module contains the abstract Source class for site-specific scraping 
configurations.
"""
from __future__ import annotations

import re
import logging

from bdb import BdbQuit

from ..common.datautils import update_defaults
from .scrapers import Requester, Driver, Scraper, APIRequester
from .exceptions import StopScrapeError
from .models.field import HTMLField, APIField
from .models.response import Response

logger = logging.getLogger('tsutils')

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

    def _calculate_specificity(self) -> int:
        return max([len(x) for x in self.url_patts])

    def _compile_fields(self, fields: dict) -> None:
        return [self._field_cls(k, v) for k, v in fields.items()]
    
    def match_url(self, url: str) -> bool:
        """
        Indicate whether a URL matches the patterns specified for this source.
        :param url: the URL to process.
        :return: True if the URL is a match otherwise False.
        """
        prefix = 'http(?:s)*://(?:www.)*.*'
        for patt in self.url_patts:
            if re.findall(prefix + patt, url, re.I):
                return True
        return False
    
    def scrape_url(self, url: str, ad_fields: dict, **kwargs) -> Result:
        """
        Call the URL given and extract available field data.
        :param url: the URL to call.
        :param ad_fields: any additional fields to retrieve.
        :param kwargs: bespoke request arguments.
        :return: a Result object compiled from the scrape.
        """
        return self._parse_response(self.scraper.get(url, **kwargs), ad_fields)

    @property
    def scraper(self) -> Scraper:
        if self._scraper is False:
            self._scraper = self._scraper_cls.get_or_create(
                **self.scraper_settings)
        return self._scraper
    
    def _parse_response(self, resp: Response, ad_fields: dict) -> Result:
        values = {}
        if resp is not None:
            for field in [*self.fields, *self._compile_fields(ad_fields)]:
                values[field.name] = field.extract(resp)
        res = self.Result(values, resp)
        return self._execute_callback(res)

    def _execute_callback(self, result: Result) -> Result:
        try:
            result = self.done_callback(result)
            if self.end_scrape(result):
                raise StopScrapeError('No further results available')
        except Exception as exc:
            result.exc = exc
        finally:  # Return the output in any case
            return result
    
    def done_callback(self, result: Result) -> Result:
        """
        This is an extensible function for scrape post-processing.
        :param result: the Result object returned from the initial scrape.
        :return: a corresponding Result object after post-processing.
        """
        # !!! Post-processing logic goes here !!!
        return result
    
    def end_scrape(self, result: Result) -> bool:
        """
        This is an extensible function for conditional scrape stopping.
        :param result: the Result object returned from scraping.
        :return: True if scraping should be stopped otherwise False.
        """
        return False

    class Result:
        """
        Result objects are returned from individual scraping operations. They 
        expose the available data for maximum post-processing flexibility.
        """
        def __init__(self, values: dict, resp: Response) -> None:
            """
            Bind the values extracted during the scraping process and the 
            underlying Response object.
            """
            self.values = values
            self.resp = resp

            # Set default exception value as False
            self.exc = False

class HTMLSource(BaseSource):
    """
    HTMLSource objects correspond to navigable URLs which return structured HTML.
    """
    # The source is applied to all URLs matching these patterns
    url_patts = ['.*']

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
        self.url_patts = [self._convert_base()]
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
    
    def call(self, **kwargs) -> BaseSource.Result:
        """
        Call the Endpoint with the given arguments.
        :return: a Result object compiled from the API call.
        """
        url = self.base  # Immutable --> copies by default
        for key in self.keys:
            url = url.format(**{key: kwargs.pop(key)})
        return self.scrape_url(url, **kwargs)

class DefensiveSource(Source):
    """
    DefensiveSource objects initiate a session using Selenium interfaces and 
    subsequently attempt to scrape via a Requester object.

    Limited retries aim to optimise request/output payoff.
    """
    _live_session = False

    _driver = False

    guided_initialisation = False

    def __init__(self) -> None:
        super().__init__()

        self.scraper_settings.update(  # These are needed to hold a session open
            {"rotate_host": False,
             "spin_hosts": False,
             "session": True,
             })

    def scrape_url(self, url: str, ad_fields: dict, 
    **kwargs) -> BaseSource.Result:
        """
        Execute normal scraping flow with appropriate scraper routing.
        """
        if self._live_session is False:
            return self._configure_session(url)
        
        # Pass the session cookies in the scraping request
        kwargs["cookies"] = self._live_session["cookies"]
        result = super().scrape_url(url, ad_fields, **kwargs)

        if result.resp is not None:  # True if the request was successful
            return result
        return self._configure_session(url)

    def _configure_session(self, url: str) -> None:
        logger.info('Configuring defensive HTML source session')
        try:
            resp = self.driver.get(url, wait_xpath='//h1[@class="citation__title"]')
            self._live_session = {
                "cookies": dict(resp.cookies),
                "host": self.driver._chrome.host,
            }
            self._restart_scraper()
            return self._parse_response(resp, {})
        except Exception as exc:
            if isinstance(exc, (KeyboardInterrupt, BdbQuit)):
                raise exc
            logger.error('Driver initialisation failed')
            return self._parse_response(None, {})
    
    @property
    def driver(self) -> Driver:
        if self._driver is False:
            self._driver = Driver.get_or_create(
                ignore_scripts=True,
                request_retries=2,
                post_load_wait=5,
                proxy_file=self.proxy_file,
                headless=not self.guided_initialisation)
        return self._driver

    def _restart_scraper(self) -> None:
        self._scraper = Requester(**self.scraper_settings)
        self._scraper._host = self._live_session["host"]