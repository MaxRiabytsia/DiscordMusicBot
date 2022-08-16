import asyncio
from discord.ext import commands, tasks
from discord.utils import get
from discord import FFmpegPCMAudio
import youtube_dl
from re import findall
import pandas as pd
import validators
import logging
import os

from Song import Song
from SongQueue import SongQueue
from constants import *
import generate_recommendations

logging.basicConfig(filename='other/bot.log', format='\n\n%(name)s - %(levelname)s - %(message)s')
prefixes = ['!', '~']
client = commands.Bot(command_prefix=prefixes)
song_queue = SongQueue()
song_now = None


# region playing audio
@tasks.loop(seconds=3.0, count=None)
async def play_from_queue(ctx):
    """
    Loop that checks every 3 seconds if the bot has stopped playing and if there is something in queue,
    if so, it plays first audio from the queue
    """
    voice = get(client.voice_clients)
    if len(song_queue) != 0 and not voice.is_playing() and not voice.is_paused():
        await play_url(ctx, voice, song_queue.dequeue())


@client.command(help="Replaces song on specified position in the queue and favs "
                     "(or currently playing song if position is not specified)"
                     "with another song with similar title")
async def replace(ctx, n=0):
    # finding song that is being replaced
    if n == 0:
        global song_now
        song = song_now
    else:
        song = song_queue[n-1]

    # finding a song to replace it
    new_song = song
    i = 0
    while new_song.url == song.url:
        new_song = Song.from_query(song.title, video_id=i)
        i += 1

    # checking if the song was in favs
    # if so remove it
    df = pd.read_csv("data/favs.csv")
    removed_from_favs = False
    if song.url in df.url.unique():
        removed_from_favs = True
        await removef(ctx, df.index[df.url == song.url][0] + 1)

    await ctx.send(f"Replacing '{song.title}' with '{new_song.title}'")

    # if the song is playing, play new song instead
    if n == 0:
        await instant(ctx, new_song.url)
    # if the song is in the queue, then replace it
    else:
        await play(ctx, new_song.url)
        await asyncio.sleep(0.1)
        await remove(ctx, n)
        await asyncio.sleep(0.1)
        await move(ctx, k=n)

    # add new song to favs
    if removed_from_favs:
        await asyncio.sleep(0.1)
        await fav(ctx, n)


async def play_from_file(ctx, request, file):
    """
    Adds n random songs from file to the queue,
    n is inside the request.
    File can either be favorite songs or recommended songs.
    """
    # finding n
    n = findall(r'\d{1,3}', request)
    if not n:
        n = 15
    else:
        n = int(n[0])

    # adding to the queue n random songs from fav
    if file == "recommendations.csv":
        data_folder = os.listdir("data")
        if "matched_favs.csv" not in data_folder or "new" in request:
            await ctx.send("Generating recommendations... (it might take some time)")
            generate_recommendations.main(True)
    df = pd.read_csv(f'data/{file}')
    if df.shape[0] > n:
        sample = df.sample(n)
    else:
        sample = df.sample(n, replace=True)
    for i, row in sample.iterrows():
        song_queue.enqueue(Song(row.url, row.title))


@client.command(help="Connects bot to a voice channel if it's not and plays the request. "
                     "Types of requests: URL, word query, 'fav' + n (optional quantity), "
                     "'recom' + n (optional quantity).")
async def play(ctx, request="fav"):
    """
    Connects bot to a voice channel if it's not and plays the request.
    Types of requests: URL, word query, 'fav' + n (optional quantity), 'recom' + n (optional quantity).
    """
    if not play_from_queue.is_running():
        # starting 'play_from_queue' loop
        play_from_queue.start(ctx)

    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    # connecting to the voice channel
    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        await channel.connect()

    msg = ctx.message.content
    for char in prefixes:
        if char in msg.strip()[:5]:
            msg = msg[msg.index(char) + 6::]

    # playing url
    if validators.url(request):
        song = Song(request)
        # adding the audio to the queue
        song_queue.enqueue(song)
    # playing n random songs from favorites
    elif request.startswith("fav"):
        await play_from_file(ctx, msg, "favs.csv")
        await ctx.send("Adding audio from favorites to the queue")
    # playing n random songs from favorites
    elif request.startswith("recom"):
        await play_from_file(ctx, msg, "recommendations.csv")
        await ctx.send("Adding recommended audio based on your favorites to the queue")
    # playing top audio from YT found by given query
    else:
        song = Song.from_query(msg)
        await ctx.send(song.url)
        # adding the audio to the queue
        song_queue.enqueue(song)


