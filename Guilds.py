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
        invite_link - varcahr(1000)

        accounts for dm channels
    """


    def __init__(self, guild_id, name=None, prefix="@JirosCal#7363", invite_link=None, guild=None):
        self.id = int(guild_id)
        self.name = name
        self.prefix = prefix
        self.invite_link = invite_link
        self.guild = guild
    # end __init__


    def edit_guild(self):
        db = Database.connect_database()

        self.name = replace_chars(self.name)
        self.prefix = replace_chars(self.prefix)

        try:
            db.cursor.execute(f"""
                INSERT INTO Guilds (
                    `id`, `name`, `prefix`, `invite_link`
                ) VALUES (
                    '{self.id}', '{self.name}', '{self.prefix}', {Support.quote(self.invite_link) if self.invite_link else 'NULL'}
                )
            ;""")

        except mysql.connector.errors.IntegrityError:
            db.cursor.execute(f"""
                UPDATE Guilds SET 
                    `name` = '{self.name}', 
                    `prefix` = '{self.prefix}',
                    `invite_link` = {Support.quote(self.invite_link) if self.invite_link else 'NULL'}
                WHERE 
                    id = '{self.id}'
            ;""")

        db.connection.commit()
        db.connection.close()
    # end edit_guild


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
    # TODO prefix help


    prefix = message.content[message.content.index(args[1])+len(args[1]):].strip()


    guild = message.guild if message.guild else message.author
    jc_guild = get_jc_guild(guild.id)       


    if not jc_guild: # if not in db, create new one
        jc_guild = Guild(guild.id, prefix=f"@{Support.get_jc_from_channel(message.channel)}")


    jc_guild.name = guild.name # set some attrs
    jc_guild.guild = guild if message.guild else None


    if prefix: # prefix included

        if author_perms.administrator: # missing permissions
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


async def set_invite_link(client, message, args, author_perms):
    """
    """

    jc = Support.get_jc_from_channel(message.channel)
    # TODO prefix help


    guild = message.guild if message.guild else message.author
    jc_guild = get_jc_guild(guild.id)


    if not jc_guild: # if not in db, create new one
        jc_guild = Guild(guild.id, prefix=f"@{Support.get_jc_from_channel(message.channel)}")


    jc_guild.name = guild.name # set some attrs
    jc_guild.guild = guild if message.guild else None


    if validators.url(args[2]): # link provided

        if not author_perms.create_instant_invite: # missing permission
            await Support.missing_permission("Create Invite", message)
            return

        jc_guild.invite_link = args[2]

        await simple_bot_response(message.channel,
            description=f"**{jc_guild.name}'s Invite Link:** {jc_guild.invite_link}"
        )


    elif args[2]: # invalid link
        await simple_bot_response(message.channel,
            title="Invalid Link",
            description=f"`{args[0]} {args[1]} <invite_link>`",
            reply_message=message
        )


    else: # no link provided
        description = f"**{jc_guild.name}'s Invite Link:** {jc_guild.invite_link if jc_guild.invite_link else '`None Provided`'}\n\n"

        description += f"`{args[0]} {args[1]} <discord.gg/invite_link>`"

        await simple_bot_response(message.channel,
            description=description,
            reply_message=message
        )

    jc_guild.edit_guild()
# end set_invite_link

