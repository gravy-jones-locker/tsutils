# Load all the static config settings as attributes of the config module
import os

from .io import file_to_dict
from . import config

for fname in os.listdir('input/config'):
    setattr(config, fname, file_to_dict(f'input/config{fname}'))

# Load logger configuration saved in logconf.json
from logging.config import dictConfig

dictConfig(config.log)