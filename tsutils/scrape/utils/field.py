import re

from typing import Union

from .response import Response
from ..exceptions import WrongFieldTypeError

class Field:
    """
    Interface for extracting field data from Response objects.
    """
    def __init__(self, name: str, conf: Union[dict, list]) -> None:
        self.name = name
        self.conf = self._compile_conf(conf)
    
    def _compile_conf(self, conf: Union[dict, list]) -> list:
        out = []
        defaults = {"patt": None, "ignore_case": True}
        if not isinstance(conf, list):
            conf = [conf]  # Default to multiple fields
        for attempt in conf:
            if not isinstance(attempt, dict):
                attempt = {"xpath": attempt}
            out.append({**defaults, **attempt})
        return out
    
    def extract(self, resp: Response) -> list:
        """
        Use the .conf dictionary to get field data from a Response.
        :param resp: the Response object to parse.
        :return: a list of field values.
        """
        for attempt in self.conf:
            try:
                results = self._execute_attempt(attempt, resp)
                if results is not None:
                    return results
            except WrongFieldTypeError:
                continue
        return []
    
    def _execute_attempt(self, attempt: dict, resp: Response) -> list:
        out = []
        vals = resp.xpath(attempt["xpath"])
        for val in vals:
            if not isinstance(val, str):
                raise WrongFieldTypeError(attempt["xpath"])
            val = self._parse_val(val, attempt["patt"], attempt["ignore_case"])
            if val is not None:
                out.append(val)
        return out

    def _parse_val(self, val: str, patt: str, ignore_case: bool) -> str:
        if patt is None:
            return val
        if ignore_case:
            matches = re.search(patt, val, flags=re.I)
        else:
            matches = re.search(patt, val)
        if matches:
            return matches.group(1)
        return None