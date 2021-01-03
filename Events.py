''' IMPORTS '''

import asyncio
import discord
import traceback


import Database
import Logger
from Logger import log
import Support
from Support import simple_bot_response



''' CONSTANTS '''

playlist_aliases = ["playlist", "pl"]
race_aliases = ["race"]
event_aliases = ["event", "events"] + race_aliases + playlist_aliases


''' CLASS '''
class Event:
    def __init__():
        pass
    # end __init__
# end Event


''' FUNCTIONS '''

async def main(client, message, args, author_perms):
    """
        @jc _command_
    """

    if args[0] in Support.create_aliases:
        await create_event(client, message, args[1:])

# end main


async def create_event(client, message, args):
    pass
# end create_event