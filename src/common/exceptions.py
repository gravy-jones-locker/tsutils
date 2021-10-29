import sys
from ..logger import logger

class NotificationError(Exception):
    # An error of this type logs the error message and moves on
    def __init__(self, message, errors):
        logger.error(message)
class CriticalError(NotificationError):
    def __init__(self, message, errors):
        message += '- CRITICAL ERROR'
        super().__init__(message, errors)
        sys.exit() # An error of this type stops execution altogether
class SkipIterationError(NotificationError):
    def __init__(self, message, errors):
        message += '- skipping iteration'
        super().__init__(message, errors)
class SilentError(Exception):
    pass  # An error of this type results in nothing whatsoever