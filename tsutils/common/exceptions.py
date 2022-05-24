import sys
import logging

logger = logging.getLogger('tsutils')

class NotificationError(Exception):
    suffix = ''
    def __init__(self, *msg):
        logger.error(''.join(msg) + self.suffix)

class CriticalError(NotificationError):
    suffix = ' CRITICAL - QUITTING'
    def __init__(self, *msg):
        super().__init__(*msg)
        sys.exit()
        
class SkipIterationError(NotificationError):
    suffix = '... skipping'

class QuietError(Exception):
    def __init__(self, *msg):
        logger.debug(''.join(msg))
        
class SilentError(Exception):
    pass