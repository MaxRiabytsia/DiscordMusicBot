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

    def __eq__(self, other):
        return self.url == other.url

    def __str__(self):
        if self.title:
            return self.title
        return self.url

    @staticmethod
    def __get_query_for_official_video(query):
        # removing everything in parentheses because
        # usually there is info that makes quality worse
        # for example "Scorpions - Wind of Change (live from Berlin 1987)"
        if '(' in query and ')' in query:
            open_index = query.find('(')
            close_index = query.find(')')
            query = query[:open_index] + query[close_index + 1:]

        if '[' in query and ']' in query:
            open_index = query.find('[')
            close_index = query.find(']')
            query = query[:open_index] + query[close_index + 1:]

        return query + " official"

    @classmethod
    def from_query(cls, query, video_id=0):
        """
        Gets the url of the first video found on YouTube after searching 'query'
        """
        query = cls.__get_query_for_official_video(query)

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
        # getting the html of the URL
        with urllib.request.urlopen(url) as file:
            html = file.read().decode("utf8")
        page = BeautifulSoup(html, 'html.parser')
        title = page.find("meta", {"name": "title"})["content"]

        return title
