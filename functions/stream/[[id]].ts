interface Channel {
    id: string;
    name: string;
    stream: string;
    headers: any;
}

export const onRequest: PagesFunction = async (context) => {
    if (context.params.id.length === 0) {
        return new Response("Invalid channel id", { status: 400 });
    }
    if (context.params.id.length === 1) {
        return new Response("Invalid stream url", { status: 400 });
    }

    const requestUrl = new URL(context.request.url);
    const localUrl = requestUrl.protocol + "//" + requestUrl.hostname + ":" + requestUrl.port;
    const channelId = context.params.id[0];
    const channel = await fetchChannel(localUrl, channelId);
    if (context.params.id[1] == "playlist.m3u8") {
        const playlist = await fetchChannelMainPlaylist(channel);
        return new Response(playlist);
    } else if (context.params.id[1] == "chunk") {
        const chunkUrl = requestUrl.searchParams.get("url");
        const chunk = await fetchChannelChunk(channel, chunkUrl);
        return new Response(chunk);
    } else {
        return new Response("Invalid stream url", { status: 400 });
    }
};

const fetchChannel = async (localUrl: string, channelId: string): Promise<Channel> => {
    const url = `${localUrl}/channels/${channelId}.json`;
    console.log(`Fetching channel from ${url}`);
    return await (await fetch(url)).json() as Channel;
}

const fetchChannelMainPlaylist = async (channel: Channel): Promise<string> => {
    return await fetchChannelPlaylist(channel, channel.stream);
}

const fetchChannelPlaylist = async (channel: Channel, playlist: string): Promise<string> => {
    const response = await fetch(playlist, { headers: channel.headers });
    const content = await response.text();
    const streamBaseUrl = streamBaseUrlFromPlaylistUrl(response.url);
    return patchM3U8(content, (url) => {
        const chunkUrl = new URL(streamBaseUrl + "/" + url);
        return `chunk?url=${encodeURIComponent(chunkUrl.toString())}`;
    });
}

const fetchChannelChunk = async (channel: Channel, chunkUrl: string): Promise<any> => {
    const url = new URL(chunkUrl);
    if (url.pathname.endsWith(".m3u8")) {
        return await fetchChannelPlaylist(channel, chunkUrl);
    } else {
        const response = await fetch(chunkUrl, { headers: channel.headers });
        return response.body;
    }
}

const patchM3U8 = (m3u8: string, urlMapper: (url: string) => string) => {
    let lines = m3u8.split("\n");
    let patchedM3u8 = "";
    for (const line of lines) {
        if (line.trim() === "" || line.startsWith("#")) {
            patchedM3u8 += line + "\n";
        } else {
            patchedM3u8 += urlMapper(line) + "\n";
        }
    }
    return patchedM3u8;
}

// for an input like 'https://linear417-gb-hls1-prd-ak.cdn.skycdp.com/100e/Content/HLS_001_1080_30/Live/channel(skynews)/index_1080-30.m3u8'
// it should return 'https://linear417-gb-hls1-prd-ak.cdn.skycdp.com/100e/Content/HLS_001_1080_30/Live/channel(skynews)'
const streamBaseUrlFromPlaylistUrl = (streamUrl: string) => {
    if (streamUrl.endsWith("/"))
        streamUrl = streamUrl.substring(0, streamUrl.length - 1);
    return streamUrl.substring(0, streamUrl.lastIndexOf('/'));
}