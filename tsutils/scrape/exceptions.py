from .utils.response import Response
from ..common.exceptions import *

class ResourceNotFoundError(SkipIterationError):
    pass

class PageLoadFailedError(NotificationError):
    pass

class RequestFailedError(QuietError):
    def __init__(self, resp: Response) -> None:
        super().__init__(f'Request failed - {resp.msg}')

class CaptchaHitError(NotificationError):
    def __init__(self, resp: Response) -> None:
        super().__init__(f'Captcha hit on {resp.url}')