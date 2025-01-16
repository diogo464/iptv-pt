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
        const m3u8 = await fetchM3U8(channel);
        return new Response(m3u8);
    }

    const streamBaseUrl = channel.stream.substring(0, channel.stream.lastIndexOf('/'));
    const requestQuery = requestUrl.searchParams.toString();

    let downloadUrl = streamBaseUrl + "/" + context.params.id.slice(1).join("/");
    if (requestQuery.length > 0) {
        downloadUrl += "?" + requestQuery;
    }

    console.log(`Downloading ${downloadUrl}`);
    return await fetch(downloadUrl, { headers: channel.headers });
};

const fetchChannel = async (localUrl: string, channelId: string) => {
    const url = `${localUrl}/channels/${channelId}.json`;
    console.log(`Fetching channel from ${url}`);
    return await (await fetch(url)).json() as Channel;
}

const fetchM3U8 = async (channel: Channel) => {
    console.log(`Fetching m3u8 for ${channel.name} from ${channel.stream}`);
    const m3u8 = await (await fetch(channel.stream, { headers: channel.headers })).text();
    return m3u8;
}