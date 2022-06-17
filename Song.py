from bs4 import BeautifulSoup
import requests


class Song:
    def __init__(self, url, title=None):
        self.url = url
        if title is not None:
            self.title = title
        else:
            self.title = self.__get_title(self.url)

    @classmethod
    def __get_title(cls, url):
        request = requests.get(url, "html.parser")
        page = BeautifulSoup(request.content, 'html.parser')
        # add .isascii check and status_code check
        title = page.find("meta", {"name": "title"})["content"]

        return title
