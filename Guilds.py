''' IMPORTS '''

import asyncio
from datetime import datetime
from dateutil.relativedelta import relativedelta
import discord
import mysql.connector
from pytz import timezone
import validators

import Database
from Database import replace_chars
import Events
import Guilds
import Help
from Logger import log
import Support
from Support import simple_bot_response



'''' CONSTANTS '''

max_prefix_length = 30 # see Guild comment

test_servers = [Support.ids.mobot_support_id, Support.ids.motestbots_id]


''' CLASS '''

class Guild:
    """
        Guild in Guilds Table
        id - varchar(20), primary key
        name - varchar(100)
        prefix - varchar(30) # length same as CustomCommand.prefix
        invite_link - varchar(500)
        follow_channel_id - varcahr(20)


        accounts for dm channels
    """


    def __init__(self, guild_id, name=None, prefix="@JirosCal#7363", invite_link=None, follow_channel_id=None, following_ids=[]):
        self.id = int(guild_id)
        self.name = name
        self.prefix = prefix
        self.invite_link = invite_link
        self.follow_channel_id = follow_channel_id
        self.following_ids = set(following_ids + [self.id]) # this could be ['all']

        self.follow_channel = None
        self.guild = None
        self.following = []
    # end __init__

    def get_following(self):
        db = Database.connect_database()
        db.cursor.execute(f"""
            SELECT following_id FROM 
        ;""")
        db.connection.close()
    # end get_following


    def edit_guild(self):
        db = Database.connect_database()

        self.name = replace_chars(self.name)
        self.prefix = replace_chars(self.prefix)

        try:
            db.cursor.execute(f"""
                INSERT INTO Guilds (
                    `id`, `name`, `prefix`, `invite_link`, `follow_channel_id`
                ) VALUES (
                    '{self.id}', '{self.name}', '{self.prefix}', 
                    {Support.quote(self.invite_link) if self.invite_link else 'NULL'},
                    {Support.quote(self.follow_channel_id) if self.follow_channel_id else 'NULL'}
                )
            ;""")

        except mysql.connector.errors.IntegrityError:
            db.cursor.execute(f"""
                UPDATE Guilds SET 
                    `name` = '{self.name}', 
                    `prefix` = '{self.prefix}',
                    `invite_link` = {Support.quote(self.invite_link) if self.invite_link else 'NULL'},
                    `follow_channel_id` = {Support.quote(self.follow_channel_id) if self.follow_channel_id else 'NULL'}
                WHERE 
                    id = '{self.id}'
            ;""")

        db.connection.commit()
        db.connection.close()
    # end edit_guild


    def update_following_ids(self):
        """
        """

        db = Database.connect_database()

        db.cursor.execute(f"""
            DELETE FROM Following 
            WHERE follower_id = '{self.id}'
        ;""")


        for f_id in set(self.following_ids):
            db.cursor.execute(f"""
                INSERT INTO Following (
                    `following_id`, `follower_id`
                ) VALUES (
                    '{f_id}',
                    '{self.id}'
                )
            ;""")

        db.connection.commit()
        db.connection.close()
    # end update_following_ids


    async def display_prefix(self, channel, new_prefix=False):
        description=f"**{self.name}'s {'New ' if new_prefix else ''}Prefix:** `{self.prefix}`\n\n"

        description += f"`{self.prefix} prefix <new_prefix>`" if not new_prefix else ''

        await simple_bot_response(channel, 
            description=description
        )
        log("prefix", f"{'New Prefix: ' if new_prefix else ''}{vars(self)}")
    # end display_prefix
# end Guild

class Reminder:
    def __init__(self, event_id=None, user_id=None, offset=0, date=None):
        self.event_id = event_id
        self.user_id = user_id
        self.offset = offset # as minutes 
        self.date = date # as datetime in correct time zone

        self.text = "" # 1 week or 2 days ... etc
        self.event = None
    # end __init__


    async def send(self, client):
        """
        """

        embed = discord.Embed(color=Support.colors.jc_grey)
        embed.title = "**Event Reminder**"

        embed.description = f"*[{self.event.name}]({self.event.invite_link})* starts in {self.text}."

        user = await client.fetch_user(self.user_id)
        await user.send(embed=embed)
    # end send


    def edit_reminders(self, reminders):
        """
            reminders is a list of Reminders
        """

        db = Database.connect_database()
        db.cursor.execute(f"""
            DELETE FROM Reminders 
            WHERE 
                event_id = '{self.event_id}' AND
                discord_id = '{self.user_id}'
        """)

        for r in reminders:
            db.cursor.execute(f"""
                INSERT INTO Reminders (
                    `event_id`, `discord_id`, `offset`
                ) VALUES (
                    '{r.event_id}',
                    '{r.user_id}',
                    '{r.offset}'
                )
            """)
        db.connection.commit()
        db.connection.close()
    # end edit_reminders


    def to_string(self):
        return (
            f"Event ID: {self.event_id}, " +
            f"User ID: {self.user_id}, " +
            f"Offset: {self.offset}, " +
            f"Date: {self.date}"
        )
    # end to_string
