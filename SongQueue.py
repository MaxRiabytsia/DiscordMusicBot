import random

import Song


class SongQueue:
    def __init__(self):
        self.__queue = []

    def __iter__(self):
        self.__current = 0
        return self

    def __next__(self):
        if self.__current >= len(self):
            raise StopIteration
        song = self.__queue[self.__current]
        self.__current += 1
        return song

    def __getitem__(self, index):
        return self.__queue[index]

    def __setitem__(self, index, value):
        if isinstance(value, Song.Song):
            self.__queue[index] = value
        else:
            raise ValueError(f"Argument should be of type Song, not {type(value)}")

    def __len__(self):
        return len(self.__queue)

    def dequeue(self):
        return self.__queue.pop(0)

    def enqueue(self, song):
        if isinstance(song, Song.Song):
            self.__queue.append(song)
        else:
            raise ValueError(f"Argument should be of type Song, not {type(song)}")

    def remove(self, index):
        self.__queue.pop(index)

    def move(self, from_index, to_index):
        song = self.__queue.pop(from_index)
        self.__queue.insert(to_index, song)

    def clear(self):
        self.__queue = []

    def shuffle(self):
        if self.__queue:
            random.shuffle(self.__queue)

    def replace(self, old_song_index, new_song):
        self.__queue[old_song_index] = new_song
