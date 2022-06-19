from discord.ext import commands, tasks
from discord.utils import get
from discord import FFmpegPCMAudio
from youtube_dl import YoutubeDL
import random
import requests
import urllib.request
from bs4 import BeautifulSoup
from re import findall
import pandas as pd
import validators

from Song import Song
from constants import *


client = commands.Bot(command_prefix=['!', '~'])
song_queue = []
song_now = None


# loop that checks every second if the voice has stopped playing and if there is something in queue,
# it plays first audio from the queue
@tasks.loop(seconds=3.0, count=None)
async def play_from_queue():
    voice = get(client.voice_clients)
    if song_queue and not voice.is_playing() and not voice.is_paused():
        play_url(voice, song_queue.pop(0))


# check if bot is ready
@client.event
async def on_ready():
    print('Bot is online')


def play_from_favs(msg):
    # finding n
    n = findall(r'\d{1,3}', msg)
    if not n:
        n = 15
    else:
        n = int(n[0])

    # adding to the queue n random songs from fav
    df = pd.read_csv('favs.csv')
    sample = df.sample(n)
    for i, song in sample.iterrows():
        song_queue.append(Song(song.url, song.title))


def play_from_query(ctx, msg):
    # composing url
    search_request = msg.lower().replace(' ', '+').replace('–', '-').replace('\n', '')

    # making requests in russian and ukrainian work using transliteration
    if not msg.isascii():
        search_request = urllib.parse.quote(search_request, encoding='utf-8')

    # getting the html of search result
    url = "https://www.youtube.com/results?search_query=" + search_request.replace("'", "")
    # getting the html of search result
    html = urllib.request.urlopen(url)

    # finding all the videos
    video_ids = findall(r"watch\?v=(\S{11})", html.read().decode())

    # composing the url of the first video
    url = "https://www.youtube.com/watch?v=" + video_ids[0]

    # request = requests.get(url, "html.parser")
    # page = BeautifulSoup(request.content, 'html.parser')
    # print(page.prettify())
    # # finding all the videos
    # first_video = page.find("a", {"id": "video-title"})["href"]
    # # composing the url of the first video
    # url = "https://www.youtube.com" + first_video

    return url


@client.command(help="connects bot to a voice channel if it's not and plays the url")
async def play(ctx, request="fav"):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    id = ctx.message.guild.id

    # connecting to the voice channel
    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

    msg = ctx.message.content
    msg = msg[msg.index('!') + 6::]

    # playing url
    if validators.url(request):
        url = request
    # playing n random songs from fav
    elif request.startswith('fav'):
        play_from_favs(msg)
        return
    # playing top video from YT found by given request
    else:
        url = play_from_query(ctx, msg)
        await ctx.send(url)

    # playing the audio or adding it to the queue
    song = Song(url)
    if not voice.is_playing():
        play_url(voice, song)
        await ctx.send("Bot is playing!")
    else:
        await ctx.send("Added to the queue!")


def play_url(voice, song):
    global song_now
    song_now = song
    print(f"URL: {song.url}\nTitle: {song.title}")

    # transforming URL to the right format
    with YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(song.url, download=False)
    url = info['url']

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


@client.command(help="adds video at position n to the favorite")
async def fav(ctx, n=0):
    id = ctx.message.guild.id
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

    df = pd.read_csv('favs.csv')
    if song.title not in df.title:
        df.loc[df.shape[0]] = pd.Series({"url": song.url, "title": song.title})
        df.to_csv('favs.csv', index=False)
    else:
        await ctx.send(f'The {song.title} is already in the favorites')


@client.command(help="shows the content of the 'favorite'")
async def favs(ctx):
    # getting id of a channel the command was called in
    id = ctx.message.guild.id

    # getting the string that contains favorites
    df = pd.read_csv('favs.csv')
    string_favs = "Favorites:\n"
    for i, song in df.iterrows():
        string_favs += f'{i + 1}. {song.title}\n'

    # splitting the string into blocks under 2000 chars in length
    string_favs = fit_text_in_msg(string_favs)
    for text_block in string_favs.split('@'):
        await ctx.send(text_block)


@client.command(help="removes the video at specified position from the favorites")
async def removef(ctx, n):
    # getting id of a channel the command was called in
    id = ctx.message.guild.id
    n = int(n)

    # reading the favorites file
    df = pd.read_csv('favs.csv')
    if df.shape[0] >= n >= 1:
        # modifying the favorites file
        await ctx.send(f"Good decison! I don't like {df.loc[n - 1].title} too!")
        df = df.drop([n - 1])
        df.to_csv("favs.csv")
    else:
        await ctx.send(f'Length of the favorites is only {df.shape[0]}, therefore there is no position {n}')


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
        song = song_queue.pop(n - 1)
        song_queue.insert(k - 1, song)
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
        song_queue.pop(n - 1)
    else:
        await ctx.send(f'Length of the queue is only {len(song_queue)}, therefore there is no position {n}')


@client.command(help="plays video instantly")
async def instant(ctx, request):
    await play(ctx, request)
    if song_queue:
        await move(ctx)
        await skip(ctx)


# command to play video after the one that's playing now
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


@client.command(help="Shuffles the queue")
async def shuffle(ctx):
    if song_queue:
        random.shuffle(song_queue)
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
    df = pd.read_csv("champ.csv")
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