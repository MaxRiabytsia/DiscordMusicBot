from bs4 import BeautifulSoup
import requests
import urllib.request
from re import findall


class Song:
    def __init__(self, url, title=None):
        self.url = url
        if title is not None:
            self.title = title
        else:
            self.title = self.__get_title(self.url)

    @classmethod
    def from_query(cls, query):
        # composing url
        search_request = query.lower().replace(' ', '+').replace('–', '-').replace('\n', '')
        # making requests in ukrainian and russian work
        if not query.isascii():
            search_request = urllib.parse.quote(search_request, encoding='utf-8')
        url = "https://www.youtube.com/results?search_query=" + search_request.replace("'", "")

        # getting the html of search result
        html = urllib.request.urlopen(url)

        # finding all the videos
        video_ids = findall(r"watch\?v=(\S{11})", html.read().decode())
        # composing the url of the first video
        url = "https://www.youtube.com/watch?v=" + video_ids[0]

        return Song(url)

    @classmethod
    def __get_title(cls, url):
        request = requests.get(url, "html.parser")
        page = BeautifulSoup(request.content, 'html.parser')
        # add .isascii check and status_code check
        title = page.find("meta", {"name": "title"})["content"]

        return title
