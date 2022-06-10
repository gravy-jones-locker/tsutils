from pathlib import Path

ROOT_DIR = str(Path(__file__).absolute().parents[0])

__version__ = '0.2'

import sys
import os

from tsutils.common.io import load_json

logconf = load_json(f'{ROOT_DIR}/input/config/log.json')
for handler, conf in logconf["handlers"].items():
    if handler == 'console':
        continue
    conf["filename"] = conf["filename"].replace('{ROOT_DIR}', ROOT_DIR)

import logging
from logging.config import dictConfig

dictConfig(logconf)

logger = logging.getLogger('tsutils')

if '--debug' in sys.argv or 'pdb' in sys.modules.keys():
    for handler in logger.handlers:
        if handler.name != 'console':
            continue
        handler.setLevel('DEBUG')

if 'pdb' in sys.modules.keys():
    os.environ["TSUTILS_DEBUG"] = 'True'
else:
    os.environ["TSUTILS_DEBUG"] = 'False'