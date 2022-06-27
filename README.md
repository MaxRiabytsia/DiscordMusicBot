# DiscordMusicBot
Discord bot that plays audio from YouTube URLs, queries, and stores favorite songs to play them later.

I have built the bot using Discord API and youtube-dl to get the audio from the URLs*.

"bot.py" mainly consists of bot commands that can be called by users. There are also files for Song and SongQueue classes.

The main functionality of the bot is obviously playing music, so all the commands just trying to make it easier (e.g. pause,
resume, skip, replay, etc.). 

There is also a notion of a queue to listen to music in order, hence there is a number of functions to manipulate the queue 
(e.g. move, remove, shuffle, clear). 

The last big part of the bot is functions centered around playing and editing favorites file (e.g. fav, removef, favs). 

There is also a cluster of commands that serve as convinient shortcuts (e.g. 'instant' plays the audio instantly by adding it to the queue,
moving to the first spot, and skipping the current song; 'next' does the same thing as 'instant' but without the skipping). 

There is also one minor command 'champ' that instantly plays winning 
songs a.k.a. songs for some proud, epic, intense moments.


*Note: in order to succesfully run the bot on your machine you will need to download FFmpeg (free and open-source software project 
consisting of a suite of libraries and programs for handling video, audio, and other multimedia files and streams.)
