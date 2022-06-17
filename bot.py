import nacl
from discord.ext import commands, tasks
from discord.utils import get
from discord import FFmpegPCMAudio
from youtube_dl import YoutubeDL
import random
import urllib.request
from re import findall
import pandas as pd

# from keep_alive import keep_alive


client = commands.Bot(command_prefix='!')
title_url_queue = []
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
YDL_OPTIONS = {'format': 'bestaudio', '--yes-playlist': True,
               '--flat-playlist': True, '--ignore-errors': True}


# check if bot is ready
@client.event
async def on_ready():
    print('Bot is online')


# loop that checks every second if the voice has stopped playing and if there is something in queue,
# it plays first audio from the queue
@tasks.loop(seconds=3.0, count=None)
async def play_from_queue():
    voice = get(client.voice_clients)
    if title_url_queue and not voice.is_playing() and not voice.is_paused():
        play_url(voice)


@client.command(help="connects bot to a voice channel if it's not and palys the URL")
async def paly(ctx, request):
    await play(ctx, request)


def play_from_favs(n):
    # adding to the queue n random songs from fav
    df = pd.read_csv('favs.csv')
    sample = df.sample(n)
    for i, song in sample.iterrows():
        title_url_queue.append((song.name, song.url))


def play_from_query(ctx, msg):
    # composing url
    search_request = msg.lower().replace(' ', '+').replace('–', '-').replace('\n', '')

    # making requests in russian and ukrainian work using transliteration
    for i in msg:
        # .isascii()
        if i in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяіїє':
            search_request = urllib.parse.quote(search_request, encoding='utf-8')
            break

    # getting the html of search result
    html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + search_request.replace("'", ""))

    # finding all the videos
    video_ids = findall(r"watch\?v=(\S{11})", html.read().decode())

    # composing the url of the first video
    url = "https://www.youtube.com/watch?v=" + video_ids[0]
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
    if request.startswith('https://www.youtube.com/watch?v=') or request.startswith('https://youtu.be'):
        url = request
    # playing n random songs from fav
    elif request.startswith('fav'):
        # finding n
        n = findall(r'\d{1,3}', msg)
        if not n:
            n = 15
        else:
            n = int(n[0])

        play_from_favs(n)

        return
    # playing top video from YT found by given request
    else:
        url = play_from_query(ctx, msg)

    # playing the audio or adding it to the queue
    title = get_title(url)
    title_url_queue.append((title, url))
    if not voice.is_playing():
        play_url(voice, url)
        await ctx.send("Bot is playing!")
    else:
        await ctx.send("Added to the queue!")


@client.command(help="plays video instantly")
async def instant(ctx, request):
    await play(ctx, request)
    if title_url_queue:
        await move(ctx)
        await skip(ctx)


# command to play video after the one that's playing now
@client.command(help="plays video after the one that's playing now")
async def next(ctx, request):
    await play(ctx, request)
    if title_url_queue:
        await move(ctx)


# command to add video at position n to the favorite
@client.command(help="adds video at position n to the favorite")
async def fav(ctx, n=0):
    id = ctx.message.guild.id
    voice = get(client.voice_clients, guild=ctx.guild)

    # position is not specified, so we take the song that is playing right now
    if n == 0 and voice.is_playing():
        title = title_now
        url = url_now
    # position is specified
    elif int(n) <= len(title_url_queue):
        title = title_url_queue[n - 1][0]
        url = title_url_queue[n - 1][1]
    else:
        await ctx.send(f'Length of the queue is only {len(title_url_queue)}, therefore there is no position {n}')
        return

    df = pd.read_csv('favs.csv')
    if title not in df.name:
        df.loc[df.shape[0]] = pd.Series({"url": url, "name": title})
        df.to_csv('favs.csv', index=False)
    else:
        await ctx.send(f'The {title} is already in the favorites')


# command to show the favorites
@client.command(help="shows the content of the 'favorite'")
async def favs(ctx):
    # getting id of a channel the command was called in
    id = ctx.message.guild.id
    # getting the string that contains favorites
    with open(f'favs.txt', 'r') as file:
        fav_titles = file.read().splitlines()[::2]
        string_favs = "Favorites:\n"
        for index, title in enumerate(fav_titles):
            string_favs = string_favs + f'{index + 1}. {title}\n'

    # splitting the string into blocks under 2000 chars in length
    string_favs = fit_text_in_msg(string_favs)
    for text_block in string_favs.split('@'):
        await ctx.send(text_block)


# command to remove the video at position n from the favorites
@client.command(help="removes the video at specified position from the favorites")
async def removef(ctx, n):
    # getting id of a channel the command was called in
    id = ctx.message.guild.id
    n = int(n)

    # reading the favorites file
    with open(f'favs.txt', 'r') as file:
        lines = file.read().splitlines()
        fav_titles = lines[::2]
        fav_url = lines[1::2]
        if len(fav_titles) >= n and n >= 0:
            # modifying the favorites file
            with open(f'favs.txt', 'w') as file:
                for line in lines:
                    if line != fav_titles[n - 1] and line != fav_url[n - 1]:
                        file.write(line + '\n')
            await ctx.send(f"Good decison! I don't like {fav_titles[n - 1]} too!")
        else:
            await ctx.send(f'Length of the favorites is only {len(fav_titles)}, therefore there is no position {n}')


