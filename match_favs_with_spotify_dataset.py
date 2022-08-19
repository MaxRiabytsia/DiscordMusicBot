import urllib.request
from re import findall
import pandas as pd
import os
import json


def get_urls(query):
    # composing url
    search_request = query.lower().replace(' ', '+').replace('–', '-').replace('\n', '')
    # making requests in ukrainian and russian work
    if not query.isascii():
        search_request = urllib.parse.quote(search_request, encoding='utf-8')
    url = "https://www.youtube.com/results?search_query=" + search_request.replace("'", "")

    # getting the html of search result
    html = urllib.request.urlopen(url)

    # finding all the videos
    video_ids = findall(r"watch\?v=(\S{11})", html.read().decode())
    # composing the url of the first video
    urls = []
    for i in video_ids[:2]:
        url = "https://www.youtube.com/watch?v=" + i
        urls.append(url)

    return urls


def match_titles(favs, spotify, old_matched_favs, spotify_title_urls_dict, favs_title_urls_dict):
    if old_matched_favs is not None:
        matched_favs = old_matched_favs
    else:
        matched_favs = pd.DataFrame(columns=["favs_title", "spotify_title", "url"])

    for i, row in favs.iterrows():
        if i % 10 == 0:
            print(f"{i / favs.shape[0] * 100}%")

        if old_matched_favs is not None and row.title in old_matched_favs.favs_title.unique():
            continue

        favs_urls = favs_title_urls_dict[row.title]

        is_match_found = False
        spotify_title = None
        for spotify_title in spotify.title.unique():
            spotify_urls = spotify_title_urls_dict[spotify_title]
            if len(set(favs_urls).intersection(set(spotify_urls))) != 0:
                is_match_found = True
                break

        if is_match_found:
            matched_favs.loc[matched_favs.shape[0]] = pd.Series({
                "favs_title": row.title,
                "spotify_title": spotify_title,
                "url": row.url})

    return matched_favs


def get_spotify_title_urls_dict(spotify):
    spotify_title_urls_dict = {}
    sorted_uniques = spotify.groupby(spotify.title, as_index=False).count().sort_values(by='user_id', ascending=False)
    sorted_uniques = sorted_uniques.reset_index()
    n_of_uniques = sorted_uniques.shape[0]
    for index, row in sorted_uniques.iterrows():
        spotify_title = row.title
        if spotify_title not in spotify_title_urls_dict:
            if index % 1000 == 0:
                print(f"{round(index / n_of_uniques * 100, 2)}%")
                with open("data/spotify_title_urls_dict.json", "w") as json_file:
                    json.dump(spotify_title_urls_dict, json_file)
            spotify_title_urls_dict[spotify_title] = get_urls(spotify_title)

    with open("data/spotify_title_urls_dict.json", "w") as json_file:
        json.dump(spotify_title_urls_dict, json_file)

    return spotify_title_urls_dict


def get_favs_title_urls_dict(favs):
    favs_title_urls_dict = {}
    for index, row in favs.iterrows():
        favs_title = row.title
        if favs_title not in favs_title_urls_dict:
            if index % 10 == 0:
                print(f"{round(index / favs.shape[0] * 100, 2)}%")
                with open("data/favs_title_urls_dict.json", "w") as json_file:
                    json.dump(favs_title_urls_dict, json_file)
            favs_title_urls_dict[favs_title] = get_urls(favs_title)

    with open("data/favs_title_urls_dict.json", "w") as json_file:
        json.dump(favs_title_urls_dict, json_file)

    return favs_title_urls_dict


def main():
    favs = pd.read_csv("data/favs.csv")
    spotify = pd.read_csv("data/spotify_dataset.csv")
    spotify["title"] = spotify.artistname + " " + spotify.trackname
    spotify = spotify.drop(columns=["artistname", "trackname"])
    print(spotify.title.unique().shape)

    data_folder = os.listdir("data")
    if "matched_favs.csv" in data_folder:
        old_matched_favs = pd.read_csv("data/matched_favs.csv")
    else:
        old_matched_favs = None

    if "spotify_title_urls_dict.json" in data_folder:
        with open("data/spotify_title_urls_dict.json") as json_file:
            spotify_title_urls_dict = json.load(json_file)
    else:
        spotify_title_urls_dict = get_spotify_title_urls_dict(spotify)

    if "favs_title_urls_dict.json" in data_folder:
        with open("data/favs_title_urls_dict.json") as json_file:
            favs_title_urls_dict = json.load(json_file)
            if len(favs_title_urls_dict) != favs.shape[0]:
                favs_title_urls_dict = get_favs_title_urls_dict(favs)
    else:
        favs_title_urls_dict = get_favs_title_urls_dict(favs)

    matched_favs = match_titles(favs, spotify, old_matched_favs, spotify_title_urls_dict, favs_title_urls_dict)
    matched_favs.to_csv("data/matched_favs.csv", index=False)


if __name__ == "__main__":
    main()
