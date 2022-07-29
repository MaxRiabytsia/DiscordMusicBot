from bs4 import BeautifulSoup
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
    def from_query(cls, query, video_id=0):
        """
        Gets the url of the first video found on YouTube after searching 'query'
        """
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
        url = "https://www.youtube.com/watch?v=" + video_ids[video_id]

        return Song(url)

    @classmethod
    def __get_title(cls, url):
        """
        Gets the title of the video from 'url'
        """
        # getting the html of the URL
        fp = urllib.request.urlopen(url)
        mybytes = fp.read()
        html = mybytes.decode("utf8")
        fp.close()
        page = BeautifulSoup(html, 'html.parser')
        title = page.find("meta", {"name": "title"})["content"]

        return title
