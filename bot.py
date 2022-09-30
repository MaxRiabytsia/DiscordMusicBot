from discord.ext import commands, tasks
from discord.utils import get
from discord import FFmpegPCMAudio
import youtube_dl
import pandas as pd
import logging
import os
import sys

from Song import Song
from SongQueue import SongQueue
from Favorites import Favorites
from UserRequest import UserRequest
from constants import *
import generate_recommendations

logging.basicConfig(filename='other/bot.log', format='\n\n%(name)s - %(levelname)s - %(message)s')
bot = commands.Bot(command_prefix=PREFIXES)
song_queue = SongQueue()
favorites = Favorites()
song_being_played = None


# region playing audio
@tasks.loop(seconds=2.0, count=None)
async def play_from_queue(ctx):
    """
    Loop that checks every 3 seconds if the bot has stopped playing and if there is something in queue.
    If so, it plays the first song from the queue
    """
    voice = get(bot.voice_clients)
    if len(song_queue) != 0 and not voice.is_playing() and not voice.is_paused():
        await play_url(ctx, song_queue.dequeue())


async def enqueue_from_favorites(ctx, number_of_songs):
    sample_of_favorites = favorites.get_random_sample(number_of_songs)
    song_queue.enqueue(sample_of_favorites)
    await ctx.send("Adding audio from favorites to the queue")


async def enqueue_from_recommendations(ctx, request):
    data_folder = os.listdir("data")
    if "recommendations.csv" not in data_folder or "new" in request.query:
        await ctx.send("Generating recommendations... (it might take some time)")
        generate_recommendations.main(True)

    sample_of_recommendations = favorites.get_random_sample(request.number_of_songs)
    song_queue.enqueue(sample_of_recommendations)
    await ctx.send("Adding recommended audio based on your favorites to the queue")


@bot.command(name="play", help="Connects bot to a voice channel if it's not and plays the request. "
                               "Types of requests: URL, word query, 'fav' + n (optional quantity), "
                               "'recom' + 'new' (optional parameter to generate new recommendations "
                               "(adding it will dramatically increase required time)) + n (optional quantity).")
async def enqueue(ctx):
    if not play_from_queue.is_running():
        play_from_queue.start(ctx)

    await connect_to_channel(ctx)
    request = UserRequest(ctx.message.content)

    if request.type == "url":
        song_queue.enqueue(Song(request.query))
    elif request.query == "fav":
        await enqueue_from_favorites(ctx, request.number_of_songs)
    elif request.query == "recom":
        await enqueue_from_recommendations(ctx, request)
    else:
        song = Song.from_query(request.query)
        await ctx.send(song.url)
        song_queue.enqueue(song)


@bot.command(name="champ", help="Plays winning songs")
async def play_champion_music(ctx):
    df = pd.read_csv("data/champ.csv")
    url = df.sample(1).iloc[0].url
    await play_instantly(ctx, url)


async def handle_errors_from_playing_url(ctx, error, song, attempt):
    logging.error(error, exc_info=True)
    await ctx.send(f"Error occured in attempting to play '{song}'.")

    # handling 'video is no longer available' and 'sign in to confirm you age'
    if ("video unavailable" in str(error).lower() or "sign in to confirm you age" in str(error).lower() or
            "private" in str(error).lower()):
        if "video unavailable" in str(error).lower():
            text_of_problem = "no longer available."
        else:
            text_of_problem = "age-restricted."

        await ctx.send(f"Video '{song.title}' is {text_of_problem} "
                       f"We will look for different video with similar title and play it instead.")
        await replace_song_with_similar_one(ctx)
    else:
        if attempt == 1:
            await ctx.send("Trying again...")
            await play_url(ctx, song, attempt=2)
        else:
            await replace_song_with_similar_one(ctx)