@client.command(help="Plays winning songs")
async def champ(ctx):
    """
    Plays winning songs
    """
    df = pd.read_csv("data/champ.csv")
    url = df.sample(1).iloc[0].url
    await instant(ctx, url)


async def play_url(ctx, voice, song, attempt=1):
    """
    Plays the song.
    """
    global song_now
    song_now = song
    print(f"\nURL: {song.url}\nTitle: {song.title}")

    # transforming URL to the playable format
    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
        ydl.cache.remove()
        try:
            info = ydl.extract_info(song.url, download=False)
            url = info['url']
            # playing URL
            voice.play(FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
            voice.is_playing()
        except (youtube_dl.utils.DownloadError, youtube_dl.utils.ExtractorError) as error:
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
                await replace(ctx)
            else:
                if attempt == 1:
                    await ctx.send("Trying again...")
                    await play_url(ctx, voice, song, attempt=2)
                else:
                    await replace(ctx)
# endregion


# region queue
@client.command(help="Displays the queue in chat")
async def queue(ctx):
    """
    Displays the queue in chat.
    """
    if song_queue:
        string_queue = "Queue:\n"
        for index, song in enumerate(song_queue):
            string_queue += f'{index + 1}. {song.title}\n'

        if len(string_queue) >= 2000:
            # splitting the string into blocks under 2000 chars in length
            list_of_messages = split_string_into_pieces(string_queue, 1800)
            for text_block in list_of_messages:
                if text_block != "":
                    await ctx.send(text_block)
        else:
            await ctx.send(string_queue)
    else:
        await ctx.send("There is nothing in the queue")


@client.command(help="Moves the audio at the position 'first number' to the position 'second number' in the queue")
async def move(ctx, n=len(song_queue), k=1):
    """
    Moves the audio at the position n to the position k in the queue
    """
    n = int(n)
    k = int(k)
    bigger = n if n >= k else k
    smaller = k if n >= k else n
    flag = False

    if n == k:
        await ctx.send(
            f"Are you drunk?! You do know that moving song from position {n} to position {k} is pointless, don't you?")
    elif len(song_queue) >= bigger and smaller >= 0:
        song_queue.move(n - 1, k - 1)
        flag = True
    else:
        await ctx.send(f'Length of the queue is only {len(song_queue)}, therefore there is no position {bigger}')

    if flag:
        if smaller == k or k == 1:
            await ctx.send(
                f"I'm totally with you on that one! We should listen to {song_queue[k - 1].title} earlier!")
        else:
            await ctx.send(f"I agree with you! We don't need to rush with listening {song_queue[k - 1].title}!")


@client.command(help="Removes the audio at specified position from the queue")
async def remove(ctx, n=len(song_queue)):
    """
    Removes the audio at specified position from the queue
    """
    n = int(n)
    if len(song_queue) >= n >= 0:
        await ctx.send(f"Good decison! I don't like {song_queue[n - 1].title} too!")
        song_queue.remove(n - 1)
    else:
        await ctx.send(f'Length of the queue is only {len(song_queue)}, therefore there is no position {n}')


@client.command(help="Shuffles the queue")
async def shuffle(ctx):
    """
    Shuffles the queue
    """
    if len(song_queue) != 0:
        song_queue.shuffle()
        await ctx.send('The queue is shuffled')
    else:
        await ctx.send("There is nothing in the queue")


@client.command(help="Clears the queue")
async def clear(ctx):
    """
    Clears the queue
    """
    if song_queue:
        song_queue.clear()
        await ctx.send("The queue is cleared")
    else:
        await ctx.send("There is nothing in the queue")


# endregion


# region favs control
@client.command(help="Adds audio at position n to the favorite")
async def fav(ctx, n=0):
    """
    Adds audio at position n to the favorites
    """
    voice = get(client.voice_clients, guild=ctx.guild)

    # position is not specified, so we take the song that is playing right now
    if n == 0 and voice.is_playing():
        song = song_now
    # position is specified
    elif int(n) <= len(song_queue):
        song = song_queue[n - 1]
    else:
        await ctx.send(f'Length of the queue is only {len(song_queue)}, therefore there is no position {n}')
        return

    df = pd.read_csv('data/favs.csv')
    if song.title not in df.title.values:
        df.loc[df.shape[0]] = pd.Series({"url": song.url, "title": song.title})
        df.to_csv('data/favs.csv', index=False)
        await ctx.send(f'{song.title} was added to the favorites')
    else:
        await ctx.send(f'{song.title} is already in the favorites')


@client.command(help="Shows the content of the favorites")
async def favs(ctx):
    """
    Shows the content of the favorites.
    """
    # getting the string that contains favorites
    df = pd.read_csv('data/favs.csv')
    string_favs = "Favorites:\n"
    for i, song in df.iterrows():
        string_favs += f'{i + 1}. {song.title}\n'

    # splitting the string into blocks under 2000 chars in length
    list_of_messages = split_string_into_pieces(string_favs, 1800)
    for text_block in list_of_messages:
        await ctx.send(text_block)


@client.command(help="Removes the audio at specified position from the favorites")
async def removef(ctx, n):
    """
    Removes the audio at specified position from the favorites
    """
    n = int(n)

    # reading the favorites file
    df = pd.read_csv('data/favs.csv')
    if df.shape[0] >= n >= 1:
        # modifying the favorites file
        await ctx.send(f"Good decison! I don't like {df.loc[n - 1].title} too!")
        df = df.drop([n - 1])
        df.to_csv("data/favs.csv")
    else:
        await ctx.send(f'Length of the favorites is only {df.shape[0]}, therefore there is no position {n}')


# endregion


# region audio stream control
@client.command(help="Displays what audio is playing right now")
async def np(ctx):
    """
    Displays what audio is playing right now
    """
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing() and isinstance(song_now, Song):
        await ctx.send(f'"{song_now.title}" is playing right now.')
    else:
        await ctx.send("Nothing is playing")


@client.command(help="Resumes playing")
async def resume(ctx):
    """
    Resumes playing the audio if it was paused.
    """
    voice = get(client.voice_clients, guild=ctx.guild)
    if not voice.is_playing():
        voice.resume()
        await ctx.send('Bot is resuming')
    else:
        await ctx.send("Nothing is playing")


@client.command(help="Pauses the audio")
async def pause(ctx):
    """
    Pauses the audio
    """
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
        await ctx.send('Bot has been paused')
    else:
        await ctx.send("Nothing is playing")


@client.command(help="Skips the current song")
async def skip(ctx):
    """
    Skips the current song
    """
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.stop()
        await ctx.send('Skipping...')
    else:
        await ctx.send("Nothing is playing")


@client.command(help="replays the audio that is playing right now")
async def replay(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    voice.stop()
    if isinstance(song_now, Song):
        await play_url(ctx, voice, song_now)
        await ctx.send(f"Let's listen to {song_now.title} again!")
    else:
        await ctx.send(f"There is nothing to replay")


# endregion


# region shortcuts
@client.command(help="Plays the audio instantly")
async def instant(ctx, request):
    """
    Plays the audio instantly
    """
    await play(ctx, request)
    if song_queue:
        await move(ctx)
        await skip(ctx)


@client.command(help="Plays the audio after the one that's playing now")
async def next(ctx, request):
    """
    Adds the to queue and moves it to the first position
    """
    await play(ctx, request)
    if song_queue:
        await move(ctx)


# endregion


# region other
@client.event
async def on_ready():
    """
    Prints message when the bot activates
    """
    print('Bot is online')


def split_string_into_pieces(string, size):
    """
    Splits string into smaller strings that has length == size + 'number of chars before \n'
    """
    list_of_chars = list(string)
    index = 1

    for i in string[size:len(list_of_chars):size]:
        index += size - 1
        if index > len(list_of_chars):
            return ''.join(list_of_chars)

        while i != '\n':
            index += 1
            if index >= len(list_of_chars):
                return ''.join(list_of_chars)
            i = list_of_chars[index]

        list_of_chars.pop(index)
        list_of_chars.insert(index, '@@@')

    new_string = ''.join(list_of_chars)

    return new_string.split("@@@")


# endregion


def main():
    # starting the bot
    client.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
