import sys
import logging

logger = logging.getLogger('tsutils')

class NotificationError(Exception):
    """Logs the error message and moves on"""
    def __init__(self, message, errors):
        logger.error(message)

class CriticalError(NotificationError):
    """Stops execution altogether"""
    def __init__(self, message, errors):
        super().__init__(message + ' - CRITICAL ERROR', errors)
        sys.exit()
        
class SkipIterationError(NotificationError):
    """Indicates that an iteration should be skipped"""
    def __init__(self, message, errors):
        super().__init__(message + ' - skipping iteration', errors)
        
class SilentError(Exception):
    """Results in nothing whatsoever"""
    pass

class InvalidSettingError(CriticalError):
    """Notifies the user of the incorrect setting passed and quits"""
    def __init__(self, key, config_dict, errors):
        msg = f'{key} is not a valid setting. Accepted fields are: {", ".join(list(config_dict.keys()))}' 
        super().__init__(msg, errors)