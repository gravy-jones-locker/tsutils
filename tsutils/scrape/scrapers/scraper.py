"""
This module contains the abstract Scraper class which provides the common
foundation for interaction with target scraping sites by the Driver and
Requester subclasses. 
"""

class Scraper:
    """
    This class serves a purely formal purpose - which is to unify the multiple
    'scraper' interfaces by which a program programatically interacts with a
    site for scraping.

    As such, it explicitly declares the methods and attributes which are
    required for this purpose by concrete subclass instances. 
    """
    def _prime_session_request(self, *args, **kwargs):
        raise NotImplementedError
    def _compose_response(self, *args, **kwargs):
        raise NotImplementedError