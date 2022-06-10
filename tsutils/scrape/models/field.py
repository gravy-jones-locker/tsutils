from typing import Union
from lxml import html

from ...common.langutils import get_re_group
from .response import Response
from ..exceptions import WrongFieldTypeError

DEFAULTS = {
    "patt": None,
    "case_sensitive": False,
    "join": False
    }

class Field:
    """
    Interface for extracting field data from Response objects. 
    
    This class is purely abstract. Concrete instances are supplied by the 
    HTMLField and APIField subclasses.
    """
    def __init__(self, name: str, conf: Union[str, dict, list]) -> None:
        self.name = name
        self.conf = self._compile_conf(conf)

    def extract(self, resp: Response) -> list:
        """
        Use the .conf dictionary to get field data from a Response.
        :param resp: the Response object to parse.
        :return: a list of field values.
        """
        data = self._get_data(resp)
        for sub_conf in self.conf:
            results = self._process_sub_conf(sub_conf, data)
            if results:
                return results
        return []

class HTMLField(Field):
    """
    Interface for extracting field data from Response objects which contain
    structured HTML.

    Each field instance is configured from the name of the field and scraping
    instructions. Scraping instructions must contain at least an "xpath" value
    and can contain a "patt" and "case_sensitive" value.

    Scraping instructions can be given either as a list of dictionaries **or**
    a list of strings (which will be assumed to be "xpath" values) **or** an
    individual string (which will be assumed to be an "xpath" value). E.g.:
    ```
    [
        {'xpath': '//div[@class="author"]/text()',
        'patt': '(\w+)\s\w+'},
        {'xpath': '(//div[@class="info-pane"]/span)[2]/text()',
        'patt': 'author: (\w+\s\w+)'}
    ]
    ```
    """
    def _get_data(self, resp: Response) -> html.HtmlElement:
        return resp.dom

    def _compile_conf(self, conf: Union[dict, list]) -> list:
        out = []
        conf = self._listify_conf(conf)
        for sub_conf in conf:
            out.append(self._compile_sub_conf(sub_conf))
        return out
    
    def _listify_conf(self, conf: Union[dict, list]) -> list:
        return conf if isinstance(conf, list) else [conf]
    
    def _compile_sub_conf(self, sub_conf: dict) -> dict:
        if not isinstance(sub_conf, dict):
            sub_conf = {"xpath": sub_conf}
        return {**DEFAULTS, **sub_conf}
    
    def _process_sub_conf(self, sub_conf: dict, data: Response) -> Union[str, 
    list]:
        out = []
        vals = data.xpath(sub_conf["xpath"])
        for val in vals:
            if not isinstance(val, str):
                raise WrongFieldTypeError(sub_conf["xpath"])
            if sub_conf["patt"] is not None:
                val = self._parse_val(val, sub_conf)
            if val is not None:
                out.append(val)
        if sub_conf["join"]:
            out = ' '.join(out)
        return out

    def _parse_val(self, val: str, sub_conf: dict) -> str:
        return get_re_group(
            val,
            sub_conf["patt"],
            sub_conf["case_sensitive"])

class APIField(Field):

    def _compile_conf(self, conf: Union[str, list, dict]) -> dict:
        return conf

    def extract(self, resp: Response) -> list:
        data = resp.json()
        keys = self.conf.split('&&')
        for key in keys:
            data = data[key]
        return data