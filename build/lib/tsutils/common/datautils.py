def update_defaults(base: dict, new: dict) -> dict:
    """
    Update a dictionary of defaults with custom values.
    :param base: the defaults dictionary.
    :param new: the dictionary of new values.
    :return: a dictionary of updated defaults
    """
    out = {}
    for key in base:
        out[key] = new.get(key, base[key])
    return out