# end Reminder



''' FUNCTIONS '''

def get_jc_guild(guild_id):
    db = Database.connect_database()
    db.cursor.execute(f"""
        SELECT * FROM Guilds WHERE id = '{guild_id}'
    ;""")
    jc_guild = db.cursor.fetchall()
    db.connection.close()

    if jc_guild:
        jc_guild = Guild(
            guild_id = int(jc_guild[0][0]),
            name = jc_guild[0][1],
            prefix = jc_guild[0][2],
            invite_link = jc_guild[0][3],
            follow_channel_id = int(jc_guild[0][4]) if jc_guild[0][4] else None
        )

    return jc_guild
# end get_jc_guild



## PREFIXES ##

def get_guild_prefix(guild_id):
    jc_guild = get_jc_guild(guild_id)
    return jc_guild.prefix if jc_guild else "@JirosCal#7363"
# end get_guild_prefix


def get_guild_prefixes():
    """
        Returns {int(id) : str(prefix), ...}
    """
    db = Database.connect_database()
    db.cursor.execute(f"""
        SELECT id, prefix FROM Guilds
    ;""")
    guilds = db.cursor.fetchall()
    db.connection.close()

    guild_prefixes = {}
    for g in guilds:
        guild_prefixes[int(g[0])] = g[1]

    return guild_prefixes
# end get_guild_prefixes


async def set_prefix(message, args, author_perms):
    """
        ..j prefix - view current prefix
        ..j prefix [new_prefix] - set prefix
    """

    jc = Support.get_jc_from_channel(message.channel)


    prefix = message.content[message.content.index(args[1])+len(args[1]):].strip()


    guild = message.guild if message.guild else message.author
    jc_guild = get_jc_guild(guild.id)       


    if not jc_guild: # if not in db, create new one
        jc_guild = Guild(guild.id, prefix=f"@{Support.get_jc_from_channel(message.channel)}")


    jc_guild.name = guild.name # set some attrs
    jc_guild.guild = guild if message.guild else message.author

    jc_guild.edit_guild()


    if prefix: # prefix included

        if message.guild and not author_perms.administrator: # missing permissions
            await Support.missing_permission("Administrator", message)
            return


        if len(prefix) <= max_prefix_length: # good to go

            if prefix not in Help.help_aliases: # good to go

                jc_guild.prefix = prefix
                await jc_guild.display_prefix(message.channel, new_prefix=True)

            else: # conflicting prefix

                description = f"Your server's {jc.mention} prefix cannot be an alias for {jc.mention}'s help messages - `{'`, `'.join(Help.help_aliases)}`."

                await simple_bot_response(message.channel,
                    title="Invalid Prefix",
                    description=description,
                    reply_message=message
                )
                log("guild prefix", "invalid prefix")


        else: # too long

            description = f"A {jc.mention} prefix cannot be longer than {max_prefix_length} characters.\n"
            description += f"`{prefix}` has {len(prefix)} characters.\n\n"

            description += f"`@{jc} prefix <new_prefix>`"

            await simple_bot_response(message.channel,
                title="Prefix Too Long",
                description=description,
                reply_message=message
            )
            log('guild prefix', 'too long')

    else:
        await jc_guild.display_prefix(message.channel)
        
    jc_guild.edit_guild()
    return jc_guild, get_guild_prefixes()
# end set_prefix



## INVITE LINKS ##

def get_guild_invite_link(guild_id):
    pass
# end get_guild_invite_link


def get_guild_invite_links():
    pass
# end get_guild_invite_links


