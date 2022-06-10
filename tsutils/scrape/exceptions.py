from requests.exceptions import ProxyError

from ..common.exceptions import *

class ResourceNotFoundError(SkipIterationError):
    pass

class PageLoadFailedError(Exception):
    pass

class ScrapeFailedError(SkipIterationError):
    pass

class RequestFailedError(Exception):
    pass

class CaptchaHitError(Exception):
    pass

class SourceNotConfiguredError(SkipIterationError):
    pass

class WrongFieldTypeError(SkipIterationError):
    pass

class LiveDriverError(CriticalError):
    pass

class StopScrapeError(StopPoolExecutionError):
    pass

class NoDriverRequestError(Exception):
    pass


PROXY_EXCEPTIONS = (
    ProxyError,
    ConnectionResetError,
)