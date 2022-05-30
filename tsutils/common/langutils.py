import re

def get_re_group(txt: str, patt: str, case_sensitive: bool=False, 
group: int=1) -> str:
    re_kwargs = {}
    if case_sensitive:
        re_kwargs["flags"] = re.I
    matches = re.search(patt, txt, **re_kwargs)
    if matches:
        return matches.group(group)
    return None