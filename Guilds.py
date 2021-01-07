''' IMPORTS '''

import mysql.connector
import validators

import Database
from Database import replace_chars
import Guilds
import Help
from Logger import log
import Support
from Support import simple_bot_response



'''' CONSTANTS '''

max_prefix_length = 30 # see Guild comment



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
    description += "\n".join([s.name for s in get_following(client, guild=jc_guild.guild, guild_id=jc_guild.id) if s])

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


async def follow_server(client, message, args, author_perms, unfollow=False):
    """
        check for local server = follow server
    """

    if message.guild and not author_perms.manage_messages:
        await Support.missing_permission('Manage Messages', message)
        return

    guild = message.guild if message.guild else message.author
    jc_guild = get_jc_guild(guild.id)


    if not jc_guild: # if not in db, create new one
        jc_guild = Guild(guild.id, prefix=f"@{Support.get_jc_from_channel(message.channel)}")


    jc_guild.name = guild.name # set some attrs
    if message.guild:
        jc_guild.guild = guild 
        
    else:
        jc_guild.guild = message.author
        jc_guild.follow_channel_id = message.author.id

    jc_guild.edit_guild()


    edited = False
    if args[2] == "all": # follow all servers
        edited = True
        jc_guild.following_ids = ["all"] if not unfollow else []

    else: # follow specific server
        jc_guild.following_ids = [s.id for s in get_following(client, jc_guild.guild, jc_guild.id) if s]

        for guild in client.guilds:

            if message.author.id != Support.ids.mo_id and guild.id in [Support.ids.mobot_support_id, Support.ids.motestbots_id]: # can't follow testing servers
                continue

            a1, c1 = Support.get_args_from_content(guild.name.lower())
            if " ".join(a1).lower() == " ".join(args[2:]).lower():
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

    test_servers = [Support.ids.mobot_support_id, Support.ids.motestbots_id]
    if edited:
        embed.title = f"**Following {'a New Server' if args[2] != 'all' else 'All Servers'}**" if not unfollow else f"Unfollowed {'a Server' if args[2] != 'all' else 'All Servers'}"

        embed.description = "**Following:**\n"
        embed.description += "\n".join([s.name for s in jc_guild.following if s.id not in test_servers])

        await message.channel.send(embed=embed)

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
    embed.description += "\n".join([s.name for s in jc_guild.following ])

    await message.channel.send(embed=embed)
# end display_following