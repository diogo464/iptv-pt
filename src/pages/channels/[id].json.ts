import type { APIRoute } from 'astro';
import { getChannelById, getChannels } from '../../scripts/channels';

const channels = getChannels();

export const GET: APIRoute = ({ params, request }) => {
    const id = params.id;
    if (id === undefined)
        throw new Error('No channel id provided');
    
    const channel = getChannelById(id);
    return new Response(
        JSON.stringify(channel),
        {
            headers: {
                'Content-Type': 'application/json'
            }
        }
    )
}

export function getStaticPaths() {
    return channels.map((channel) => { return { params: { id: channel.id } }; });
}