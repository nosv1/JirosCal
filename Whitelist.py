''' IMPORTS '''

import asyncio
import discord
import re
import traceback


import Database
import Logger
from Logger import log
import Support
from Support import simple_bot_response


''' CLASS '''

class Host:
    def __init__(self, host_id=None, whitelisted_by_id=None, blacklisted=None):
        self.id = host_id
        self.whitelisted_by_id = whitelisted_by_id
        self.blacklisted = blacklisted

        self.member = None
        self.guild = None
    # end __init__
# end Host


''' FUNCTIONS '''

async def whitelist(client, message, args):
    """
    """

    msg = None
    reactions = [Support.emojis.tick_emoji, Support.emojis.x_emoji]
    def reaction_check(reaction, r_user):
        return (
            reaction.message.id == msg.id and
            str(reaction.emoji) in reactions and
            r_user.id == message.author.id
        )
    # end reaction_check


    jc = Support.get_jc_from_channel(message.channel)
    hosts = get_hosts()


    ## GET AUTHOR HOST ##

    host_author = [h for h in hosts if h.id == message.author.id]
    host_author = host_author[0] if host_author else None

    same_guild_hosts = get_same_guild_hosts(message.guild, hosts=hosts)

    if not host_author or host_author.blacklisted: # author not host or is blacklisted
    
        if host_author and host_author.blacklisted:
            description = "You cannot whitelist someone if you are blacklisted."

        else:
            description = "You cannot whitelist someone if you are not a Host yourself.\n\n"

            description += f"**Hosts in this Server:**\n"
            description += "\n".join([f"<@{h.id}>" for h in same_guild_hosts]) if same_guild_hosts else f"There are no hosts in this server. Contact Jiros#8283 or Mo#9991 to be considered getting whitelisted as a Host, or have a host from another server whitelist you."

        await simple_bot_response(message.channel,
            title="Not Whitelisted",
            description=description,
            reply_message=message
        )    
        return


    # GET MENTIONED HOST

    host_user_id = [m for m in re.findall(r"(<@!*\d{17,}>)", message.content) if Support.get_id_from_str(m) != jc.id]
    host_user_id = Support.get_id_from_str(host_user_id[0])[0] if host_user_id else None

    if not host_user_id: # user not mentioned
        await simple_bot_response(message.channel,
            description=f"**A user was not mentioned. `{args[0]} {args[1]} @user`**",
            reply_message=message
        )
        return


    description = "Whitelisting hosts enables them to create, edit, and delete events. Their actions are your responsibility. If they show signs of misuse, they, everyone they whitelisted, and yourself will be blacklisted.\n\n"

    description += f"**Are you sure you would like to whitelist <@{host_user_id}>?**"

    msg = await Support.simple_bot_response(message.channel,
        title="Whitelisting a Host",
        description=description,
        footer=f"{args[0]} report <@user> <reasoning>"
    )

    for r in reactions:
        await msg.add_reaction(r)


    try: # confirm whitelist host
        # wait
        reaction, r_user = await client.wait_for("reaction_add", check=reaction_check, timeout=120)

        if str(reaction.emoji) == reactions[1]: # x emoji
            msg.embeds[0].title += "\nCancelled"
            try:
                await msg.edit(embed=msg.embeds[0])
                await Support.remove_reactions(msg, jc, reactions)
            except discord.errors.NotFound:
                pass


        ## WHITELIST HOST ##

        elif str(reaction.emoji) == reactions[0]: # tick emoji
            host_exists = [h for h in hosts if h.id == host_user_id]


            if host_exists:
                host_host = host_exists[0]


                if host_exists[0].blacklisted: # new host is blacklisted
                    await simple_bot_response(message.channel,
                        description=f"**<@{host_host.id}> is blacklisted.**"
                    )


                else: # new host already whitelisted
                    await simple_bot_response(message.channel,
                        description=f"**<@{host_host.id}> has already been whitelisted by <@{host_host.whitelisted_by_id}>.**"
                    )


            else: # whitliest host
                whitelist_host(host_author.id, host_user_id)

                embed = await simple_bot_response(message.channel,
                    title="Host Whitelisted",
                    description=f"<@{host_user_id}> can now create, edit, and delete events.",
                    send=False
                )

                await msg.edit(embed=embed)
                await Support.remove_reactions(msg, jc, reactions)


    except asyncio.TimeoutError:
        msg.embeds[0].title += "\nTimed Out"
        try:
            await msg.edit(embed=msg.embeds[0])
            await Support.remove_reactions(msg, jc, reactions)
        except discord.errors.NotFound:
            pass
# end whitelist


def whitelist_host(whitlisted_by_id, host_id):
    db = Database.connect_database()
    db.cursor.execute(f"""
        INSERT INTO Hosts (
            id, whitelisted_by_id
        ) VALUES (
            '{host_id}', '{whitlisted_by_id}'
        )
    ;""")
    db.connection.commit()
    db.connection.close()
# end whitelist_host


def get_host_from_entry(entry):
    """
    """
    return Host(
        host_id=int(entry[0]),
        whitelisted_by_id=int(entry[1]),
        blacklisted=int(entry[2])
    )
# end get_host_from_entry


def get_hosts(blacklisted=""):
    """
    """

    db = Database.connect_database()
    db.cursor.execute(f"""
        SELECT * FROM Hosts
        WHERE
            blacklisted LIKE '%{blacklisted}%'
    ;""")
    db.connection.close()
    return [get_host_from_entry(entry) for entry in db.cursor.fetchall()]
# end get_whitelist


def get_same_guild_hosts(guild, hosts=get_hosts(blacklisted=0)):
    """
    """

    same_guild_hosts = []
    if guild:

        for host in hosts:
            for member in guild.members:
                if host.id == member.id and not host.blacklisted: # not blacklisted because get_hosts may include blacklisted
                    host.memember = member
                    host.guild = guild
                    same_guild_hosts.append(host)

    return same_guild_hosts
# end get_same_guild_hosts