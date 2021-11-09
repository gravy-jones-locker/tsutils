from ..common.exceptions import *

class RetryNeededError(NotificationError):
    """Logs message and prompts a retry"""
    def __init__(self, message, errors):
        super().__init__(message + ' - retrying', errors)

class ClientSideError(RetryNeededError):
    """Logs message and prompts header/proxy rotation"""
    def __init__(self, message, errors):
        super().__init__(message +' - clientside error; rotating host', errors)

class InvalidResourceError(SkipIterationError):
    """Logs message and skips current iteration"""
    def __init__(self, message, errors):
        super().__init__(message + ' - resource missing or unavailable', errors)

class ServerSideError(RetryNeededError):
    """Direct subclass of RetryNeededError"""
    pass

class RetriesExhaustedError(SkipIterationError):
    """Logs retries exhausted error and skips iteration"""
    def __init__(self, message, errors):
        super().__init__(message + ' - retries exhausted', errors)