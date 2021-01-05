# TODO BREAK WEEKS!!!


''' IMPORTS '''

import asyncio
from datetime import datetime
from dateutil.relativedelta import relativedelta
import discord
import re
import string
import traceback
import validators

from pytz import timezone


import Database
from Database import replace_chars
import Guilds
import Logger
from Logger import log
import Support
from Support import get_jc_from_channel, simple_bot_response
import Whitelist



''' CONSTANTS '''

playlist_aliases = ["playlist", "pl"]
race_aliases = ["race", "oneoff", "one-off"]
championship_aliases = ["league", "championship"]
time_trial_aliases = ["timetrial", "tt", "time-trial"]
event_aliases = ["event", ] + championship_aliases + race_aliases + playlist_aliases + time_trial_aliases

calendar_aliases = ["calendar", "cal", "events"]

event_types = ["playlist", "one-off", "championship", "time-trial"]
platforms = ["Xbox", "PC", "PS", "Cross-Platform"]

time_zones = {
    "North America" : [
        {"Los Angeles" : "US/Pacific"}, 
        {"Denver" : "US/Mountain"}, 
        {"Chicago" : "US/Central"}, 
        {"New York" : "US/Eastern"}, 
    ],

    "South America" : [
        {"Buenos Aires" : "America/Argentina/Buenos_Aires"},
    ],

    "Europe" : [
        {"UTC" : "UTC"},
        {"London" : "Europe/London"},
        {"Amsterdam" : "Europe/Amsterdam"},
    ],

    "Asia" : [
        {"Vientiane" : "Asia/Vientiane"},
        {"Japan" : "Japan"},
    ],

    "Australia" : [
        {"Queensland" : "Australia/Queensland"},
        {"Sydney" : "Australia/Sydney"},
    ],
}

time_format1 = "%Y-%m-%d %I:%M %p"