async def set_invite_link(message, args, author_perms):
    """
    """

    jc = Support.get_jc_from_channel(message.channel)


    guild = message.guild if message.guild else message.author
    jc_guild = get_jc_guild(guild.id)


    if not jc_guild: # if not in db, create new one
        jc_guild = Guild(guild.id, prefix=f"@{Support.get_jc_from_channel(message.channel)}")


    jc_guild.name = guild.name # set some attrs
    jc_guild.guild = guild if message.guild else None

    jc_guild.edit_guild()


    if validators.url(args[2]): # link provided

        if message.guild and not author_perms.create_instant_invite: # missing permission
            await Support.missing_permission("Create Invite", message)
            return

        jc_guild.invite_link = args[2]

        await simple_bot_response(message.channel,
            description=f"**{jc_guild.name}'s Default Event Invite Link:** {jc_guild.invite_link}"
        )


    elif args[2]: # invalid link
        await simple_bot_response(message.channel,
            title="Invalid Link",
            description=f"`@{jc} {args[1]} <invite_link>`",
            reply_message=message
        )


    else: # no link provided
        description = f"**{jc_guild.name}'s Default Event Invite Link:** {jc_guild.invite_link if jc_guild.invite_link else '`None Provided`'}\n\n"

        description += f"`@{jc} {args[1]} <invite_link>`"

        await simple_bot_response(message.channel,
            description=description,
            reply_message=message
        )

    jc_guild.edit_guild()
# end set_invite_link



## FOLLOWING EVENTS ##

async def set_follow_channel(client, message, args, author_perms):
    """
    """

    if message.guild and not author_perms.administrator:
        await Support.missing_permission('Administrator', message)
        return

    guild = message.guild if message.guild else message.author
    jc_guild = get_jc_guild(guild.id)


    if not jc_guild: # if not in db, create new one
        jc_guild = Guild(guild.id, prefix=f"@{Support.get_jc_from_channel(message.channel)}")


    jc_guild.name = guild.name # set some attrs
    jc_guild.guild = guild if message.guild else None

    jc_guild.follow_channel = message.channel # set the channel
    jc_guild.follow_channel_id = jc_guild.follow_channel.id

    jc_guild.edit_guild()


    description = "Events from followed servers will now appear in this channel.\n\n"

    description += "**Following:**\n"
    description += "\n".join([s.name for s in get_following(client, guild=jc_guild.guild, guild_id=jc_guild.id) if s and s.id not in test_servers])

    await simple_bot_response(message.channel,
        title="Event Channel Specified",
        description=description
    )
# end set_follow_channel


def get_following(client, guild=None, guild_id=""):
    """
        returns [Guild, ...]
    """

    db = Database.connect_database()
    db.cursor.execute(f"""
        SELECT following_id from Following 
        WHERE follower_id LIKE '%{guild_id}%'
    ;""")
    db.connection.close()

    following = [guild] if guild else []
    for f_id in db.cursor.fetchall():
        if f_id[0] == "all":
            following = client.guilds

        else:
            g = client.get_guild(int(f_id[0]))
            following += [g] if g else []

    return list(set(following))
# end get_following


def get_followers(client, guild_id=""):
    """
        returns [Guild, ...]
    """

    db = Database.connect_database()
    db.cursor.execute(f"""
        SELECT follower_id from Following 
        WHERE 
            following_id LIKE '%{guild_id}%' OR
            following_id = 'all'
    ;""")
    db.connection.close()

    followers = [guild_id] # important this goes first in the list
    for f_id in db.cursor.fetchall():
        if f_id[0] == "all":
            followers = [g.id for g in client.guilds]

        elif int(f_id[0]) not in followers:
            followers += [int(f_id[0])]

    return followers
# end get_following


async def follow_server(client, message, args, user, unfollow=False):
    """
        check for local server = follow server
    """

    jc = Support.get_jc_from_channel(message.channel)

    event = None
    if not args:
        event = Events.get_events(event_id=message.embeds[0].footer.text.split(":")[1].strip())[0]


    if args and message.guild and not Support.get_member_perms(message.channel, user).manage_messages:
        await Support.missing_permission('Manage Messages', message)
        return

    guild = message.guild if message.guild and args else user
    jc_guild = get_jc_guild(guild.id)


    if not jc_guild: # if not in db, create new one
        jc_guild = Guild(guild.id, prefix=f"@{Support.get_jc_from_channel(message.channel)}")


    jc_guild.name = guild.name # set some attrs
    if message.guild:
        jc_guild.guild = guild 
        
    else:
        jc_guild.guild = user
        jc_guild.follow_channel_id = user.id

    jc_guild.edit_guild()


    edited = False
    if args and args[2] == "all": # follow all servers
        edited = True
        jc_guild.following_ids = ["all"] if not unfollow else []


    else: # follow specific server
        jc_guild.following_ids = [s.id for s in get_following(client, jc_guild.guild, jc_guild.id) if s]

        for guild in client.guilds:

            if user.id != Support.ids.mo_id and guild.id in [Support.ids.mobot_support_id, Support.ids.motestbots_id]: # can't follow testing servers
                continue

            a1, c1 = Support.get_args_from_content(guild.name.lower())
            if (
                " ".join(a1).lower() == " ".join(args[2:]).lower() or 
                (event and guild.id == event.guild_id)
            ):
                edited = True

                if not unfollow:
                    jc_guild.following_ids.append(guild.id)

                else:
                    try:
                        del jc_guild.following_ids[jc_guild.following_ids.index(guild.id)]

                    except ValueError:
                        edited = False


    jc_guild.update_following_ids()
    jc_guild.following = get_following(client, jc_guild.guild, jc_guild.id)


    embed = await simple_bot_response(message.channel, send=False)

    if edited:
        embed.title = f"**Following {'a New Server' if (args and args[2] != 'all') or not args else 'All Servers'}**" if not unfollow else f"Unfollowed {'a Server' if (args and args[2] != 'all') or not args else 'All Servers'}"

        embed.description = "**Following:**\n"
        embed.description += "\n".join([s.name for s in jc_guild.following if s.id not in test_servers])

        if not args:
            embed.set_footer(text=f"@{jc} unfollow <all/server_name>")


        if not event:
            await message.channel.send(embed=embed)

        else:
            try:
                await user.send(embed=embed)
            except discord.errors.Forbidden:
                await Support.process_complete_reaction(message, remove=True, rejected=True)

    elif not unfollow:
        
        embed.description = f"**{client.user.mention} is not in `{args[2]}`.**\n\n" if args[2] else ""

        embed.description += f"**Available Servers:**\n"
        for g in client.guilds:
            if g.id in test_servers: # don't show these servers
                continue

            embed.description += f"{g.name}{' (following)' if g in jc_guild.following else ''}\n"

        await message.reply(embed=embed)

    elif unfollow:

        embed.description = f"**{jc_guild.guild} was not following `{args[2]}`.**\n"

        embed.description += "**Following:**\n"
        embed.description += "\n".join([s.name for s in jc_guild.following if s.id not in test_servers])

        await message.reply(embed=embed)
# end follow_server


async def display_following(client, message, args):
    """
    """

    guild = message.guild if message.guild else message.author
    jc_guild = get_jc_guild(guild.id)


    if not jc_guild: # if not in db, create new one
        jc_guild = Guild(guild.id, prefix=f"@{Support.get_jc_from_channel(message.channel)}")


    jc_guild.name = guild.name # set some attrs
    jc_guild.guild = guild if message.guild else message.author

    jc_guild.edit_guild()
    
    embed = await simple_bot_response(message.channel, send=False)

    jc_guild.following = get_following(client, jc_guild.guild, jc_guild.id)

    embed.description = "**Following:**\n"
    embed.description += "\n".join([s.name for s in jc_guild.following if s.id not in test_servers])

    await message.channel.send(embed=embed)
# end display_following



## REMINDERS ##


async def get_reminders(client, event_id="", user_id=""):
    """
    """

    db = Database.connect_database()
    db.cursor.execute(f"""
        SELECT * FROM Reminders
        WHERE
            event_id LIKE '%{event_id}%' AND
            discord_id LIKE '%{user_id}%'
    """)
    db.connection.close()
    
    reminders = []
    for r in db.cursor.fetchall():

        ue = await Events.get_upcoming_events(client, event_id=r[0])

        for u in ue:
            now = timezone("UTC").localize(datetime.utcnow()).astimezone(u.time_zone)
            if u.start_date > now:
                ue = u
                break

        if type(ue) == Events.Event:

            reminders.append(
                Reminder(
                    event_id=r[0], # event_id
                    user_id=int(r[1]), # user id
                    offset=int(r[2]), # offset minutes
                    date=ue.start_date - relativedelta(minutes=int(r[2])) # reminder date
                )
            )

            reminders[-1].event = ue


            weeks =  reminders[-1].offset // (60 * 24 * 7)
            days = (reminders[-1].offset - weeks * 60 * 24 * 7) // (60 * 24)
            hours = (reminders[-1].offset - (weeks * 60 * 24 * 7) - days * 60 * 24) // 60
            minutes = (reminders[-1].offset - (weeks * 60 * 24 * 7) - (days * 60 * 24) - (hours * 60))

            text = []
            text += [f"{weeks} week{'s' if weeks > 1 else ''}"] if weeks else []
            text += [f"{days} day{'s' if days > 1 else ''}"] if days else []
            text += [f"{hours} hour{'s' if hours > 1 else ''}"] if hours else []
            text += [f"{minutes} minute{'s' if minutes > 1 else ''}"] if minutes else []

            reminders[-1].text = " and ".join(text)


    return reminders
