import asyncio
import json
import os
import re

import requests
import yt_dlp
from PIL import Image

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager
)

UPLOAD_DIR = "upload"
DATA_FILE = "data.json"

UPLOAD_URL = "YourWebServ" #You can use any free web hosting platform, just drop the "upload_image.php file and modify the token
UPLOAD_TOKEN = "Uploadfiletoken" 


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def safe_filename(value):
    value = re.sub(r'[<>:"/\\|?*]', "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:120]


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def format_time(seconds):
    if seconds is None:
        return "--:--"

    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def timespan_to_seconds(value):
    if value is None:
        return None

    return value.total_seconds()


async def get_media_info():
    manager = await MediaManager.request_async()
    session = manager.get_current_session()

    if session is None:
        return None

    properties = await session.try_get_media_properties_async()
    timeline = session.get_timeline_properties()
    playback = session.get_playback_info()

    return {
        "title": properties.title or "",
        "artist": properties.artist or "",
        "album": properties.album_title or "",
        "position": timespan_to_seconds(timeline.position),
        "duration": timespan_to_seconds(timeline.end_time),
        "status": str(playback.playback_status)
    }


def search_youtube(title, artist):
    query = f"{artist} {title} official audio"

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "default_search": "ytsearch",
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        result = ydl.extract_info(
            f"ytsearch1:{query}",
            download=False
        )

    entries = result.get("entries") or []

    if not entries:
        return None

    video = entries[0]

    return {
        "youtube_title": video.get("title"),
        "youtube_url": video.get("url") or video.get("webpage_url"),
        "video_id": video.get("id"),
        "channel": video.get("uploader") or video.get("channel")
    }


def get_best_thumbnail_url(video_id):
    urls = [
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 200 and len(response.content) > 1000:
                return response.content

        except requests.RequestException:
            pass

    return None


def save_local_png(track_key, image_data):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    filename = safe_filename(f"{track_key}.png")
    local_path = os.path.join(UPLOAD_DIR, filename)

    temp_path = local_path + ".tmp"

    with open(temp_path, "wb") as file:
        file.write(image_data)

    try:
        image = Image.open(temp_path).convert("RGB")
        image.save(local_path, "PNG")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return local_path


def upload_cover(local_path):
    try:
        with open(local_path, "rb") as file:
            files = {
                "image": (os.path.basename(local_path), file, "image/png")
            }

            data = {
                "token": UPLOAD_TOKEN
            }

            response = requests.post(
                UPLOAD_URL,
                files=files,
                data=data,
                timeout=20
            )

        result = response.json()

        if response.status_code == 200 and result.get("success"):
            return result.get("url")

        print(
            "Upload error:",
            result.get("error", response.text)
        )

    except Exception as error:
        print("Upload error :", error)

    return None


def process_track(media):
    title = media["title"].strip()
    artist = media["artist"].strip()

    if not title:
        return None

    track_key = safe_filename(f"{artist} - {title}")

    data = load_data()
    existing = data.get(track_key)

    if existing and existing.get("cover_url"):
        print("Track already save.")
        return existing

    print(f"Recherche YouTube : {artist} - {title}")

    video = search_youtube(title, artist)

    if video is None:
        print("No Youtube video avaible.")
        return None

    image_data = get_best_thumbnail_url(video.get("video_id"))

    if image_data is None:
        print("Unable to retrieve the thumbnail")
        return None

    local_path = save_local_png(track_key, image_data)
    cover_url = upload_cover(local_path)

    if not cover_url:
        print("Unable to contact the server")
        return None

    print(f"Pochette en ligne : {cover_url}")

    track_data = {
        "title": title,
        "artist": artist,
        "album": media["album"],
        "youtube_title": video.get("youtube_title"),
        "youtube_url": video.get("youtube_url"),
        "youtube_channel": video.get("channel"),
        "youtube_video_id": video.get("video_id"),
        "cover_local_path": local_path.replace("\\", "/"),
        "cover_filename": os.path.basename(local_path),
        "cover_url": cover_url
    }

    data[track_key] = track_data
    save_data(data)

    return track_data


def display_media(media, track_data):
    clear_console()

    print("=" * 64)
    print("YOUTUBE ")
    print("=" * 64)

    if track_data:
        print(f"Titre           : {track_data['title']}")
        print(f"Artiste         : {track_data['artist']}")
        print(f"Vidéo YouTube   : {track_data['youtube_title']}")
        print(f"Chaîne          : {track_data['youtube_channel']}")
        print(f"Lien            : {track_data['youtube_url']}")
        print(f"Pochette online : {track_data['cover_url']}")
    else:
        print("No data avaible.")

    print()
    print(f"Titre Deezer    : {media['title']}")
    print(f"Artiste Deezer  : {media['artist']}")
    print(f"Statut          : {media['status']}")
    print(
        f"Temps           : "
        f"{format_time(media['position'])} / "
        f"{format_time(media['duration'])}"
    )
    print("=" * 64)
    print("Ctrl + C for leave")


async def main():
    last_track = None
    track_data = None

    while True:
        try:
            media = await get_media_info()

            if media is None:
                clear_console()
                print("No reads detected")
                print("Open Deezer an launch song")

            else:
                current_track = (
                    media["title"],
                    media["artist"]
                )

                if current_track != last_track:
                    last_track = current_track
                    track_data = process_track(media)

                display_media(media, track_data)

        except Exception as error:
            clear_console()
            print("[ERREUR]", error)

        await asyncio.sleep(2)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStop")