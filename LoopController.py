''' IMPORTS '''

from discord.ext import tasks
from datetime import datetime
from pytz import timezone

import Guilds
from Logger import log


''' LOOPS '''

@tasks.loop(minutes=1)
async def send_reminders(client):
    """
    """
    
    now = timezone("UTC").localize(datetime.utcnow())

    for r in await Guilds.get_reminders(client):

        d = r.date.astimezone(timezone("UTC")) 
        if d.strftime("%Y%d%m%H%M") == now.strftime("%Y%d%m%H%M"):

            await r.send(client)

            log("Reminder", f"Sent: {r.to_string()}")
# end update_items_loopimport discord