# end get_reminders


async def set_reminders(client, message, user):
    """
        assuming coming from bell on event message
    """

    msg = None
    def message_check(m):
        return (
            m.channel.id == msg.channel.id and
            m.author.id == user.id
        )
    # end message_check

    async def cancel(embed, editor, timed_out=False):
        embed.title = discord.Embed().Empty
        embed.description = f"**Cancelled** ([back to server]({message.jump_url}))" if not timed_out else "**Timed Out**"
        embed.set_footer(text=discord.Embed().Empty)
        await editor.send(embed=embed)
    # end cancel


    embed = discord.Embed(color=Support.colors.jc_grey)


    event = Events.get_events(event_id=message.embeds[0].footer.text.split(":")[1].strip())[0]
    upcoming_event = await Events.get_upcoming_events(client, event_id=event.id)

    now = timezone("UTC").localize(datetime.utcnow()).astimezone(event.time_zone)

    for e in upcoming_event:
        if e.start_date > now:
            upcoming_event = e
            break

    if type(upcoming_event) != Events.Event:
        embed.title = "Cannot Set Reminder"
        embed.description = f"There is not an upcoming starting date for *{event.name}*."
        try:
            await user.send(embed=embed)
        except discord.errors.Forbidden:
            await Support.process_complete_reaction(message, remove=True, rejected=True)
        return
    

    reminders = await get_reminders(client, event_id=event.id, user_id=user.id)


    crd = "" # cancel or done
    try:
        while True:

            # cancel or restart or done
            if crd:
                await Events.cancel(embed, user) if crd == "cancel" else ""
                break

            # prepare
            embed.description = ""
            embed.set_footer(text="cancel | done")
            if not reminders:
                embed.title = f"**When would you like to receive reminders for *{event.name}*?**"
                embed.description = "This process loops, so only type one reminder at a time.\n"


            else:
                embed.title =f"**Would you like to set another reminder?**"
                
                embed.description += "\nEnter a number to delete the reminder.\n"

                reminders.sort(key=lambda r: r.offset)
                for i, r in enumerate(reminders):
                    embed.description += f"> **{i+1}** - {r.text}\n"


            embed.description += "\nFollow the templates, but insert your own values.\nLimits: 2 weeks before event, 3 reminders\n"

            embed.description += "> 30 minutes\n"
            embed.description += "> 1 hour and 30 minutes\n"
            embed.description += "> 1 day\n"
            embed.description += "> 1 week\n"


            # send
            msg = await user.send(embed=embed)


            # wait
            mesge = await client.wait_for("message", check=message_check, timeout=300)
            crd = mesge.content.lower() if mesge.content.lower() in ["cancel", "done"] else ""

            if not crd:
                a, c = Support.get_args_from_content(mesge.content)
                units = ["minute", "hour", "day", "week"]
                minutes = 0

                i = len(a) - 1
                while i > 0:
                    for unit in units:
                        if unit in a[i].lower():
                            if a[i-1].isnumeric():

                                value = int(a[i-1])
                                multiplier = 1
                                if unit == "week":
                                    multiplier = 60 * 24 * 7

                                if unit == "day":
                                    multiplier = 60 * 24

                                elif unit == "hour":
                                    multiplier = 60

                                minutes += value * multiplier
                    i -= 1
                # end while

                if minutes and minutes <= 60 * 24 * 14:
                    reminders.append(
                        Reminder(
                            event_id=event.id, 
                            user_id=user.id, 
                            offset=minutes
                        )
                    )
                    reminders[-1].text = " ".join(a)
                    reminders = reminders[-3:]

                    
                elif len(a[:-1]) == 1:
                    if a[0].isnumeric() and 1 <= int(a[0]) <= len(reminders):
                        del reminders[int(a[0])-1]


            # save it
            if crd == "done":
                Reminder(event_id=event.id, user_id=user.id).edit_reminders(reminders)

                embed.title = discord.Embed().Empty
                embed.set_footer(text=discord.Embed().Empty)
                embed.description = f"**{len(reminders)} reminder{'s' if len(reminders) != 1 else ''} set.**"
                await user.send(embed=embed)

                break
        # end while

    except asyncio.TimeoutError:
        await cancel(embed, user, timed_out=True)

    except discord.errors.Forbidden:
        await Support.process_complete_reaction(message, remove=True, rejected=True)
# end set_reminder