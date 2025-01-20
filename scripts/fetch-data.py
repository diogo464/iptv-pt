import json
import logging
import os
import csv
import re
import requests
import unicodedata

from io import BytesIO
from PIL import Image
from dataclasses import dataclass

DATABASE_FILE = "channels.csv"
DATABASE_URL = "https://raw.githubusercontent.com/iptv-org/database/refs/heads/master/data/channels.csv"
STREAMS_FILE = "pt.m3u"
STREAMS_URL = (
    "https://raw.githubusercontent.com/LITUATUI/M3UPT/refs/heads/main/M3U/M3UPT.m3u"
)
PORTUGAL_ID = "PT"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0"


@dataclass
class StreamEntry:
    id: str
    name: str
    stream: str
    logo: str | None
    headers: dict[str, str]


@dataclass
class Channel:
    id: str
    name: str
    country: str
    logo: str
    stream: str
    headers: dict[str, str]


def normalize_id(id: str) -> str:
    # https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-normalize-in-a-python-unicode-string
    nfkd_form = unicodedata.normalize("NFKD", id)
    only_ascii = nfkd_form.encode("ASCII", "ignore").decode("utf-8")
    return only_ascii.replace(" ", "").replace("&", "")


def parse_m3u(content: str) -> list[StreamEntry]:
    entries = []
    metadata_lines = []
    for line in content.splitlines():
        line = line.strip()
        if line == "":
            metadata_lines.clear()
            continue

        if line.startswith("#"):
            metadata_lines.append(line)
            continue

        if len(metadata_lines) > 0 and "tvg-id" not in metadata_lines[0]:
            continue

        stream = line
        headers = {}
        for metadata_line in metadata_lines:
            if metadata_line.startswith("EXTVLCOPT:http-user-agent="):
                headers["User-Agent"] = metadata_line.split("=")[1]
            elif metadata_line.startswith("#EXTVLCOPT:http-referrer="):
                headers["Referer"] = metadata_line.split("=")[1]

        if "User-Agent" not in headers:
            headers["User-Agent"] = USER_AGENT

        if len(metadata_lines) == 0:
            logging.warning(f"Stream without metadata: {line}")
            continue

        name = metadata_lines[0].split(",")[-1]

        id_match = re.search(r'tvg-id="([^"]+)"', metadata_lines[0])
        if id_match is not None:
            tvg_id = id_match.group(1)
        else:
            tvg_id = name
        tvg_id = normalize_id(tvg_id)

        if tvg_id == "":
            logging.warning(f"Stream without tvg-id: {metadata_lines[0]}")
            continue

        logo_match = re.search(r'tvg-logo="([^"]*)"', metadata_lines[0])
        if logo_match is not None and logo_match.group(1) != "":
            logo = logo_match.group(1)
        else:
            logo = None

        entries.append(
            StreamEntry(id=tvg_id, name=name, stream=stream, logo=logo, headers=headers)
        )

    return entries


def download_streams() -> list[StreamEntry]:
    if os.path.exists(STREAMS_FILE):
        with open(STREAMS_FILE, "r") as file:
            content = file.read()
    else:
        response = requests.get(STREAMS_URL)
        response.raise_for_status()  # Ensure we notice bad responses
        content = response.text
        with open(STREAMS_FILE, "w") as file:
            file.write(content)

    return parse_m3u(content)


def download_channel_logos(streams: list[StreamEntry]):
    if not os.path.exists("./public/logos"):
        os.makedirs("./public/logos")

    for stream in streams:
        if stream.logo is None:
            continue

        try:
            response = requests.get(
                stream.logo,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0"
                },
            )
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            image_path = f"./public/logos/{stream.id}.webp"
            if not os.path.exists(image_path):
                image.save(image_path, "WEBP")
        except Exception as e:
            logging.warning(
                f"Failed to download logo for {stream.name} at {stream.logo}: {e}"
            )


def sort_channels(channels: list[Channel]) -> list[Channel]:
    priority_prefixes = ["rtp", "sic", "artv", "tvi", "cnn"]
    priority_channels = []
    other_channels = []
    for channel in channels:
        if channel.name.lower().startswith(tuple(priority_prefixes)):
            priority_channels.append(channel)
        else:
            other_channels.append(channel)
    return priority_channels + other_channels


def streams_to_channels(streams: list[StreamEntry]) -> list[Channel]:
    channels = []
    for stream in streams:
        country = PORTUGAL_ID
        name = stream.name
        id = stream.id
        logo = stream.logo
        stream_url = stream.stream
        headers = stream.headers
        channels.append(Channel(id, name, country, logo, stream_url, headers))
    return channels


def main():
    logging.basicConfig(level=logging.WARNING)

    streams = download_streams()
    channels = streams_to_channels(streams)
    channels = sort_channels(channels)
    download_channel_logos(channels)
    with open("./public/channels.json", "w") as file:
        json.dump([channel.__dict__ for channel in channels], file, indent=4)


if __name__ == "__main__":
    main()
