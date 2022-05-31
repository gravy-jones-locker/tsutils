from pathlib import Path

ROOT_DIR = str(Path(__file__).absolute().parents[0])

import sys
import os

if '--debug' in sys.argv or 'pdb' in sys.modules.keys():
    os.environ["TSUTILS_DEBUG"] = 'True'
else:
    os.environ["TSUTILS_DEBUG"] = 'False'

from tsutils.common.io import load_json

logconf = load_json(f'{ROOT_DIR}/input/config/log.json')
for handler, conf in logconf["handlers"].items():
    if handler == 'console':
        continue
    conf["filename"] = conf["filename"].replace('{ROOT_DIR}', ROOT_DIR)

from logging.config import dictConfig

dictConfig(logconf)

import os

if os.environ.get('TSUTILS_DEBUG') == 'True':
    import logging
    logger = logging.getLogger('tsutils')
    for handler in logger.handlers:
        if handler.name != 'console':
            continue
        handler.setLevel('DEBUG')