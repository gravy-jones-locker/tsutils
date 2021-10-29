from ..common.exceptions import *

class RetryNeededError(NotificationError):
    # An error of this type prompts a retry
    def __init__(self, message, errors):
        message += ' - retrying'
class ClientSideError(NotificationError):
    # An error of this type prompts header/proxy rotation
    def __init__(self, message, errors):
        message += ' - clientside error; rotating header/proxy config'
class InvalidResourceError(SkipIterationError):
    # Skips current iteration (and hopefully the invalid resource)
    def __init__(self, message, errors):
        message += '- resource missing or unavailable'
        super().__init__(message, errors)
class ServerSideError(RetryNeededError):
    pass  # Any serverside error requires a retry
class RetriesExhaustedError(SkipIterationError):
    # Extends iteration skipping error and records message
    def __init__(self, message, errors):
        message += '- retries exhausted'
        super().__init__(message, errors)