import json
import logging
import os
import csv
import requests

from io import BytesIO
from PIL import Image
from dataclasses import dataclass

DATABASE_URL = "https://raw.githubusercontent.com/iptv-org/database/refs/heads/master/data/channels.csv"
STREAMS_URL = (
    "https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/pt.m3u"
)
PORTUGAL_ID = "PT"


@dataclass
class DatabaseEntry:
    id: str
    name: str
    country: str
    closed: bool
    logo: str


@dataclass
class StreamEntry:
    id: str
    stream: str


@dataclass
class Channel:
    id: str
    name: str
    country: str
    logo: str
    stream: str


def download_database() -> list[DatabaseEntry]:
    response = requests.get(DATABASE_URL)
    response.raise_for_status()  # Ensure we notice bad responses

    entries = []
    csv_content = response.text.splitlines()
    reader = csv.DictReader(csv_content)
    for row in reader:
        entry = DatabaseEntry(
            id=row["id"],
            name=row["name"],
            country=row["country"],
            closed=row["closed"].lower() == "true",
            logo=row["logo"],
        )
        entries.append(entry)

    return entries


def download_streams() -> list[StreamEntry]:
    response = requests.get(STREAMS_URL)
    response.raise_for_status()  # Ensure we notice bad responses

    entries = []
    lines = response.text.splitlines()
    for i in range(len(lines)):
        if lines[i].startswith("#EXTINF"):
            tvg_id = lines[i].split('tvg-id="')[1].split('"')[0]
            stream = lines[i + 1].strip()
            if stream.startswith("#"):
                stream = lines[i + 2].strip()
            entries.append(StreamEntry(id=tvg_id, stream=stream))

    return entries


def merge_entries(
    database: list[DatabaseEntry], streams: list[StreamEntry]
) -> list[Channel]:
    channels = []
    for stream in streams:
        if any(channel.id == stream.id for channel in channels):
            continue
        for entry in database:
            if stream.id == entry.id:
                channel = Channel(
                    id=entry.id,
                    name=entry.name,
                    country=entry.country,
                    logo=entry.logo,
                    stream=stream.stream,
                )
                channels.append(channel)
                break

    return channels


def download_channel_logos(channels: list[Channel]):
    if not os.path.exists("./public/logos"):
        os.makedirs("./public/logos")

    for channel in channels:
        try:
            response = requests.get(
                channel.logo,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0"
                },
            )
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            image_path = f"./public/logos/{channel.id}.webp"
            if not os.path.exists(image_path):
                image.save(image_path, "WEBP")
        except Exception as e:
            logging.warning(f"Failed to download logo for {channel.name}: {e}")


def sort_channels(channels: list[Channel]) -> list[Channel]:
    priority_prefixes = ["rtp", "sic", "artv", "tvi"]
    priority_channels = []
    other_channels = []
    for channel in channels:
        if channel.name.lower().startswith(tuple(priority_prefixes)):
            priority_channels.append(channel)
        else:
            other_channels.append(channel)
    return priority_channels + other_channels


def main():
    logging.basicConfig(level=logging.WARNING)

    database_entries = download_database()
    stream_entries = download_streams()
    channels = merge_entries(database_entries, stream_entries)
    channels = sort_channels(channels)
    download_channel_logos(channels)
    with open("./public/channels.json", "w") as file:
        json.dump([channel.__dict__ for channel in channels], file, indent=4)


if __name__ == "__main__":
    main()
