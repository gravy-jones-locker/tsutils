from urllib.parse import urlparse

def compare_urls(*urls) -> bool:
    """
    Work out if a collection of URLs are "the same".
    :return: True if the URLs point to the same resource otherwise False.
    """
    refs = []
    for url in urls:
        refs.append(get_url_parts(url))
    return len(set(refs)) == 1

def get_url_parts(url: str) -> tuple:
    """
    Get the domain (netloc) and path from a URL.
    :return: the two parsed components.
    """
    parsed = urlparse(url)
    return parsed.netloc, parsed.path

def is_url(url: str) -> bool:
    """
    Do parsing to work out if a URL is valid.
    :param url: the URL to test.
    :return: True if the URL is valid otherwise False.
    """
    return all(get_url_parts(url))