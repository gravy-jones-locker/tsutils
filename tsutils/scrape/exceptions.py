from ..common.exceptions import *

class ResourceNotFoundError(SkipIterationError):
    pass

class PageLoadFailedError(NotificationError):
    pass

class RequestFailedError(QuietError):
    def __init__(self, msg: str) -> None:
        super().__init__(f'Request failed - {msg}')

class CaptchaHitError(NotificationError):
    def __init__(self, url: str) -> None:
        super().__init__(f'Captcha hit on {url}')

class SourceNotConfiguredError(SkipIterationError):
    pass

class WrongFieldTypeError(SkipIterationError):
    def __init__(self, xpath) -> None:
        super().__init__(f'{xpath} could not be resolved into a string')