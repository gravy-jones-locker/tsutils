"""
This module constitutes the high-level interface for centralising scraping 
operations in the TS codebase.
"""
from __future__ import annotations

from typing import Union

import logging

from ..common.pool import Pool
from ..common.exceptions import PoolError
from .source import DriverSource, Source, BaseSource, Endpoint
from .exceptions import SourceNotConfiguredError

logger = logging.getLogger('tsutils')

class Session:
    """
    This class is the intended entry point for complex scraping operations. 
    Example usage:
        >>> sess = Session(use_driver=True)
        >>> scrape_res = sess.scrape_urls(url_fields, 3)
        [TIME DATE] INFO: Processing url 1/10
        [TIME DATE] INFO: All urls successfully processed
        >>> print(scrape_res)
        {url1: {field1: value, field2: value, field3: value}, url2...}
    """

    def __init__(self, sources: list[BaseSource]=None, use_driver: bool=False, 
    **scraper_settings) -> None:
        """
        Configure connection details.
        :param sources: a list of Source *classes* for site-specific scraping.
        :param use_driver: toggles whether to use a Driver (Selenium) instance.
        :param scraper_settings: additional scraper settings.
        """
        self.sources = []  # All requests are passed through Source objects
        if sources is None:
            base_source = self._compile_source(use_driver, **scraper_settings)
            self.sources.append(base_source)
        else:
            self.sources = [x() for x in sources]
        # Very important to sort in order of descending specificity
        self.sources.sort(key=lambda x: x.specificity, reverse=True)

    def _compile_source(self, use_driver: bool, **scraper_settings) -> BaseSource:
        stype = Source
        if use_driver:
            stype = DriverSource
        stype.scraper_settings = scraper_settings
        return stype()
    
    def scrape_url(self, url: str, fields: dict=None, values_only: bool=True,
    **kwargs) -> Union[BaseSource.Result, dict]:
        """
        Call the URL given and extract available field data.
        :param url: the URL to call.
        :param ad_fields: any additional fields to retrieve.
        :param values_only: toggle the output format.
        :param kwargs: bespoke request arguments.
        :return: a dictionary of values or Result object as per values_only.
        """
        try:
            source = self._identify_request_source(url)
            if fields is None:
                fields = {}
            res = source.scrape_url(url, fields, **kwargs)
            if values_only:
                res = res.values
            return res
        except SourceNotConfiguredError:
            logger.info(f'Scraping {url} failed')
            return {}, None
    
    def _identify_request_source(self, url: str) -> Source:
        for source in self.sources:
            if not source.match_url(url):
                continue
            return source
        raise SourceNotConfiguredError(f'No source is configured for {url}')
    
    def scrape_urls(self, urls: list, fields: dict=None, values_only: bool=True,
    index: bool=False, num_threads: int=1) -> list:
        """
        Iterate over urls and return fields/responses as per file config.
        :param urls: a list of urls from which to scrape data.
        :param fields: an individual field config dict.
        :param values_only: toggle value dictionary or Result object outputs.
        :param index: toggle whether to return an indexed dictionary or list.
        :param num_threads: the number of threads (1 = no parallelisation).
        :return: a dictionary of results indexed by url.
        """
        if num_threads > 1 and self._running_driver():
            raise PoolError('Driver instances cannot be run in parallel')
        with Pool(num_threads, log_step=num_threads+1, raise_errs=False) as pool:
            out = pool.map(
                self.scrape_url, 
                [[x, fields, False] for x in urls])
        return self._parse_mapped_output(out, urls, values_only, index)
    
    def _parse_mapped_output(self, scraped: list, urls: list, 
    values_only: bool, index: bool) -> Union[dict, list]:
        out = []
        for result in scraped:
            if values_only:
                result = result.values
            out.append(result)
        if not index:
            return out
        return {urls[i]: x for i, x in enumerate(out)}

    def _running_driver(self) -> bool:
        return any([isinstance(x, DriverSource) for x in self.sources])
    
    def call_api(self, name: str, **kwargs) -> dict:
        """
        Call the given API with the arguments passed.
        :name: the .name attribute of an Endpoint object.
        :return: a dictionary of values found for each field.
        """
        try:
            source = self._identify_api_source(name)
            return source.call(**kwargs)
        except SourceNotConfiguredError:
            logger.info(f'Calling {name} failed')
            return {}
    
    def _identify_api_source(self, name: str) -> Endpoint:
        for source in self.sources:
            if not isinstance(source, Endpoint):
                continue
            if source.__class__.__name__ != name:
                continue
            return source
        raise SourceNotConfiguredError(f'No endpoint for {name} was found')