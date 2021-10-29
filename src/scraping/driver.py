from seleniumwire import webdriver
from itertools import cycle
from ..logger import logger
from . import config

class Driver(webdriver.Chrome):
    """
    A subclass of the SeleniumWire ChromeDriver for scraping from sites which
    require dynamic interactivity.
    """
    def __init__(self, proxies: list=None, cookies: dict=None, headers=None,
        headless: bool=True, chromedriver_path: str=None, 
        scraper_settings: dict=None) -> None:
        """
        Start the webdriver instance and configure connection details.
        :param proxies: a list of proxies through which to rotate if necessary.
        :param cookies: a dictionary of cookie key/value pairs to configure.
        :param headers: a dictionary of header key/value pairs to configure.
        :param headless: toggles whether to create a headless instance.
        :param chromedriver_path: necessary if driver binary not in root.
        :param scraper_settings: a dictionary of other scraper settings. 
        """
        self.hosts = self.configure_hosts(proxies)
        self.cookies = cookies if cookies is not None else {}
        self.headers = headers if headers is not None else {}
        self.headless = headless
        self.chromedriver_path = chromedriver_path
        self.settings = config.SCRAPER_SETTINGS
        if scraper_settings is not None:
            # Overwrite default scraper settings with any provided
            self.settings.update(scraper_settings)
        self.init_webdriver()

    @staticmethod
    def configure_hosts(proxies: list) -> cycle:
        """
        Set up a repeating set of host configurations from proxies/user agents.
        :param proxies: the list of proxies passed into the constructor method.
        :return: an itertools.cycle consisting of possible host configs. 
        """
        proxies.insert(0, None)  # Guarantees start from localhost
        return cycle(zip(proxies, config.USER_AGENTS))

    def init_webdriver(self) -> None:
        """
        Configures options and executes parent webdriver constructor
        """
        logger.info('Starting webdriver')
        init_kwargs = {}
        init_kwargs["options"] = self.configure_webdriver_options()
        if self.chromedriver_path is not None:
            init_kwargs["executable_path"] = self.chromedriver_path
        super().__init__(**init_kwargs)
        self.set_page_load_timeout(self.settings["load_timeout"])
        for key, value in self.cookies.items():
            # TODO this might require a 'domain' key also..
            self.add_cookie({"name": key, "value": value})
        self.header_overrides = self.headers

    def configure_webdriver_options(self) -> webdriver.ChromeOptions:
        """
        Build user-specified settings into a webdriver Options object.
        :return: a seleniumwire Chrome options instance.
        """
        options = webdriver.ChromeOptions()
        proxy, user_agent = next(self.hosts)
        options.add_argument(f'user_agent={user_agent}')
        if proxy is not None:
            options.add_argument(f'proxy-server={proxy}')
        if self.headless:
            options.add_argument('headless')
        # Hard-wired to ignore excessive logging
        options.add_argument(f'log-level=3')
        # These arguments improve driver robustness
        options.add_argument('no-sandbox')
        options.add_argument('disable-dev-shm-usage')
        return options