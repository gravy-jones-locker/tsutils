"""
Look for some other running Logger instance or create a new one and declare
as logger (for import by other modules).
"""

import logging
import os
import pathlib
from logging.handlers import RotatingFileHandler

LOGPATH = os.path.split(pathlib.Path(__file__).resolve())[0] + '/log.txt'

def configure_logger():
    logger = logging.getLogger(__name__)
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s',
                        level=logging.INFO)
    file = configure_file_log_handler()
    logger.addHandler(file)
    return logger

def configure_file_log_handler():
    mode = 'w+' if not os.path.isfile(LOGPATH) else 'a'
    file = RotatingFileHandler(filename=LOGPATH,
                                maxBytes=5*1024*1024, 
                                backupCount=2,
                                mode=mode)
    fileformat = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    file.setFormatter(fileformat)
    return file

loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
if loggers:
    logger = loggers[0]  # TODO may need to choose selectively
else:
    logger = configure_logger()