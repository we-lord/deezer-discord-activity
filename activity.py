import asyncio
import time

from pypresence import AioPresence
from pypresence.exceptions import DiscordNotFound

from task import (
    get_media_info,
    process_track,
    format_time
)

CLIENT_ID = "YOURAPPLICATIONTOKEN"


async def connect_discord():
    try:
        rpc = AioPresence(CLIENT_ID)
        await rpc.connect()
        print("[OK] Login to Discord")
        return rpc

    except DiscordNotFound:
        raise RuntimeError("Discord is not open")

    except Exception as error:
        raise RuntimeError(f"Unable to connect to Discord: {error}")


async def update_discord(rpc, media, track_data, track_start):
    title = media["title"]
    artist = media["artist"]
    album = media["album"]

    payload = {
        "details": title or "Data not available",
        "state": artist or "Data not available",
        "start": track_start,
        "activity_type": 2,
        "large_text": album or "Listening"
    }

    if track_data and track_data.get("cover_url"):
        payload["large_image"] = track_data["cover_url"]

    if track_data and track_data.get("youtube_url"):
        payload["buttons"] = [
            {
                "label": "Listen on YouTube",
                "url": track_data["youtube_url"]
            }
        ]

    try:
        await rpc.update(**payload)

    except Exception as error:
        print(f"[Playload unable : {error}")

        try:
            await rpc.update(
                details=payload["details"],
                state=payload["state"],
                start=track_start,
                activity_type=2
            )
            print("Activity Send")

        except Exception as fallback_error:
            print(f"Fallback unable : {fallback_error}")


async def activity_loop(rpc):
    last_track = None
    track_data = None
    track_start = int(time.time())

    while True:
        try:
            media = await get_media_info()

            if media is None:
                await rpc.clear()
                last_track = None
                track_data = None

            else:
                current_track = (
                    media["title"],
                    media["artist"]
                )

                if current_track != last_track:
                    last_track = current_track
                    track_start = int(time.time())
                    track_data = process_track(media)

                await update_discord(rpc, media, track_data, track_start)

                print(
                    f"[MUSIQUE] {media['artist']} - {media['title']} "
                    f"({format_time(media['position'])} / "
                    f"{format_time(media['duration'])})"
                )

        except Exception as error:
            print("[ERREUR]", error)

        await asyncio.sleep(15)


async def main():
    rpc = await connect_discord()
    await activity_loop(rpc)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStop.")