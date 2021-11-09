class Scraper:
    def get(self, *args, **kwargs):
        raise NotImplementedError
    def click(self, *args, **kwargs):
        raise NotImplementedError
    def click_xpath(self, *args, **kwargs):
        raise NotImplementedError
    def _prime_session_request(self, *args, **kwargs):
        raise NotImplementedError