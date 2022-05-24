"""
This module contains the Response class which is returned from every scraping
action (even where it has to be composed..)
"""
from __future__ import annotations

from requests import Response as RequestsResponse
from requests.cookies import cookiejar_from_dict, RequestsCookieJar
from seleniumwire.request import Request as SWRequest
from seleniumwire.request import Response as SWResponse
from seleniumwire.utils import decode
from lxml import html
from typing import Union

from ..constants import BAD_COOKIE_KEYS, CAPTCHA_STRS

class Response(RequestsResponse):
    """
    This class provides a unified response interface for both scraping session
    types (Driver and Requests sessions). 
    """
    AD_ATTRS = [
        '_msg',
        '_dom',
        '_captchaed'
    ]
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for attr in self.AD_ATTRS:  # Configure additional properties
            setattr(self, attr, False)

    @property
    def dom(self) -> html.HtmlElement:
        """
        Return the document-object-model from the response.
        """
        if self._dom is False:
            self._dom = html.fromstring(self.text)
        return self._dom
    
    @property
    def msg(self) -> str:
        """
        Return a descriptive message for logging.
        :return: the output message string.
        """
        if self._msg is False:
            self._msg = f'{self.status_code} raised requesting {self.url}'
        return self._msg
    
    @property
    def captchaed(self) -> bool:
        """
        Return True if the response contains a captcha.
        :return: True if there are captcha elements in the page.
        """
        if self._captchaed is False:
            self._captchaed = self._detect_captcha()
        return self._captchaed

    def xpath(self, statement: str) -> Union[str, html.HtmlElement]:
        """
        Return the contents of an xpath search on the response dom.
        :param statement: an xpath statement e.g. '//a[@class="link"]'
        :return: the result of the xpath search.
        """
        return self.dom.xpath(statement)
    
    def _detect_captcha(self) -> bool:
        if any([x in self.text for x in CAPTCHA_STRS]):
            return True
        return False

    @classmethod
    def _from_chrome(cls, request: SWRequest, cookies: list) -> Response:
        return cls._configure_from_state({
            "status_code": request.response.status_code,
            "reason": request.response.reason,
            "headers": request.response.headers,
            "url": request.url,
            "_content": cls._decode_response_body(request.response),
            "request": request,
            "cookies": cls._load_chrome_cookies(cookies)})
    
    @classmethod
    def _from_details(cls, **kwargs) -> Response:
        return cls._configure_from_state(kwargs)
    
    @classmethod
    def _from_requester(cls, response: RequestsResponse) -> Response:
        return cls._configure_from_state(response.__getstate__())
    
    @classmethod
    def _from_chrome_src(cls, src: str, cookies: list, **kwargs) -> Response:
        return cls._configure_from_state({
            "status_code": 0,
            "reason": "User compiled - status unknown",
            "_content": cls._get_content_from_src(src),
            "cookies": cls._load_chrome_cookies(cookies),
            **kwargs})
    
    @classmethod
    def _configure_from_state(cls, state: dict) -> Response:
        resp = cls()
        resp.__setstate__(state)
        return resp
    
    @staticmethod
    def _load_chrome_cookies(cookies: list) -> RequestsCookieJar:
        out = cookiejar_from_dict({})
        for cookie in cookies:
            for key in BAD_COOKIE_KEYS & set(cookie.keys()):
                cookie.pop(key)
            out.set(cookie.pop('name'), cookie.pop('value'), **cookie)
        return out
    
    @staticmethod
    def _decode_response_body(resp: SWResponse) -> str:
        return decode(resp.body,
                      resp.headers.get('Content-Encoding', 'identity'))
    
    @staticmethod
    def _get_content_from_src(src: str) -> bytes:
        return src.encode('utf8')