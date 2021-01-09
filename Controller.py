''' IMPORTS '''

import asyncio
import copy
import discord
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone
import re
import traceback

import os
from dotenv import load_dotenv
load_dotenv()


import Events
import General
import Guilds
import Help
import Logger
from Logger import log
import Support
import Whitelist


Logger.create_log_file()


''' CONSTANTS '''

intents = discord.Intents.all()
client = discord.Client(intents = intents)

connected = None
host = os.getenv("HOST")

guild_prefixes = Guilds.get_guild_prefixes()
log("startup", f"Guild Prefixes: {len(guild_prefixes)}")

# restart stuff
restart = 0 # the host runs this Controller.py in a loop, when Controller disconnects, it returns 1 or 0 depending if ..jc restart is called, 1 being restart, 0 being exit loop
restart_time = datetime.utcnow() # used to not allow commands {restart_interval} seconds before restart happens
restart_interval = 60 # time between restart/shutdown command and action



''' FUNCTIONS '''

@client.event
async def on_raw_message_edit(payload):
    if not connected: # we aint ready yet
        return

    error = False
    message = None
    try:

        pd = payload.data

        channel_id = int(pd["channel_id"])
        message_id = int(pd["id"])

        channel = client.get_channel(channel_id)
        channel = channel if channel else await client.fetch_channel(channel_id) # if DM, get_channel is none, i think

        message = await channel.fetch_message(message_id)

        if not message.author.bot:
            try:
                pd["content"]
                await on_message(message)
            except KeyError: # when content was not updated
                pass

    except discord.errors.NotFound:
        await Logger.log_error("message edit erorr", traceback.format_exc())
    
    except:
        error = traceback.format_exc()

    if error:
        await Logger.log_error(client, error)
# end on_raw_message_edit


@client.event
async def on_message(message):
    global restart 
    global restart_time
    global guild_prefixes

    if not connected: # we aint ready yet
        return

    error = False
    try:
        # prep message content for use
        args, mc = Support.get_args_from_content(message.content)

        ## BEGIN CHECKS ##

        if not message.author.bot: # not a bot and webhook we care about
                

            try:
                guild_prefix = guild_prefixes[message.guild.id if message.guild else message.author.id]
            except KeyError:
                guild_prefix = None

            if (
                (
                    host == "PI4" and # is PI4
                    (
                        re.findall(rf"(<@!*{Support.ids.jc_id}>)", args[0]) or # @JirosCal command
                        guild_prefix and mc[:len(str(guild_prefix))+1] == guild_prefix + " " # start of content = guild prefix
                    )
                ) or (
                    host == "PC" and # is PC
                        (args[0] in ["11j", "``j"]) # 11j command
                )
            ):
                log("COMMAND", f"{message.author.id}, '{message.content}'\n")

                jc = Support.get_jc_from_channel(message.channel)
                is_mo = message.author.id == Support.ids.mo_id

                author_perms = Support.get_member_perms(message.channel, message.author)


                ## COMMAND CHECKS ##


                ## CHECK FOR UPCOMING RESTART ##

                restart_delta = (restart_time - datetime.utcnow()).seconds
                if restart_delta < restart_interval and not is_mo:
                    description = f"**{jc.mention} is about to {'restart' if restart else 'shut down'}. "
                    if restart:
                        description += f"Try again in {restart_delta + restart_interval} seconds, or watch for its status to change.**" 
                    else:
                        description += "Try again when it comes back online.**"

                    await Support.simple_bot_response(message.channel, description=description, reply_message=message)
                    return


                ## MO ##

                if is_mo:
                    if args[1] == "test":
                        
                        e = Events.get_events(event_id=3)[0]
                        e.guild = await client.fetch_guild(e.guild_id)
                        await e.get_messages(client, urls=False)

                        embed = e.to_embed()
                        for m in e.messages:
                            print(m)
                            await m.edit(embed=embed)


                        return
                        
                    elif args[1] == "setavatar":
                        with open('Images/logo.png', 'rb') as f:
                            await client.user.edit(avatar=f.read())
                        return

                    elif args[1] == "name":
                        await client.user.edit(username="JirosCal")
                        print('edited')
                        return

                    elif args[1] == "guild":
                        guild = client.get_guild(int(args[2]))

                        description = f"**Members:** {len(guild.members)}\n"
                        description += f"**Joined:** {datetime.strftime(jc.joined_at, Support.short_date_1)}\n\n"

                        description += f"[**Go to**](https://discord.com/channels/{guild.id})\n"

                        await Support.simple_bot_response(message.channel,
                            title=guild.name,
                            description=description,
                            thumbnail_url=guild.icon_url
                        )
                        return

                    elif args[1] in ["close", "shutdown", "stop", "restart"]:
                        restart, msg  = await Support.restart(client, message, restart_interval, restart=args[1] == "restart")

                        restart_time = datetime.utcnow() + relativedelta(seconds=restart_interval) # set new restart time
                        await asyncio.sleep(restart_interval)

                        if msg:
                            msg.embeds[0].description = "**Restarting**" if restart else "**Shutting Down**"
                            try:
                                await msg.channel.delete_messages([msg, message])
                            except:
                                pass
                            
                        await client.close()
                    
                        
                
                ## HELP + GENERAL ##

                # if args[1] in ["?", "search"]:
                    # await Help.search(message, args)

                if args[1] in Help.help_aliases[:3] + ["commands", "cmds"]:
                    e = await Support.simple_bot_response(message.channel, send=False)
                    h_embed = Support.load_embed_from_Embeds("Embeds/command_list.json")
                    h_embed.color = e.color
                    await message.channel.send(embed=h_embed)
                    # await Help.send_help_embed(client, message, Help.help_links.general)

                # elif args[1] in ["commands", "cmds"]:
                    # await Help.send_help_embed(client, message, Help.help_links.command_list_1)

                elif args[1] in ["whitelist", "wl"]:
                    await Whitelist.whitelist(client, message, args)

                
                ## EVENTS ##

                elif args[1] in Support.create_aliases + Support.edit_aliases + Support.delete_aliases:
                    await Events.main(client, message, args)

                elif args[1] in Events.calendar_aliases:
                    await Events.send_calendar(client, message, message.author)


                
                ## GUILDS ##

                elif args[1] == "prefix":
                    jc_guild, guild_prefixes = await Guilds.set_prefix(message, args, author_perms)

                elif args[1] == "link": 
                    await Guilds.set_invite_link(message, args, author_perms)

                elif args[1] == "here":
                    await Guilds.set_follow_channel(client, message, args, author_perms)

                elif args[1] in ["follow", "unfollow"]:
                    await Guilds.follow_server(client, message, args, author_perms, unfollow=args[1] == "unfollow")

                elif args[1] == "following":
                    await Guilds.display_following(client, message, args)




                else:
                    # await Help.send_help_embed(client, message, Help.help_links.simple)
                    description = f"`@{jc} help`\n"
                    description += f"`@{jc} calendar`\n"
                    await Support.simple_bot_response(message.channel,
                        title="Command Not Recognized",
                        description=description,
                        reply_message=message
                    )

                    if args[1]: # >= 1 arg given, gimme that insight
                        await Logger.log_error(client, f"command not recognized {message.content}")

                ''' END COMMAND CHECKS '''

            
            

    except RuntimeError:
        log("Connection", f"{host} Disconnected")
    
    except:
        error = traceback.format_exc()

    if error:
        await Logger.log_error(client, error)