# command to resume voice if it is paused
@client.command(help="Resumes playing")
async def resume(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if not voice.is_playing():
        voice.resume()
        await ctx.send('Bot is resuming')
    else:
        await ctx.send("Nothing is playing")


# command to pause voice if it is playing
@client.command(help="Pauses the music")
async def pause(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
        await ctx.send('Bot has been paused')
    else:
        await ctx.send("Nothing is playing")


# command to stop voice
@client.command(help="Skips the current song")
async def skip(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.stop()
        await ctx.send('Skipping...')
    else:
        await ctx.send("Nothing is playing")


# command to shuffle the queue
@client.command(help="Shuffles the queue")
async def shuffle(ctx):
    if title_url_queue:
        random.shuffle(title_url_queue)
        await ctx.send('Queue is shuffled')
    else:
        await ctx.send("There is nothing in the queue")


# command to clear the queue
@client.command(help="Clears the queue")
async def clear(ctx):
    if title_url_queue:
        title_url_queue.clear()
        await ctx.send("Миша, всё ху*ня, давай по новой...")
    else:
        await ctx.send("There is nothing in the queue")


# command to remove the video at position n from the queue
@client.command(help="removes the video at specified position from the queue")
async def remove(ctx, n=len(title_url_queue)):
    n = int(n)
    if len(title_url_queue) >= n and n >= 0:
        await ctx.send(f"Good decison! I don't like {title_url_queue[n - 1][0]} too!")
        title_url_queue.pop(n - 1)
    else:
        await ctx.send(f'Length of the queue is only {len(title_url_queue)}, therefore there is no position {n}')


# command to move the video at the position n to the position k in the queue
@client.command(help="moves the video at the position 'first number' to the position 'second number' in the queue")
async def move(ctx, n=len(title_url_queue), k=1):
    n = int(n)
    k = int(k)
    bigger = n if n >= k else k
    smaller = k if n >= k else n
    flag = False

    if n == k:
        await ctx.send(
            f"Are you drunk?! You do know that moving song from position {n} to position {k} is pointless, don't you?")
    elif len(title_url_queue) >= bigger and smaller >= 0:
        title_url_queue.insert(k - 1, title_url_queue.pop(n - 1))
        flag = True
    else:
        await ctx.send(f'Length of the queue is only {len(title_url_queue)}, therefore there is no position {bigger}')

    if flag:
        if smaller == k or k == 1:
            await ctx.send(
                f"I'm totally with you on that one! We should listen to {title_url_queue[k - 1][0]} earlier!")
        else:
            await ctx.send(f"I agree with you! We don't need to rush with listening {title_url_queue[k - 1][0]}!")


# command to display a queue in chat
@client.command(help="displays a queue in chat")
async def queue(ctx):
    if title_url_queue:
        string_queue = "Queue:\n"
        for index, title_url in enumerate(title_url_queue):
            string_queue = string_queue + f'{index + 1}. {title_url[0]}\n'

        if len(string_queue) >= 2000:
            # splitting the string into blocks under 2000 chars in length
            string_queue = fit_text_in_msg(string_queue)
            for text_block in string_queue.split('@'):
                await ctx.send(text_block)
        else:
            await ctx.send(string_queue)
    else:
        await ctx.send("There is nothing in the queue")


# command to display what video is playing right now
@client.command(help="displays what video is playing right now")
async def np(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        await ctx.send(f'"{title_now}" is playing right now.')


# command to replay the video that is playing right now
@client.command(help="replays the video that is playing right now")
async def replay(ctx):
    voice = get(client.voice_clients, guild=ctx.guild)
    voice.stop()
    play_url(voice, "replay")
    await ctx.send(f"Let's listen to {title_now} again!")


# command to play winning songs
@client.command(help="plays winning songs")
async def champ(ctx):
    with open('champ.txt', 'r') as file:
        content = file.readlines()
        url = random.choice(content)
        await instant(ctx, url)


def play_url(voice, URL=None):
    if title_url_queue and URL != "replay" or not URL and URL != "replay":
        global url_now, title_now
        title_now, url_now = title_url_queue.pop(0)
        URL = url_now
    print(URL, get_title(URL))
    # transforming URL to the right format
    with YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(URL, download=False)
    URL = info['url']
    # playing URL
    voice.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS))
    voice.is_playing()


def get_title(URL):
    # getting the html of the URL
    fp = urllib.request.urlopen(URL)
    mybytes = fp.read()
    html = mybytes.decode("utf8")
    fp.close()

    # finding the title
    title = findall(r'{"title":{"simpleText":".{,100}"},"subtitle":{', html)
    try:
        title = title[0][24:-15:]
    except IndexError:
        print(f"Unable to find the title")

    return title


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


# starting 'play_from_queue' loop
play_from_queue.start()

# keep alive the server
# keep_alive()

# starting the bot
client.run("ODg4MTAwODMyODgzNjU4ODAy.YUNyWg.dCLPmbHUI9Jo-FhkWtLKiQGulgA")
