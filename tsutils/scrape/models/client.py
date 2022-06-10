from .response import Response
from .hosts import Host

class Client:
    """
    Client is an interface for storing, updating and injecting Client details
    (headers, cookies, hosts).
    """
    def __init__(self, resp: Response, host: Host) -> None:
        self.resp = resp
        self.host = host
    
    def get_kwargs(self) -> dict:
        """
        Get a dictionary of request kwargs for injection.
        :return: a dictionary containing cookie, header and proxy details.
        """
        return {
            "headers": {"User-Agent": self.host.user_agent},
            "cookies": dict(self.resp.cookies),
            "proxies": self.host.proxy_dict,  # TODO no Driver compatibility
        }