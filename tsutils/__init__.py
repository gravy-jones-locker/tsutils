from pathlib import Path

ROOT_DIR = str(Path(__file__).absolute().parents[0])

import sys
import os

os.environ["TSUTILS_DEBUG"] = str('--debug' in sys.argv)

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
    logging.getLogger('tsutils').setLevel('DEBUG')