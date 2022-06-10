from bdb import BdbQuit

class CriticalError(Exception):
    pass
        
class SkipIterationError(Exception):
    pass

class StopPoolExecutionError(Exception):
    pass

class PoolError(CriticalError):
    pass

class ConfigurationError(Exception):
    pass

STOP_EXCEPTIONS = (
    KeyboardInterrupt,
    BdbQuit,
)