''' CLASS '''
class Event:
    def __init__(self, event_id=None, guild_id=None, creator_id=None, editor_id=None, event_type=None, platform=None, name=None, details=None, time_zone=None, start_date=None, end_date=None, duration=None, repeating=None, break_weeks=[], invite_link=None):
        self.id = event_id

        self.guild_id = guild_id
        self.guild = None

        self.creator_id = creator_id
        self.creator = None

        self.editor_id = editor_id
        self.editor = None

        self.type = event_type
        self.platform = platform
        self.name = name
        self.details = details
        self.time_zone = time_zone # timezone()
        self.start_date = start_date # datetime.datetime() -- time_format1 (constant)
        self.start_date_utc = None
        self.end_date = end_date # as a date (not time), same as start, none, new date
        self.duration = duration # as seconds
        self.repeating = repeating # as days -- Weekly, Every N Weeks, Never
        self.break_weeks = break_weeks
        self.invite_link = invite_link # jc_guild.invite_link

        self.edited = False
        self.embed = None
        self.messages = []
        self.weeks = []
    # end __init__


    def get_weeks(self):

        t = self.start_date
        i = 0
        while t <= self.end_date:
            i += 1

            self.weeks.append(t)

            if self.repeating:
                t += relativedelta(days=self.repeating)

            else:
                break
        # end while
    # end get_weeks


    def update_upcoming_events(self):
        """
        """

        db = Database.connect_database()

        db.cursor.execute(f"""
            DELETE FROM UpcomingEvents
            WHERE id = '{self.id}'
        ;""")

        # TODO work out never ending events...

        for week in self.weeks:
            db.cursor.execute(f"""
                INSERT INTO UpcomingEvents (
                    `id`, `date`
                ) VALUES (
                    '{self.id}', '{week.strftime(time_format1)}'
                )
            ;""")
            
            if self.repeating:
                self.start_date += relativedelta(days=self.repeating)

            else:
                break
        # end while


        db.connection.commit()
        db.connection.close()
    # end update_upcoming_events


    async def send(self, client):
        """
        """

        self.embed = self.to_embed()

        for guild in Guilds.get_followers(client, guild=self.guild, guild_id=self.guild.id):
            jc_guild = Guilds.get_jc_guild(guild.id)
            jc_guild.guild = client.get_guild(jc_guild.id)
            if jc_guild.guild:
                jc_guild.follow_channel = jc_guild.guild.get_channel(jc_guild.follow_channel_id)

            if not self.edited and jc_guild.follow_channel: # send new messages
                e = await simple_bot_response(jc_guild.follow_channel, send=False)
                self.embed.color = e.color

                self.messages.append(await jc_guild.follow_channel.send(embed=self.embed))
                await self.messages[-1].add_reaction(Support.emojis.calendar_emoji)

        # TODO HANDLE EDITED EVENTS

        if not self.edited and self.messages: # save messages
            db = Database.connect_database()
            for m in self.messages:
                db.cursor.execute(f"""
                    INSERT INTO EventMessages (
                        `id`, `channel_id`, `message_id`
                    ) VALUES (
                        '{self.id}', '{m.channel.id}', '{m.id}'
                    )
                ;""")
            db.connection.commit()
            db.connection.close()

    # end send


    def edit_event(self, insert=True):
        """
        """

        db = Database.connect_database()

        if insert:
            db.cursor.execute(f"""
                INSERT INTO Events (
                    `guild_id`, `creator_id`, `editor_id`, `type`, `platform`, `name`, `details`, `time_zone`, `start_date`, `end_date`, `duration`, `repeating`, `invite_link`

                ) VALUES (

                    '{self.guild_id}',
                    '{self.creator_id}',
                    '{self.editor_id}',
                    '{self.type}',
                    '{self.platform}',
                    '{replace_chars(self.name)}',
                    '{replace_chars(self.details)}',
                    '{self.time_zone}',
                    '{self.start_date.strftime(time_format1)}',
                    '{self.end_date.strftime(time_format1)}',
                    '{self.duration}',
                    '{self.repeating}',
                    '{replace_chars(self.invite_link)}'
                )
            ;""")

        else:
            pass

        db.connection.commit()

        db.cursor.execute(f"""
            SELECT MAX(id) FROM Events
        ;""")

        db.connection.close()

        return int(db.cursor.fetchall()[0][0])
    # end edit_event


    def to_embed(self):
        embed = discord.Embed()
        embed.set_footer(text=f"Event ID: {self.id}")

        embed.title = f"**{self.name} ({self.platform})**"
        embed.description = self.details


        value = f"**Start Date:** {self.start_date.strftime('%a %b %m, %Y - %I:%M%p %Z')} [(convert)]({self.start_date.strftime(f'https://time.is/%I%M%p_%d_%b_%Y_{self.start_date.tzname()}')})\n" # start date


        value += "**End Date:** " # end date
        if self.end_date == datetime.utcfromtimestamp(0): # never ending
            value += "Never\n"

        else:
            value += f"{self.end_date.strftime('%a %b %m, %Y - %I:%M%p %Z')} [(convert)]({self.end_date.strftime(f'https://time.is/%I%M%p_%d_%b_%Y_{self.end_date.tzname()}')})\n"
        value = value.replace("AM", "am").replace("PM", "pm").replace(" 0", " ") # AM/PM >> am/pm, 01:00 >> 1:00, 01, >> 1, 


        value += "**Duration:** "
        if self.duration: # duration

            hours = self.duration // (60 * 60) # 60 * 60 cause duration is in seconds
            minutes = (self.duration // 60) - (hours * 60) # // 60 cause ^^

            if hours:
                value += f"{hours} hour{'s' if hours > 1 else ''} "

            if minutes:
                value += f"{minutes} minutes"

            value += "\n"
                
        else:
            value += "None\n"


        if self.repeating: # repeating
            value += "**Repeating:** "

            if self.repeating == 7:
                value += "Weekly\n"

            else:
                value += f"Every {self.repeating // 7} weeks\n"
            

        value += f"**Host Server:** [{self.guild}]({self.invite_link})\n" # invite link


        embed.add_field(
            name=Support.emojis.space_char,
            value=value,
            inline=False
        )

        embed.add_field(
            name=Support.emojis.space_char,
            value=f"{Support.emojis.calendar_emoji} Upcoming Events",
            inline=False
        )

        return embed
    # end to_embed


    def to_string(self):
        return (
            f"ID: {self.id}, " +
            f"Type: {self.type}, " +
            f"Name: {self.name}, " +
            f"Details: {self.details[:100]}..., " + 
            f"Guild: {self.guild}, " + 
            f"Time Zone: {self.time_zone}, " + 
            f"Start Date: {self.start_date}, " +
            f"End Date: {self.end_date}, " +
            f"Duration: {self.duration} seconds, " +
            f"Repeating: {self.repeating} days, " +
            f"Invite Link: {self.invite_link}, " +
            ""
        )
    # end to_string
# end Event


''' FUNCTIONS '''

async def main(client, message, args):
    """
        @jc _command_
    """

    async def author_not_host():
        await simple_bot_response(message.channel,
            title="Not Whitelisted",
            description="You are not a whitelisted host. Only whitelisted hosts can create, edit, and delete events.",
            footer=f"@{get_jc_from_channel(message.channel)} whitelist @user",
            reply_message=message
        )
    # end author_not_host


    hosts = Whitelist.get_hosts(blacklisted=0)
    author_is_host = [h for h in hosts if h.id == message.author.id]


    if args[2] in Support.create_aliases + Support.edit_aliases:

        if author_is_host:

            if args[2] in Support.create_aliases and not message.guild:
                await simple_bot_response(message.channel,
                    description=f"**This command must be used in the host server.**",
                    reply_message=message
                )
                return

            await edit_event(client, message, args)

        else:
            author_not_host()
            return

# end main

def get_upcoming_events(guild_id=""):
    """
    """

    db = Database.connect_database()
    db.cursor.execute(f"""
        SELECT * FROM UpcomingEvents
    ;""")
    db.connection.close()

    upcoming_events = []
    for entry in db.cursor.fetchall():
        event = get_events(event_id=entry[0], guild_id=guild_id)

        if event:
            event = event[0]
            event.start_date = event.time_zone.localize(datetime.strptime(entry[1], time_format1))
            upcoming_events.append(event)

    return upcoming_events
# end get_upcoming_events


def get_event_from_entry(entry):
    e = Event(
        event_id=int(entry[0]),
        guild_id=int(entry[1]),
        creator_id=int(entry[2]),
        editor_id=int(entry[3]),
        event_type=entry[4],
        platform=entry[5],
        name=entry[6],
        details=entry[7],
        time_zone=timezone(entry[8]),
        start_date=datetime.strptime(entry[9], time_format1),
        end_date=datetime.strptime(entry[10], time_format1),
        duration=int(entry[11]),
        repeating=int(entry[12]),
        invite_link=entry[13],
    )

    e.start_date = e.time_zone.localize(e.start_date)
    e.end_date = e.time_zone.localize(e.end_date)

    return e
# end get_event_from_entry


def get_events(event_id="", guild_id=""):
    """
    """

    db = Database.connect_database()
    db.cursor.execute(f"""
        SELECT * FROM Events
        WHERE 
            guild_id LIKE '%{guild_id}%' AND
            id LIKE '%{event_id}%'
    ;""")
    db.connection.close()

    return [get_event_from_entry(entry) for entry in db.cursor.fetchall()]
# end get_events


async def send_calendar(client, message, user):
    """
    """
    
    jc_guild = Guilds.get_jc_guild(message.guild.id if message.guild else message.author.id)
    jc_guild.guild = message.guild if message.guild else message.author
    jc_guild.following = Guilds.get_following(client, jc_guild.guild, jc_guild.id)

    upcoming_events = []
    args = []
    for server in jc_guild.following:
        following = server.id
        if message.author.id != client.user.id:
            args, c = Support.get_args_from_content(message.content)
            following = '' if args[-2] == "all" else following


        ue = get_upcoming_events(following)
        if following:
            upcoming_events += ue
        else:
            upcoming_events = ue
        

    embed = discord.Embed(color=Support.colors.jc_grey)
    embed.title = "Upcoming Races (4 weeks)"
    embed.description = f"`@{client.user} calendar all` to view all upcoming races.\n\n" if args and args[-2] != "all" else ''
    embed.description += "The times link to online converters.\n"
    embed.description += "The host servers link to the server's default event invite link.\n"

    for e in upcoming_events:
        e.start_date_utc = e.start_date.astimezone(timezone("UTC"))

    upcoming_events.sort(key=lambda e:e.start_date_utc)

    calendar = ""

    prev_day = datetime.utcfromtimestamp(0)
    for e in upcoming_events:
        if (e.start_date - upcoming_events[0].start_date).days > 28: # only looping 4 weeks
            break

        if e.start_date.date() != prev_day.date():
            prev_day = e.start_date
            calendar += f"\n**{e.start_date.strftime('%A %B %d, %Y').replace(' 0', ' ')}**\n"

        calendar += f"[{e.start_date.strftime('%H:%M %Z')}]({e.start_date.strftime(f'https://time.is/%I%M%p_%d_%b_%Y_{e.start_date.tzname()}')}) - **{e.name}** (**{e.platform}**)\n"

        calendar += f"Host Server: [{client.get_guild(e.guild_id)}]({e.invite_link})\n"
        calendar += f"Type: {string.capwords(e.type)} ({'weekly' if e.repeating else f'every {e.repeating // 7} weeks' if e.repeating else 'one-off'})\n\n"


    embed.description += calendar
    await user.send(embed=embed)

    await Support.process_complete_reaction(message, remove=True)
# end send_calendar


async def edit_event(client, message, args, event=None):
    """
    """

    msg = None
    def message_check(m):
        return (
            m.channel.id == msg.channel.id and
            m.author.id == message.author.id
        )
    # end message_check

    async def cancel(embed, creator, timed_out=False):
        embed.title = discord.Embed().Empty
        embed.description = f"**Cancelled** ([back to server]({message.jump_url}))" if not timed_out else "**Timed Out**"
        embed.set_footer(text=discord.Embed().Empty)
        await creator.send(embed=embed)
    # end cancel


    creator = message.author
    embed = discord.Embed(color=Support.colors.jc_grey)


    try:
        await message.add_reaction(Support.emojis.tick_emoji)


        ''' 'CREATE' SESSION '''

        c_or_r = "" # cancel or restart
        while True: 

            if not event:
                event = Event()
                event.guild = message.guild if message.guild else message.author
                event.creator, event.editor = message.author, message.author
                event.guild_id, event.creator_id, event.editor_id = event.guild.id, event.creator.id, event.editor.id

                embed.set_footer(text="cancel | restart")

            else:
                event.editor = message.author
                event.editor_id = message.editor_id
                event.edited = True


            ''' GET EVENT TYPE '''

            if args[1] in playlist_aliases: # playlist
                event.type = event_types[0]

            elif args[1] in race_aliases: # one off
                event.type = event_types[1]

            elif args[1] in championship_aliases: # championship
                event.type = event_types[2]

            elif args[1] in time_trial_aliases: # time trial
                event.type = event_types[3]


            while not event.type:

                # cancel or restart
                if c_or_r:
                    await cancel(embed, creator) if c_or_r == "cancel" else ""
                    break


                # prepare
                embed.title = "**Which type of event is this?**"
                embed.description = "Enter the number that matches the event's type.\n\n"

                for i, event_type in enumerate(event_types):
                    embed.description += f"**{i+1}** {string.capwords(event_type)}\n"
            
                # send
                msg = await creator.send(embed=embed)


                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=120)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""


                # set
                if not c_or_r and mesge.content.isnumeric():
                    num = int(mesge.content)
                    if num and num <= len(event_types):
                        event.type = event_types[num-1]

            # end while ## GET EVENT TYPE ##

            # cancel or restart
            if c_or_r == "cancel":
                break
            elif c_or_r == "restart":
                continue


            ''' GET EVENT PLATFORM '''

            while not event.platform:

                # cancel or restart
                if c_or_r:
                    await cancel(embed, creator) if c_or_r == "cancel" else ""
                    break


                # prepare
                embed.title = f"**Which platform is this {event.type} hosted on?**"
                embed.description = f"Enter the number that matches the platform for this {event.type}.\n\n"

                for i, platform in enumerate(platforms):
                    embed.description += f"**{i+1}** {platform}\n"
            
                # send
                msg = await creator.send(embed=embed)


                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=120)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""

                # set
                if not c_or_r and mesge.content.isnumeric():
                    num = int(mesge.content)
                    if num and num <= len(platforms):
                        event.platform = platforms[num-1]

            # end while ## GET EVENT PLATFORM ##

            # cancel or restart
            if c_or_r == "cancel":
                break
            elif c_or_r == "restart":
                continue


            ''' GET EVENT NAME '''

            if not event.name:

                # prepare
                embed.title = f"**What is the name of this {event.type}?**"
                embed.description = "200 characters or less"
                
                # send
                msg = await creator.send(embed=embed)

                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=120)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""

                # set
                if not c_or_r:
                    event.name = mesge.content[:200]

                # cancel or restart
                if c_or_r == "cancel":
                    await cancel(embed, creator) if c_or_r == "cancel" else ""
                    break

                elif c_or_r == "restart":
                    continue


            ''' GET EVENT DETAILS '''

            if not event.details:

                # prepare
                embed.title = f"**What are the details for *{event.name}*?**"
                embed.description = f"Provide a link to a discord message ([back to server]({message.jump_url})), a link to a spreadsheet, or simply type the details here. If there are no details, type `None`."
                
                # send
                msg = await creator.send(embed=embed)

                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=300)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""

                # set
                if not c_or_r:
                    event.details = mesge.content

                # cancel or restart
                if c_or_r == "cancel":
                    await cancel(embed, creator)
                    break

                elif c_or_r == "restart":
                    continue


            ''' GET EVENT TIMEZONE '''

            while not event.time_zone:

                # cancel or restart
                if c_or_r:
                    await cancel(embed, creator) if c_or_r == "cancel" else ""
                    break


                tzs = [] # list of time zone names

                # prepare
                embed.title = f"**Which time zone should be used for *{event.name}*?**"
                embed.description = f"Enter the number that is associated with the event's time zone. If the desired time zone is missing, contact Mo#9991.\n{Support.emojis.space_char}"

                for continent in time_zones: 

                    value = ""
                    for i in range(len(time_zones[continent])): # list of continent tzs
                        for tz_name in time_zones[continent][i]: # {name : time zone}
                            tz = time_zones[continent][i][tz_name]
                            tzs.append(tz)
                            value += f"**{len(tzs)}** {tz_name}\n"

                    value += Support.emojis.space_char
                    embed.add_field(name=continent, value=value, inline=True)


                # send
                msg = await creator.send(embed=embed)


                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=300)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""

                # set
                if not c_or_r and mesge.content.isnumeric():
                    num = int(mesge.content)
                    if num and num <= len(tzs):
                        event.time_zone = timezone(tzs[num-1])

                        embed = embed.to_dict()
                        del embed["fields"] # #NoFields
                        embed = discord.Embed().from_dict(embed)

            # end while ## GET EVENT TIMEZONE ##

            # cancel or restart
            if c_or_r == "cancel":
                break
            elif c_or_r == "restart":
                continue


            ''' GET EVENT START DATE '''

            while not event.start_date:

                # cancel or restart
                if c_or_r:
                    await cancel(embed, creator) if c_or_r == "cancel" else ""
                    break


                tzs = [] # list of time zone names

                # prepare
                embed.title = f"**When does *{event.name}* start?**"

                embed.description = "> Friday at 9pm\n"
                embed.description += "> Today/Tomorrow at 18:00\n"
                embed.description += "> Now\n"
                embed.description += "> YYYY-MM-DD 7:00 PM\n"

                # send
                msg = await creator.send(embed=embed)


                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=300)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""


                # set
                if not c_or_r:
                    a, c = Support.get_args_from_content(mesge.content)
                    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                    relative_days = ["today", "tomorrow"]

                    if a[0].lower() in days: # day at some_time
                        for format in ["%A at %I%p", "%A at %I:%M%p", "%A at %H%M", "%A at %H:%M"]:
                            try:
                                time = datetime.strptime(mesge.content, format)

                                for i in range(1, 7): # loop next week to find the matching day name
                                    d = datetime.utcnow() + relativedelta(days=i)
                                    if days.index(a[0].lower()) == d.weekday(): # found the matching weekday
                                        event.start_date = event.time_zone.localize(
                                            datetime(
                                                d.year, d.month, d.day,
                                                time.hour, time.minute, time.second
                                            )
                                        )
                                        break
                                break

                            except ValueError:
                                pass

                        
                    elif a[0].lower() in relative_days: # today/tomorrow at some_time
                        for format in ["%I%p", "%I:%M%p", "%H%M", "%H:%M"]:
                            try:
                                event.start_date = timezone("UTC").localize(datetime.utcnow()).astimezone(event.time_zone)
                                event.start_date += relativedelta(days=1 if a[0].lower() == "tomorrow" else 0)

                                if "at" == a[1]:
                                    time = datetime.strptime("".join(a[2:]), format)
                                    event.start_date = event.time_zone.localize(
                                        datetime(
                                            event.start_date.year, event.start_date.month, event.start_date.day,
                                            time.hour, time.minute, time.second
                                        )
                                    )
                                    break

                            except ValueError:
                                pass


                    elif a[0].lower() == "now": # NOW
                        event.start_date = timezone("UTC").localize(datetime.utcnow()).astimezone(event.time_zone)
                        


                    else: # try to convert content to time
                        for format in ["%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M"]:
                            try:
                                event.start_date = event.time_zone.localize(
                                    datetime.strptime(mesge.content.upper(), format) # .upper for AM/PM
                                )
                                break

                            except ValueError:
                                pass

            # end while ## GET EVENT START DATE ##

            # cancel or restart
            if c_or_r == "cancel":
                break
            elif c_or_r == "restart":
                continue


            ''' GET EVENT END DATE '''

            while not event.end_date or (event.end_date != datetime.utcfromtimestamp(0) and event.end_date < event.start_date):

                # cancel or restart
                if c_or_r:
                    await cancel(embed, creator) if c_or_r == "cancel" else ""
                    break


                tzs = [] # list of time zone names

                # prepare
                embed.title = f"**When does *{event.name}* end?**"

                embed.description = "Enter the respective number or the end date.\n\n"

                embed.description += "**1** Same day as start date\n"
                embed.description += "**2** Never\n\n"

                embed.description += "> Friday at 9pm\n"
                embed.description += "> Today/Tomorrow at 18:00\n"
                embed.description += "> Now\n"
                embed.description += "> YYYY-MM-DD 7:00 PM\n"

                # send
                msg = await creator.send(embed=embed)


                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=300)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""


                # set
                if not c_or_r:
                    a, c = Support.get_args_from_content(mesge.content)
                    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                    relative_days = ["today", "tomorrow"]

                    if mesge.content == "1": # same as start date
                        event.end_date = event.start_date # edit end time later when asking for duration
                        event.repeating = 0


                    elif mesge.content == "2": # never ending
                        event.end_date = datetime.utcfromtimestamp(0)
                        

                    elif a[0].lower() in days: # day at some_time
                        for format in ["%A at %I%p", "%A at %I:%M%p", "%A at %H%M", "%A at %H:%M"]:
                            try:
                                time = datetime.strptime(mesge.content, format)

                                for i in range(1, 8): # loop next week to find the matching day name
                                    d = datetime.utcnow() + relativedelta(days=i)
                                    if days.index(a[0].lower()) == d.weekday(): # found the matching weekday
                                        event.end_date = event.time_zone.localize(
                                            datetime(
                                                d.year, d.month, d.day,
                                                time.hour, time.minute, time.second
                                            )
                                        )
                                        break
                                break

                            except ValueError:
                                pass

                        
                    elif a[0].lower() in relative_days: # today/tomorrow at some_time
                        for format in ["%I%p", "%I:%M%p", "%H%M", "%H:%M"]:
                            try:
                                event.end_date = timezone("UTC").localize(datetime.utcnow()).astimezone(event.time_zone)
                                event.end_date += relativedelta(days=1 if a[0].lower() == "tomorrow" else 0)

                                time = datetime.strptime("".join(a[2:]), format)
                                event.end_date = event.time_zone.localize(
                                    datetime(
                                        event.end_date.year, event.end_date.month, event.end_date.day,
                                        time.hour, time.minute, time.second
                                    )
                                )
                                break

                            except ValueError:
                                pass


                    elif a[0].lower() == "now": # NOW
                        event.end_date = timezone("UTC").localize(datetime.utcnow()).astimezone(event.time_zone)
                        


                    else: # try to convert content to time
                        for format in ["%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M"]:
                            try:
                                event.end_date = event.time_zone.localize(
                                    datetime.strptime(mesge.content.upper(), format) # .upper for AM/PM
                                )
                                break

                            except ValueError:
                                pass

                    print(event.start_date, event.end_date)

            # end while ## GET EVENT END DATE ##

            # cancel or restart
            if c_or_r == "cancel":
                break
            elif c_or_r == "restart":
                continue


            ''' GET EVENT DURATION '''

            while not event.duration:

                # cancel or restart
                if c_or_r:
                    await cancel(embed, creator) if c_or_r == "cancel" else ""
                    break


                tzs = [] # list of time zone names

                # prepare
                embed.title = f"**How long is *{event.name}*?**"

                embed.description = "Type `None` for no duration.\n\n"

                embed.description += "> 2 hours\n"
                embed.description += "> 45 minutes\n"
                embed.description += "> 1 hour and 30 minutes\n"

                # send
                msg = await creator.send(embed=embed)


                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=300)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""


                # set
                if not c_or_r:
                    a, c = Support.get_args_from_content(mesge.content)
                    units = ["hour", "minute"]
                    seconds = 0

                    i = len(a) - 1
                    while i > 0:
                        for unit in units:
                            if unit in a[i].lower():
                                if a[i-1].isnumeric():
                                    seconds += (int(a[i-1]) * (60 if unit == "hour" else 1)) * 60
                        i -= 1
                    # end while

                    if seconds:
                        event.duration = seconds

                        if event.end_date == event.start_date: # only if an end date was not given and is not none, adjust
                            event.end_date += relativedelta(seconds=seconds)

                    elif mesge.content.lower() == "none":
                        event.duration = 0
                        break

            # end while ## GET EVENT DURATION ##

            # cancel or restart
            if c_or_r == "cancel":
                break
            elif c_or_r == "restart":
                continue


            ''' GET EVENT REPETITIVENESS '''

            while event.repeating is None:

                # cancel or restart
                if c_or_r:
                    await cancel(embed, creator) if c_or_r == "cancel" else ""
                    break


                tzs = [] # list of time zone names

                # prepare
                embed.title = f"**How often does *{event.name}* repeat?**"

                embed.description = ""
                for repeat in ["Weekly", "Every *n* Weeks", "Never"]: # THESE MATCH THE IFS BELOW
                    embed.description += f"> {repeat}\n"

                # send
                msg = await creator.send(embed=embed)


                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=300)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""


                # set
                if not c_or_r:
                    a, c = Support.get_args_from_content(mesge.content)
                    
                    if a[0].lower() == "weekly": # THESE IFS MATCH THE FOR LOOP ABOVE
                        event.repeating = 7

                    elif a[0].lower() == "every" and "week" in a[-2].lower(): # -2 cause -1 is ''
                        if a[1].isnumeric():
                            event.repeating = int(a[1]) * 7

                    elif a[0].lower() == "never": # never
                        event.repeating = 0

            # end while ## GET EVENT REPETITIVENESS ##

            # cancel or restart
            if c_or_r == "cancel":
                break
            elif c_or_r == "restart":
                continue


            ''' GET EVENT BREAK WEEKS '''

            event.get_weeks()

            while not event.break_weeks and event.repeating and event.end_date != datetime.utcfromtimestamp(0): # is repeating and does end

                # cancel or restart
                if c_or_r:
                    await cancel(embed, creator) if c_or_r == "cancel" else ""
                    break


                tzs = [] # list of time zone names

                # prepare
                embed.title = f"**Which weeks are the breaks weeks?**"

                embed.description = "Enter `None` if there are no break weeks.\n"
                embed.description += "List the break week numbers - ex. `4, 7`.\n\n" 

                for i, w in enumerate(event.weeks):
                    embed.description += f"**{i+1}** {w.strftime('%A %B %d, %Y')}\n"

                # send
                msg = await creator.send(embed=embed)


                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=300)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""


                # set it
                a, c = Support.get_args_from_content(mesge.content)

                if mesge.content.lower() == "none":
                    event.break_weeks = "None"

                else:
                    del_weeks = []
                    for arg in a:
                        week_num = re.findall("(\d+)", arg)
                        
                        if week_num: # valid number given
                            week_num = int(week_num[0])

                            if week_num and week_num <= len(event.weeks): # number in range
                                event.break_weeks.append(week_num)
                                del_weeks.append(event.weeks[week_num-1])

                    for dw in del_weeks:
                        del event.weeks[event.weeks.index(dw)]

            # end while ## GET EVENT BREAK WEEKS ##



            ''' GET EVENT INVITE LINK '''

            while not event.invite_link:

                # cancel or restart
                if c_or_r:
                    await cancel(embed, creator) if c_or_r == "cancel" else ""
                    break


                jc_guild = Guilds.get_jc_guild(event.guild.id)


                # prepare
                embed.title = f"**Which invite link should be used for *{event.name}*?**"

                if jc_guild and jc_guild.invite_link:
                    embed.description = f"> Default - {jc_guild.invite_link}\n"

                else:
                     embed.description = f"> ~~Default~~ - `{args[0]} link <invite_link>`\n"

                embed.description += f"> Enter Link\n"
                embed.description += f"> None\n"

                # send
                msg = await creator.send(embed=embed)


                # wait
                mesge = await client.wait_for("message", check=message_check, timeout=300)
                c_or_r = mesge.content if mesge.content in ["cancel", "restart"] else ""


                # set
                if not c_or_r:
                    a, c = Support.get_args_from_content(mesge.content)

                    if jc_guild and jc_guild.invite_link and a[0].lower() == "default":
                        event.invite_link = jc_guild.invite_link

                    elif validators.url(a[0]):
                        event.invite_link = a[0]

                    elif a[0].lower() == "none":
                        event.invite_link = "None"

            # end while ## GET EVENT INVITE LINK ##

            # cancel or restart
            if c_or_r == "cancel":
                break
            elif c_or_r == "restart":
                continue

            break # natural break, loop only 'continues' if user types restart
        # end while

        # save it
        event.id = event.edit_event()
        log("event", event.to_string())

        # send it
        embed = await simple_bot_response(msg.channel, send=False)
        event.embed = event.to_embed()
        event.embed.color = embed.color
        await creator.send(embed=event.embed)
        
        await event.send(client)
        event.update_upcoming_events()

    except asyncio.TimeoutError:
        await cancel(embed, creator, timed_out=True)


    except discord.errors.Forbidden:

        description = "Event Creating Editing and Deleting Takes place in DMs, enable the setting below, then try again.\n\n"

        description += f"**Settings >> Privacy & Safety >> `Allow direct messages from server members` >> {Support.emojis.tick_emoji}**"

        await simple_bot_response(message.channel,
            description=description,
            reply_message=message
        )
        await Support.remove_reactions(message, client.user, Support.emojis.tick_emoji)
# end edit_event