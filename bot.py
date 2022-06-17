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
queue = []
song_now = None


# loop that checks every second if the voice has stopped playing and if there is something in queue,
# it plays first audio from the queue
@tasks.loop(seconds=3.0, count=None)
async def play_from_queue():
    voice = get(client.voice_clients)
    if queue and not voice.is_playing() and not voice.is_paused():
        play_url(voice, queue.pop(0))


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
        queue.append(Song(song.url, song.title))


def play_from_query(ctx, msg):
    # composing url
    search_request = msg.lower().replace(' ', '+').replace('–', '-').replace('\n', '')

    # making requests in russian and ukrainian work using transliteration
    if not msg.isascii():
        search_request = urllib.parse.quote(search_request, encoding='utf-8')

    # getting the html of search result
    url = "https://www.youtube.com/results?search_query=" + search_request.replace("'", "")
    request = requests.get(url, "html.parser")
    page = BeautifulSoup(request.content, 'html.parser')

    # finding all the videos
    first_video = page.find("a", {"class": "yt-simple-endpoint style-scope ytd-video-renderer"})["href"]

    # composing the url of the first video
    url = "https://www.youtube.com" + first_video
    await ctx.send(url)

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

    # playing the audio or adding it to the queue
    song = Song(url)
    queue.append(song)
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


@client.command(help="displays what video is playing right now")
async def np(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        await ctx.send(f'"{song_now.title}" is playing right now.')


@client.command(help="Shuffles the queue")
async def shuffle(ctx):
    if queue:
        random.shuffle(queue)
        await ctx.send('The queue is shuffled')
    else:
        await ctx.send("There is nothing in the queue")


@client.command(help="Clears the queue")
async def clear(ctx):
    if queue:
        queue.clear()
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


def main():
    # starting 'play_from_queue' loop
    play_from_queue.start()

    # starting the bot
    client.run(BOT_TOKEN)


if __name__ == "__main__":
    main()