from re import findall
import validators

from constants import *


class UserRequest:
    def __init__(self, request):
        self.__request = self.__get_request_without_command_name(request)
        self.type = self.__get_request_type()
        self.query = self.__get_query()
        self.number_of_songs = self.__get_number_of_songs()

    @staticmethod
    def __get_request_without_command_name(request):
        list_of_words_in_request = request.strip().split(" ")
        list_of_words_in_request.pop(0)
        request_without_command_name = " ".join(list_of_words_in_request)
        print(request_without_command_name)

        if request_without_command_name == "":
            request_without_command_name = "fav"

        return request_without_command_name

    def __get_request_type(self):
        if validators.url(self.__request):
            return "url"
        elif "fav" in self.__request or "recom" in self.__request:
            return "file"
        else:
            return "word query"

    def __get_query(self):
        if "fav" in self.__request:
            return "fav"
        elif "recom" in self.__request and "new" in self.__request:
            return "recom new"
        elif "recom" in self.__request:
            return "recom"
        else:
            return self.__request

    def __get_number_of_songs(self):
        if self.type == "file":
            number_of_songs = findall(r'\d+', self.__request)
            if not number_of_songs:
                number_of_songs = 15
            elif int(number_of_songs[0]) > 1000:
                number_of_songs = 1000
            else:
                number_of_songs = int(number_of_songs[0])

            return number_of_songs

        return 1
