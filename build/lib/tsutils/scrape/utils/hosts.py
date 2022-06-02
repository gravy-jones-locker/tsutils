"""
These classes simplify host configuration and rotation to minimise user
supervision of avoidable scraping failures.
"""
from __future__ import annotations

import os
import logging

from typing import Generator, Union
from itertools import cycle, product

from tsutils.common.io import load_csv 
from tsutils import ROOT_DIR    

logger = logging.getLogger('tsutils')

UAS_FPATH = f'{ROOT_DIR}/input/data/useragents.csv'

class Hosts:
    """
    The Host instances are collected into an infinite loop for easy rotation.
    """
    def __init__(self, proxy_file: Union[str, None]) -> None:
        self._cycle = cycle(
            self._compile_hosts(
                self._load_proxies(proxy_file),
                self._load_user_agents()))
    
    def __next__(self) -> Host:
        return next(self._cycle)
    
    def _compile_hosts(self, proxies: list, user_agents: list) -> Generator:
        for user_agent, proxy in product(user_agents, proxies):
            yield Host._load(proxy, user_agent)
    
    def _load_proxies(self, proxy_file: Union[str, None]) -> list:
        if proxy_file is not None:
            if os.path.isfile(proxy_file):
                return load_csv(proxy_file, flat=True)
            logger.error(f'Proxy file at {proxy_file} not found. Ignoring')
        return ['localhost']
    
    def _load_user_agents(self) -> list:
        return load_csv(UAS_FPATH, flat=True)

class Host:
    """
    Corresponds to a unique proxy/user-agent combination.
    """
    @classmethod
    def _load(cls, proxy: str, user_agent: str) -> None:
        if proxy == 'localhost':
            return LocalHost(user_agent)
        return Host(proxy, user_agent)

    def __init__(self, proxy: str, user_agent: str) -> None:
        self.proxy = proxy
        self.user_agent = user_agent
        self.proxy_dict = self._build_proxy_dict()
        self.proxy_dict_prefixed = self._build_proxy_dict(prefixed=True)
    
    def _build_proxy_dict(self, prefixed: bool=False) -> dict:
        out = {"https": self.proxy, "http": self.proxy, "ftp": self.proxy}
        if prefixed:
            out = {k: k+'://'+v for k, v in out.items()}
        return out

    def __str__(self) -> str:
        return f'{self.proxy} - {self.user_agent[:20]}...'

class LocalHost(Host):
    """
    Corresponds to the Host instance where no proxy is being used.
    """
    def __init__(self, user_agent: str) -> None:
        super().__init__(None, user_agent)
        
    def _build_proxy_dict(self, prefixed: bool=False) -> dict:
        return {}