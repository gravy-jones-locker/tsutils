import json
import csv
import pickle

from typing import Any

def _read_text(fname: str) -> str:
    with open(fname, 'r') as infile:
        return infile.read()
def _read_bytes(fname: str) -> bytes:
    with open(fname, 'rb') as infile:
        return infile.read()
def _read_text_lines(fname: str) -> str:
    with open(fname, 'r') as infile:
        return infile.readlines()

def load_json(fpath: str) -> dict:
    """
    Convert a saved mapping to a Python dictionary.
    """
    return json.loads(_read_text(fpath))

def load_csv(fpath: str, flat: bool=False, delimiter: str=',') -> list:
    """
    Convert a comma-delimited file to a Python list of lists.
    """
    out = []
    for row in csv.reader(_read_text_lines(fpath), delimiter=delimiter):
        if flat:
            row = ' '.join(row)
        out.append(row)
    return out

def load_lines(fpath: str) -> list:
    """
    Return lines in any text file as a list of values.
    """
    return _read_text_lines(fpath)

def unpickle(fpath: str) -> Any:
    """
    Unpickle any file and return the pickled object.
    """
    data = _read_bytes(fpath)
    if len(data) == 0:
        return None
    return pickle.loads(data)

################################################################################
#                           OUTPUT FUNCTIONS START HERE                        #
################################################################################

def pickle_obj(obj: Any, fpath: str) -> None:
    """
    Pickle any object and write to the specified output file.
    """
    with open(fpath, 'wb+') as outfile:
        pickle.dump(obj, outfile)