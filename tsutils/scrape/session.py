"""
This module constitutes the high-level interface for centralising scraping 
operations in the TS codebase.
"""
from __future__ import annotations

from typing import Union

import logging
import re

from ..common.pool import Pool
from .scrapers import *

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

    def __init__(self, scraper: Scraper=None, use_driver: bool=False, 
    proxy_file: str=None) -> None:
        """
        Configure connection details.
        :param scraper: a preconfigured scraper instance - useful if 
        non-standard scraper settings are required (e.g. cookies, headers).
        :param use_driver: use a Driver (Selenium) instance.
        :param proxies: the path to a proxy file (.txt).
        """
        self._scraper = self._configure_scraper(scraper,
                                                use_driver,
                                                proxy_file)
    
    def scrape_url(self, url: str, fields: dict, **kwargs) -> dict:
        """
        Scrape a given url for the fields specified.
        :param url: the url from which to extract the data.
        :param fields: a dictionary of xpath/regex details for each field.
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
        resp = self._scraper.get(url, **kwargs)
        if resp is None:
            return out
        for field, field_conf in fields.items():
            out[field] = []
            if not isinstance(field_conf, list):
                field_conf = [field_conf]
            for conf in field_conf:
                if not isinstance(conf, dict):
                    conf = {"xpath": conf, "patt": ''}
                elems = resp.dom.xpath(conf["xpath"])
                if not elems:
                    continue
                for elem in elems:
                    if conf["patt"]:
                        matches = re.search(conf["patt"], elem, flags=re.I)
                        if not matches:
                            continue
                        val = matches.group(1)
                    else:
                        val = elem
                    out[field].append(val)
        return out

    def scrape_urls(self, urls: list, fields: Union[list, dict],
    num_threads: int=1) -> dict:
        """
        Iterate over urls and extract field data as per file config.
        :param urls: a list of urls from which to scrape data.
        :param fields: a broadcastable array/individual field config dict.
        :param num_threads: the number of threads (1 = no parallelisation).
        :return: a dictionary of results indexed by url.
        """
        if isinstance(fields, dict):
            fields = [fields for _ in range(len(urls))]
        arg_ls = list(zip(urls, fields))
        with Pool(num_threads, log_step=1) as pool:
            values = pool.map(self.scrape_url, arg_ls)
        return {urls[i]: v for i, v in enumerate(values)}
    
    def _configure_scraper(self, scraper: Union[Scraper, None], 
    use_driver: bool, proxy_file: Union[str, None]) -> Scraper:
        if scraper is not None:
            return scraper  # True if a preconfigured instance is passed
        if use_driver:
            return Driver(proxy_file)
        return Requester(proxy_file)

    def _configure_fields(urls: list, fields: Union[list, dict]) -> list:
        return fields