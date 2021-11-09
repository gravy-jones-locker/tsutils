"""
These classes simplify host configuration and rotation to minimise user
supervision of avoidable scraping failures.
"""

from itertools import cycle, product

class Host:
    """
    Each individual Host instance represents a certain proxy/user agent combo.
    """
    def __init__(self, proxy: str, user_agent: str) -> None:
        """
        Store the host proxy and user agent and configure other attrs.
        :param proxy: an ip:host proxy address for routing requests.
        :param user_agent: a user agent string to add to request headers.
        """
        self.proxy = proxy
        self.user_agent = user_agent
        self.use_count = 0       # Updated after every request
        self.rotation_count = 0  # Updated after rotation away

    def __str__(self) -> str:
        return f'{self.proxy} - {self.user_agent[:20]}...'

    def _mark_rotation(self) -> None:
        self.use_count = 0
        self.rotation_count += 1

class Hosts:
    """
    The Host instances are collected into an infinite loop for easy rotation.
    """
    current_host: Host = None
    # _ls and _cycle are the underlying iterables containing each of the
    # possible user_agent/proxy combinations. 
    _ls: list
    _cycle: cycle

    def __init__(self, proxies: list, user_agents: list) -> None:
        """
        Combines proxy and user_agent values into individual Host instances.
        :param proxies: a list of ip:host proxy addresses.
        :param user_agents: a list of user agents.
        using a certain host.
        """
        proxies = [] if proxies is None else proxies
        proxies.insert(0, None)  # Guarantees start from localhost
        self._ls = []
        for proxy, user_agent in product(proxies, user_agents):
            self._ls.append(Host(proxy, user_agent))
        self._cycle = cycle(self._ls)
        self.rotate()

    def rotate(self) -> None:
        """
        Extend usual next() method by integrating Host expiry and counters.
        """
        if self.current_host is not None:
            # If no successful requests were made with the current host then
            # discard it.
            if self.current_host.use_count == 0:
                self._ls = [x for x in self.ls if x != self.current_host]
                self._cycle = cycle(self._ls)
            else:
                self.current_host._mark_rotation()
        self.current_host = next(self._cycle)

    def __str__(self) -> str:
        return '\n'.join([str(x) for x in self._ls])