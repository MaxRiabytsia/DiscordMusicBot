from bs4 import BeautifulSoup
import requests


class Song:
    def __init__(self, *args):
        if len(args) == 1:
            self.url = args[0]
            self.title = self.__get_title(self.url)
        elif len(args) == 2:
            self.title = args[0]
            self.url = args[1]

    @classmethod
    def __get_title(cls, url):
        request = requests.get(url, "html.parser")
        page = BeautifulSoup(request.content, 'html.parser')
        # !!!!!!!!!!!!!!!!!!!!!!!
        title = page.find("yt-formatted-string", {"class": "style-scope ytd-watch-metadata"}).text

        return title
