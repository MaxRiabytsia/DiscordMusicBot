from discord.ext import commands, tasks
from discord.utils import get
from discord import FFmpegPCMAudio
from youtube_dl import YoutubeDL
from re import findall
import pandas as pd
import validators
import logging

from Song import Song
from SongQueue import SongQueue
from constants import *


logging.basicConfig(filename='other/bot.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
client = commands.Bot(command_prefix=['!', '~'])
song_queue = SongQueue()
song_now = None


# loop that checks every second if the voice has stopped playing and if there is something in queue,
# it plays first audio from the queue
@tasks.loop(seconds=3.0, count=None)
async def play_from_queue():
    voice = get(client.voice_clients)
    if len(song_queue) != 0 and not voice.is_playing() and not voice.is_paused():
        play_url(voice, song_queue.dequeue())


# check if bot is active
@client.event
async def on_ready():
    print('Bot is online')


def play_from_favs(request):
    # finding n
    n = findall(r'\d{1,3}', request)
    if not n:
        n = 15
    else:
        n = int(n[0])

    # adding to the queue n random songs from fav
    df = pd.read_csv('data/favs.csv')
    sample = df.sample(n)
    for i, row in sample.iterrows():
        song_queue.enqueue(Song(row.url, row.title))


@client.command(help="connects bot to a voice channel if it's not and plays the url")
async def play(ctx, request="fav"):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    # connecting to the voice channel
    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

    # playing url
    if validators.url(request):
        song = Song(request)
    # playing n random songs from favorites
    elif request.startswith('fav'):
        play_from_favs(request)
        await ctx.send("Adding music from favorites to the queue")
        return
    # playing top video from YT found by given query
    else:
        msg = ctx.message.content
        msg = msg[msg.index('!') + 6::]
        song = Song.from_query(msg)
        await ctx.send(song.url)

    # adding the audio to the queue
    song_queue.enqueue(song)


def play_url(voice, song):
    global song_now
    song_now = song
    print(f"URL: {song.url}\nTitle: {song.title}")

    try:
        # transforming URL to the playable format
        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(song.url, download=False)
        url = info['url']
    except Exception as e:
        logging.error(e, exc_info=True)
        return

    # playing URL
    voice.play(FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
    voice.is_playing()


@client.command(help="displays a queue in chat")
async def queue(ctx):
    if song_queue:
        string_queue = "Queue:\n"
        for index, song in enumerate(song_queue):
            string_queue += f'{index + 1}. {song.title}\n'

        if len(string_queue) >= 2000:
            # splitting the string into blocks under 2000 chars in length
            string_queue = fit_text_in_msg(string_queue)
            for text_block in string_queue.split('@'):
                await ctx.send(text_block)
        else:
            await ctx.send(string_queue)
    else:
        await ctx.send("There is nothing in the queue")


@client.command(help="moves the video at the position 'first number' to the position 'second number' in the queue")
async def move(ctx, n=len(song_queue), k=1):
    n = int(n)
    k = int(k)
    bigger = n if n >= k else k
    smaller = k if n >= k else n
    flag = False

    if n == k:
        await ctx.send(
            f"Are you drunk?! You do know that moving song from position {n} to position {k} is pointless, don't you?")
    elif len(song_queue) >= bigger and smaller >= 0:
        song_queue.move(n-1, k-1)
        flag = True
    else:
        await ctx.send(f'Length of the queue is only {len(song_queue)}, therefore there is no position {bigger}')

    if flag:
        if smaller == k or k == 1:
            await ctx.send(
                f"I'm totally with you on that one! We should listen to {song_queue[k - 1].title} earlier!")
        else:
            await ctx.send(f"I agree with you! We don't need to rush with listening {song_queue[k - 1].title}!")


@client.command(help="removes the video at specified position from the queue")
async def remove(ctx, n=len(song_queue)):
    n = int(n)
    if len(song_queue) >= n >= 0:
        await ctx.send(f"Good decison! I don't like {song_queue[n - 1].title} too!")
        song_queue.remove(n - 1)
    else:
        await ctx.send(f'Length of the queue is only {len(song_queue)}, therefore there is no position {n}')


@client.command(help="Shuffles the queue")
async def shuffle(ctx):
    if len(song_queue) != 0:
        song_queue.shuffle()
        await ctx.send('The queue is shuffled')
    else:
        await ctx.send("There is nothing in the queue")


@client.command(help="Clears the queue")
async def clear(ctx):
    if song_queue:
        song_queue.clear()
        await ctx.send("The queue is cleared")
    else:
        await ctx.send("There is nothing in the queue")


@client.command(help="adds video at position n to the favorite")
async def fav(ctx, n=0):
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
    if song.title not in df.title:
        df.loc[df.shape[0]] = pd.Series({"url": song.url, "title": song.title})
        df.to_csv('data/favs.csv', index=False)
        await ctx.send(f'{song.title} was added to the favorites')
    else:
        await ctx.send(f'{song.title} is already in the favorites')


@client.command(help="shows the content of the 'favorite'")
async def favs(ctx):
    # getting the string that contains favorites
    df = pd.read_csv('data/favs.csv')
    string_favs = "Favorites:\n"
    for i, song in df.iterrows():
        string_favs += f'{i + 1}. {song.title}\n'

    # splitting the string into blocks under 2000 chars in length
    string_favs = fit_text_in_msg(string_favs)
    for text_block in string_favs.split('@'):
        await ctx.send(text_block)


@client.command(help="removes the video at specified position from the favorites")
async def removef(ctx, n):
    n = int(n)

    # reading the favorites file
    df = pd.read_csv('data/favs.csv')
    if df.shape[0] >= n >= 1:
        # modifying the favorites file
        await ctx.send(f"Good decison! I don't like {df.loc[n - 1].title} too!")
        df = df.drop([n - 1])
        df.to_csv("data/.csv")
    else:
        await ctx.send(f'Length of the favorites is only {df.shape[0]}, therefore there is no position {n}')


@client.command(help="plays video instantly")
async def instant(ctx, request):
    await play(ctx, request)
    if song_queue:
        await move(ctx)
        await skip(ctx)


@client.command(help="plays video after the one that's playing now")
async def next(ctx, request):
    await play(ctx, request)
    if song_queue:
        await move(ctx)


@client.command(help="displays what video is playing right now")
async def np(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        await ctx.send(f'"{song_now.title}" is playing right now.')
    else:
        await ctx.send("Nothing is playing")


@client.command(help="Resumes playing")
async def resume(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if not voice.is_playing():
        voice.resume()
        await ctx.send('Bot is resuming')
    else:
        await ctx.send("Nothing is playing")


@client.command(help="Pauses the music")
async def pause(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
        await ctx.send('Bot has been paused')
    else:
        await ctx.send("Nothing is playing")


@client.command(help="Skips the current song")
async def skip(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.stop()
        await ctx.send('Skipping...')
    else:
        await ctx.send("Nothing is playing")


@client.command(help="replays the video that is playing right now")
async def replay(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    voice.stop()
    play_url(voice, song_now)
    await ctx.send(f"Let's listen to {song_now.title} again!")


@client.command(help="plays winning songs")
async def champ(ctx):
    df = pd.read_csv("data/champ.csv")
    url = df.sample(1).iloc[0].url
    await instant(ctx, url)


def fit_text_in_msg(string):
    step = 1800
    tmp_list = list(string)
    index = 1

    for i in string[step:len(tmp_list):step]:
        index += step - 1
        if index > len(tmp_list):
            return ''.join(tmp_list)

        while i != '\n':
            index += 1
            if index >= len(tmp_list):
                return ''.join(tmp_list)
            i = tmp_list[index]

        tmp_list.pop(index)
        tmp_list.insert(index, '@')

    return ''.join(tmp_list)


def main():
    # starting 'play_from_queue' loop
    play_from_queue.start()

    # starting the bot
    client.run(BOT_TOKEN)


if __name__ == "__main__":
    main()