async def play_url(ctx, song, attempt=1):
    voice = get(bot.voice_clients)
    global song_being_played
    song_being_played = song
    print(f"\nURL: {song.url}\nTitle: {song.title}")

    # transforming URL to the playable format
    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
        ydl.cache.remove()
        try:
            info = ydl.extract_info(song.url, download=False)
            if "_type" in info.keys() and info["_type"] == "playlist":
                songs = [Song(f"https://www.youtube.com/watch?v={video['id']}", video["title"]) for video in
                         info['entries']]
                song_queue.enqueue(songs)
                url = songs[0].url
            else:
                url = info["url"]
            voice.play(FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
            voice.is_playing()
        except (youtube_dl.utils.DownloadError, youtube_dl.utils.ExtractorError) as error:
            await handle_errors_from_playing_url(ctx, error, song, attempt)


# endregion


# region queue
@bot.command(name="queue", help="Displays the queue in chat")
async def display_song_queue(ctx):
    if song_queue:
        await ctx.send("Queue:\n")
        for msg in song_queue.split_into_messages():
            if msg != "":
                await ctx.send(msg)
    else:
        await ctx.send("There is nothing in the queue")


@bot.command(name="move",
             help="Moves the song at the position 'position_from' to the position 'position_to' in the queue")
async def move_song_in_queue(ctx, position_from=len(song_queue), position_to=1):
    bigger = position_from if position_from >= position_to else position_to
    smaller = position_to if position_from >= position_to else position_from
    is_song_moved = False

    if position_from == position_to:
        await ctx.send(
            f"Are you drunk?! You do know that moving song from position {position_from} "
            f"to position {position_to} is pointless, don't you?")
    elif len(song_queue) >= bigger and smaller >= 0:
        song_queue.move(position_from - 1, position_to - 1)
        is_song_moved = True
    else:
        await ctx.send(f'Length of the queue is only {len(song_queue)}, therefore there is no position {bigger}')

    if is_song_moved:
        if smaller == position_to or position_to == 1:
            await ctx.send(
                f"I'm totally with you on that one! We should listen to '{song_queue[position_to - 1].title}' earlier!")
        else:
            await ctx.send(f"I agree with you! "
                           f"We don't need to rush with listening '{song_queue[position_to - 1].title}'!")


@bot.command(name="remove", help="Removes the audio at specified position from the queue")
async def remove_song_from_queue_by_position(ctx, position: int):
    position = position if position else len(song_queue)
    song = song_queue.remove_by_index(position - 1)
    if song:
        await ctx.send(f"Good decison! I don't like {song.title} too!")
    else:
        await ctx.send(f'Length of the queue is only {len(song_queue)}, therefore there is no position {position}')


@bot.command(name="shuffle", help="Shuffles the queue")
async def shuffle_queue(ctx):
    if len(song_queue) != 0:
        song_queue.shuffle()
        await ctx.send('The queue is shuffled')
    else:
        await ctx.send("There is nothing in the queue")


@bot.command(name="clear", help="Clears the queue")
async def clear_queue(ctx):
    if song_queue:
        song_queue.clear()
        await ctx.send("The queue is cleared")
    else:
        await ctx.send("There is nothing in the queue")


# endregion


# region favs control
@bot.command(name="fav", help="Adds audio at position n to the favorite")
async def add_from_queue_to_favorites(ctx, song_position_in_queue=0):
    voice = get(bot.voice_clients, guild=ctx.guild)

    # position is not specified, so we take the song that is playing right now
    if song_position_in_queue == 0 and voice.is_playing():
        song = song_being_played
    # position is specified
    elif song_position_in_queue <= len(song_queue):
        song = song_queue[song_position_in_queue - 1]
    else:
        await ctx.send(f'Length of the queue is only {len(song_queue)}, '
                       f'therefore there is no position {song_position_in_queue}')
        return

    is_successful = favorites.append(song)
    if is_successful:
        await ctx.send(f'{song.title} was added to the favorites')
    else:
        await ctx.send(f'{song.title} is already in the favorites')


@bot.command(name="favs", help="Shows the content of the favorites")
async def display_favorites(ctx):
    if favorites:
        await ctx.send("Favorites:\n")
        for msg in favorites.split_into_messages():
            if msg != "":
                await ctx.send(msg)
    else:
        await ctx.send("There is nothing in the favorites")


@bot.command(name="removef", help="Removes the audio at specified position from the favorites")
async def remove_from_favorites_by_position(ctx, position=len(favorites)):
    song = favorites.remove_by_index(position - 1)
    if song:
        await ctx.send(f"Good decison! I don't like {song.title} too!")
    else:
        await ctx.send(f'Length of the favorites is only {len(favorites)}, therefore there is no position {position}')


# endregion


# region audio stream control
@bot.command(name="np", help="Displays what audio is playing right now")
async def display_current_song(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing() and isinstance(song_being_played, Song):
        await ctx.send(f'"{song_being_played.title}" is playing right now.')
    else:
        await ctx.send("Nothing is playing")


@bot.command(name="resume", help="Resumes playing")
async def resume_playing(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if not voice.is_playing():
        voice.resume()
        await ctx.send('Bot is resuming')
    else:
        await ctx.send("Nothing is playing")


@bot.command(name="pause", help="Pauses the audio")
async def pause_playing(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
        await ctx.send('Bot has been paused')
    else:
        await ctx.send("Nothing is playing")


@bot.command(name="skip", help="Skips the current song")
async def skip_current_song(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.stop()
        await ctx.send('Skipping...')
    else:
        await ctx.send("Nothing is playing")


@bot.command(name="replay", help="replays the audio that is playing right now")
async def replay_current_song(ctx):
    if isinstance(song_being_played, Song):
        await play_instantly(ctx, song_being_played.url)
        await ctx.send(f"Let's listen to {song_being_played.title} again!")
    else:
        await ctx.send(f"There is nothing to replay")


# endregion


# region shortcuts
@bot.command(name="instant", help="Plays the audio instantly")
async def play_instantly(ctx, request=None):
    if request:
        ctx.message.content = request
    await enqueue(ctx)
    if song_queue:
        await move_song_in_queue(ctx)
        await skip_current_song(ctx)


@bot.command(name="next", help="Plays the audio after the one that's playing now")
async def play_song_next(ctx):
    await enqueue(ctx)
    if song_queue:
        await move_song_in_queue(ctx)


# endregion


# region other
async def connect_to_channel(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        await channel.connect()


@bot.command(name="replace", help="Replaces song on specified position in the queue and favs "
                                  "(or currently playing song if position is not specified)"
                                  "with another song with similar title")
async def replace_song_with_similar_one(ctx, n=0):
    # finding song that is being replaced
    if n == 0:
        global song_being_played
        old_song = song_being_played
    else:
        old_song = song_queue[n - 1]

    # finding a new song to replace it
    new_song = old_song
    i = 0
    while new_song.url == old_song.url:
        new_song = Song.from_query(old_song.title, video_id=i)
        i += 1

    await ctx.send(f"Replacing '{old_song.title}' with '{new_song.title}'")

    # if the song is playing, play new song instead
    if n == 0:
        await play_instantly(ctx, new_song.url)
    # if the song is in the queue, then replace it
    else:
        song_queue.replace(n - 1, new_song)

    # replace in favorites if it is there
    song_was_in_favorites = favorites.replace(old_song, new_song)
    if song_was_in_favorites:
        await ctx.send(f"Replacing '{old_song.title}' with '{new_song.title}' in favorites")


@bot.command(name="exit", help="Saves changes and terminates the bot")
async def save_changes_and_terminate(ctx):
    await ctx.send("Saving changes to the favorites...")
    favorites.save()
    await ctx.send("Bye!")
    sys.exit()


@bot.event
async def on_ready():
    """
    Prints message when the bot activates
    """
    print('Bot is online')


# endregion


def main():
    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
