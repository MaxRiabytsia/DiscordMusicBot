import random
from typing import overload

from SongList import SongList
from Song import Song


class SongQueue(SongList):
    def __init__(self):
        super().__init__()

    @overload
    def enqueue(self, song: Song) -> None:
        ...

    @overload
    def enqueue(self, list_of_song: list[Song]) -> None:
        ...

    def enqueue(self, item):
        if isinstance(item, Song):
            super().append(item)
        elif isinstance(item, list):
            self._song_list += item
        else:
            raise ValueError('You must pass either Song or list of Song')

    def dequeue(self):
        return self._song_list.pop(0)

    def move(self, from_index, to_index):
        song = self._song_list.pop(from_index)
        self._song_list.insert(to_index, song)

    def clear(self):
        self._song_list = []

    def shuffle(self):
        if self._song_list:
            random.shuffle(self._song_list)