# end on_message


@client.event
async def on_raw_reaction_add(payload):
    global restart 
    global restart_time

    if not connected: # we aint ready yet
        return

    user_id = payload.user_id
    channel_id = payload.channel_id
    channel = client.get_channel(channel_id)
    message_id = payload.message_id

    message = None
    user = None
    is_dm = None
    error = False
    try:

        message = await channel.fetch_message(message_id)
        if not message:
            return

        is_dm = message.channel.type == discord.ChannelType.private

        user = [user for user in (message.channel.members if not is_dm else [message.channel.recipient]) if user.id == user_id]
        user = user[0] if user else user

        jc = Support.get_jc_from_channel(message.channel)

        remove_reaction = False
        if user: # message and user are found

            if not user.bot: # not bot reaction

                restart_delta = (restart_time - datetime.utcnow()).seconds
                if restart_delta < restart_interval:
                    return

                
                ## PLAIN REACTION CHECKS ##

                if message.author.id == client.user.id: # is jiroscal messages
                    
                    if payload.emoji.name == Support.emojis.calendar_emoji: # calendar emoji
                        await Events.send_calendar(client, message, user)
                        remove_reaction = True


                ## EMBED CHECKS ##

                embed = message.embeds[0] if message.embeds else []

                if embed: # has embed
                    pass

                    if embed.title: # has title 
                        pass


    

        if remove_reaction and not is_dm:
            await message.remove_reaction(payload.emoji, user)

    except AttributeError: # possibly NoneType.fetch_message, happens in DMs after bot is restarted
        error = traceback.format_exc()

    #except discord.errors.NotFound: # bot aint finding messages...
     #   Logger.log_error(traceback.format_exc())
      #  return

    except discord.errors.Forbidden:
        error = traceback.format_exc()
    
    except:
        error = traceback.format_exc()

    if error:
        await Logger.log_error(client, error)
# end on_reaction_add


@client.event
async def on_raw_reaction_remove(payload):
    global restart 
    global restart_time

    if not connected: # we aint ready yet
        return

    user_id = payload.user_id
    channel_id = payload.channel_id
    channel = client.get_channel(channel_id)
    message_id = payload.message_id

    message = None
    user = None
    is_dm = None
    error = False
    try:

        message = await channel.fetch_message(message_id)
        if not message:
            return

        is_dm = message.channel.type == discord.ChannelType.private

        user = [user for user in (message.channel.members if not is_dm else [message.channel.recipient]) if user.id == user_id]
        user = user[0] if user else user


        if message and user:

            if not user.bot: # not bot reaction

                restart_delta = (restart_time - datetime.utcnow()).seconds
                if restart_delta < restart_interval:
                    return


    except AttributeError: # possibly NoneType.fetch_message, happens in DMs after bot is restarted
        error = traceback.format_exc()

    #except discord.errors.NotFound: # bot aint finding messages...
     #   Logger.log_error(traceback.format_exc())
      #  return

    except discord.errors.Forbidden:
        error = traceback.format_exc()
    
    except:
        error = traceback.format_exc()

    if error:
        await Logger.log_error(client, error)
# end on_reaction_remove


''' STARTUP '''

''' this appears to simply not be needed
@client.event 
async def on_ready():
    error = None
    try:
    
    except:
        error = traceback.format_exc()

    if error:
        await Logger.log_error(client, error)
# end on_ready
'''

async def startup():
    global connected
    global restart
    await client.wait_until_ready()

    connected = True
    restart = 1
    log("Connection", f"{host} Controller Connected")

    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing, name="Better get that on the calendar."
        ),
        status=discord.Status.online
    )
# end startup

log("Connection", f"{host} Controller Connecting")

client.loop.create_task(startup())

client.run(os.getenv("TOKEN"))
print(restart)