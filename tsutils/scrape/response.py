"""
This module contains the Response class which is returned from every scraping
action (even where it has to be composed..) and associated convenience classes.
"""

from __future__ import annotations

from seleniumwire.webdriver import Chrome
from requests import Session as InbuiltSession

SUCCESS_CODES = [200]
SERVERSIDE_ERROR_CODES = [404, 500]
# TODO extend these lists..

class Response:
    """
    This class provides a unified response interface for both scraping session
    types (Driver and Requests sessions). Important attributes:
        status_code: int
        content: bytes
        headers: dict
        error: Error  # Bound in case of any non-200 status code
    """
    def __init__(self, status_code: int, content: bytes, headers: dict) -> None:
        """
        Create Response from parsed/composed response details.
        :param status_code: the status code returned with the response.
        :param content: the bytes contents of the response.
        :param headers: the header dictionary returned with the response. 
        """
        self.status_code = status_code
        self.content = content
        self.headers = headers
        self.error = None
        if self.status_code not in SUCCESS_CODES:
            self.error = Error(self.status_code)
            
    @classmethod
    def from_driversession(cls, driver: Chrome) -> Response:
        """
        Configure a Response object from the driver attached to a DriverSession
        object.
        :param: a seleniumwire driver instance with 
        """
        cls.__init__(status_code, content, headers)

class Error:
    """
    Convenience class for error handling - computes error type and severity from
    the status code and other response content. Import attributes:
        clientside: bool
        serverside: bool
    """
    def __init__(self, status_code: int) -> None:
        """
        Parse response for the kind of error that has been returned.
        :param status_code: a non-200 status code from which to deduce details.
        """
        self.serverside = status_code in SERVERSIDE_ERROR_CODES
        self.clientside = not self.serverside