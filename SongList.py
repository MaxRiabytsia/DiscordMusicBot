from Song import Song


class SongList:
    def __init__(self):
        self._song_list = []

    def __bool__(self):
        return self._song_list != []

    def __str__(self):
        return ", ".join([str(song) for song in self._song_list])

    def __iter__(self):
        self.__current = 0
        return self

    def __next__(self):
        if self.__current >= len(self._song_list):
            raise StopIteration
        song = self._song_list[self.__current]
        self.__current += 1
        return song

    def __len__(self):
        return len(self._song_list)

    def __getitem__(self, index):
        return self._song_list[index]

    def __setitem__(self, index, value):
        if isinstance(value, Song):
            self._song_list[index] = value
        else:
            raise ValueError(f"Argument should be of type Song, not {type(value)}")

    def append(self, song):
        if isinstance(song, Song):
            self._song_list.append(song)
        else:
            raise ValueError(f"Argument should be of type Song, not {type(song)}")

    def remove_by_index(self, index):
        if len(self._song_list) >= index >= 0:
            song = self._song_list.pop(index)
            return song
        return 0

    def remove_by_url(self, url):
        for song in self._song_list:
            if song.url == url:
                self._song_list.remove(song)
                return 1
        return 0

    def replace(self, old_song, new_song):
        if old_song in self._song_list:
            self._song_list[self.get_index(old_song)] = new_song
            return 1
        return 0

    def get_index(self, song):
        return self._song_list.index(song)

    def __get_numerated_titles(self):
        titles = []
        for i, song in enumerate(self._song_list):
            titles.append(f"{i+1}. {song.title}")
        return titles

    def split_into_messages(self):
        string_queue = '\n'.join(self.__get_numerated_titles())
        max_size_of_discord_msg = 1800
        if len(string_queue) < max_size_of_discord_msg:
            return [string_queue]

        separating_string = "@@@$$$***&&&###"
        list_of_chars = list(string_queue)
        index = 1

        for i in string_queue[max_size_of_discord_msg:len(list_of_chars):max_size_of_discord_msg]:
            index += max_size_of_discord_msg - 1
            if index > len(list_of_chars):
                return ''.join(list_of_chars)

            while i != '\n':
                index += 1
                if index >= len(list_of_chars):
                    return ''.join(list_of_chars)
                i = list_of_chars[index]

            list_of_chars.pop(index)
            list_of_chars.insert(index, separating_string)

        new_string = ''.join(list_of_chars)
        return new_string.split(separating_string)
