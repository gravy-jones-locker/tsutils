"""
This module constitutes the high-level interface for centralising scraping 
operations in the TS codebase.
"""
from __future__ import annotations

from typing import Union

import logging

from ..common.pool import Pool
from ..common.exceptions import PoolError
from .source import DriverSource, Source, BaseSource
from .exceptions import SourceNotConfiguredError
from .utils.field import Field
from .utils.response import Response

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
    
    def scrape_url(self, url: str, fields: dict, **kwargs) -> dict:
        """
        Scrape a given url for the fields specified.
        :param url: the url from which to extract the data.
        :param fields: a dictionary of xpath/regex details for each field.
        :param kwargs: bespoke request arguments for the scraping call.
        :return: a dictionary with the values found for each field.
        Field configuration dictionaries should look like this:
        ```
            {'author': {[  # Each field has multiple possible entries
                {'xpath': '//div[@class="author"]/text()',
                 'patt': '\w+\s\w+'},
                {'xpath': '(//div[@class="info-pane"]/span)[2]/text()',
                 'patt': 'author: \w+\s\w+'}
                 ]},
            'publication_name': ...
            }
        ```
        """
        out = {}
        try:
            resp = self.get(url, **kwargs)
            if resp is None:
                return out
            for fname, fconf in fields.items():
                field = Field(fname, fconf)
                out[fname] = field.extract(resp)
            return out
        except SourceNotConfiguredError:
            logger.info(f'Scraping {url} failed')
            return out
    
    def get(self, url: str, **kwargs) -> Response:
        """
        Execute a get request using the configured scrapers.
        :param url: the URL to which to point the get request.
        :param kwargs: any bespoke request arguments to add.
        :return: a Response object compiled from the server response.
        """
        return self._identify_request_source(url).scraper.get(url, **kwargs)
    
    def _identify_request_source(self, url: str) -> Source:
        for source in self.sources:
            if not source.match_url(url):
                continue
            return source
        raise SourceNotConfiguredError(f'No source is configured for {url}')
    
    def scrape_urls(self, urls: list, fields: Union[list, dict],
    num_threads: int=1) -> dict:
        """
        Iterate over urls and extract field data as per file config.
        :param urls: a list of urls from which to scrape data.
        :param fields: a broadcastable array/individual field config dict.
        :param num_threads: the number of threads (1 = no parallelisation).
        :return: a dictionary of results indexed by url.
        """
        if num_threads > 1 and self._running_driver():
            raise PoolError('Driver instances cannot be run in parallel')
        with Pool(num_threads, log_step=num_threads+1) as pool:
            values = pool.map(
                self.scrape_url, 
                self._build_map_args(urls, fields))
        return {urls[i]: v for i, v in enumerate(values)}
    
    def _build_map_args(self, urls: list, fields: Union[list, dict]) -> list:
        if isinstance(fields, dict):
            fields = [fields for _ in range(len(urls))]
        return list(zip(urls, fields))
    
    def _running_driver(self) -> bool:
        return any([isinstance(x, DriverSource) for x in self.sources])