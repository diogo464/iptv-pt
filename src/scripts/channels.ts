import data from '../../public/channels.json';

export interface Channel {
    id: string;
    name: string;
    logo: string;
    stream: string;
    headers: any;
}

export function getChannels(): Channel[] {
    let channels = [];
    for (const value of data) {
        channels.push({
            id: value.id,
            name: value.name,
            logo: value.logo,
            stream: value.stream,
            headers: value.headers,
        });
    }
    return channels;
}

export function getChannelById(id: string): Channel {
    const channel = getChannels().find((channel) => channel.id === id);
    if (channel === undefined)
        throw new Error(`Channel with id ${id} not found`);
    return channel;
}

export function getChannelLogoPath(channel: Channel): string {
    return `/logos/${channel.id}.webp`;
}