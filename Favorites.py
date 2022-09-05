import pandas as pd
import os
import random

from SongList import SongList
from Song import Song


class Favorites(SongList):
    def __init__(self):
        super().__init__()
        data_folder = os.listdir("data")
        if "favs.csv" in data_folder:
            self.__favorites_df = pd.read_csv("data/favs.csv")
        else:
            self.__favorites_df = pd.DataFrame(columns=['url', 'title'])
        for i, row in self.__favorites_df.iterrows():
            super().append(Song(row.url, row.title))

    def __bool__(self):
        return self._song_list

    def append(self, song):
        if song not in self._song_list:
            super().append(song)
            return 1
        return 0

    def save(self):
        for song in self._song_list:
            if song.url not in self.__favorites_df.url.unique():
                self.__favorites_df.loc[self.__favorites_df.shape[0]] = pd.Series({'url': song.url,
                                                                                   'title': song.title})
        self.__favorites_df.to_csv("data/favs.csv", index=False)

    def get_random_sample(self, sample_size):
        if 0 < sample_size < len(self._song_list):
            return random.sample(self._song_list, sample_size)
        else:
            return random.sample(self._song_list, 15)
