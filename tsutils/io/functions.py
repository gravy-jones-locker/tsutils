import json

def file_to_dict(fpath: str, encoding: str='utf8') -> dict:
    """
    Convert a saved mapping to a Python dictionary.
    :param fpath: a path to a saved Python dict or .json file.
    :param encoding: the file encoding.
    :return: a Python dictionary
    """
    with open(fpath, 'r', encoding=encoding) as infile:
        data = infile.read()
    return json.loads(data)