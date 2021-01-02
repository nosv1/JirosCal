''' IMPORTS '''

import asyncio
import copy
import discord
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone
import traceback

import os
from dotenv import load_dotenv
load_dotenv()


import Copy
import CustomCommands
import Database
import Delete
import Embeds
import Events
import General
import Guilds
import Help
import Logger
from Logger import log
import Morse
import Role
from Stats import command_used
from Servers import TemplarLeagues
import Support
import Tables


Logger.create_log_file()


''' CONSTANTS '''

intents = discord.Intents.all()
client = discord.Client(intents = intents)

connected = None
host = os.getenv("HOST")

guild_prefixes = Guilds.get_guild_prefixes()
log("startup", f"Guild Prefixes: {len(guild_prefixes)}")


# event stuff
events = Events.get_events()
log("startup", f"Events: {len(events)}")

phyner_webhook_ids = Events.get_object_ids(events, "webhook")
log("startup", f"Phyner Webhook IDs: {len(phyner_webhook_ids)}")

phyner_reaction_adds = Events.get_event_events(events, "reaction_add")
log("startup", f"Phyner Reaction Add Events: {len(phyner_reaction_adds)}")

phyner_reaction_removes = Events.get_event_events(events, "reaction_remove")
log("startup", f"Phyner Reaction Remove Events: {len(phyner_reaction_removes)}")

phyner_custom_command_guild_ids = CustomCommands.get_guild_ids()
log("startup", f"Phyner Custom Command Guilds: {len(phyner_custom_command_guild_ids)}")

# restart stuff
restart = 0 # the host runs this Controller.py in a loop, when Controller disconnects, it returns 1 or 0 depending if @Phyner restart is called, 1 being restart, 0 being exit loop
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

        if not message.author.bot and connected:
            try:
                pd["content"]
                await on_message(message)
            except KeyError: # when content was not updated
                pass

    except discord.errors.NotFound:
        await log("message edit erorr", traceback.format_exc())
    
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
    global phyner_webhook_ids
    global phyner_reaction_adds
    global phyner_reaction_removes
    global phyner_custom_command_guild_ids

    if not connected: # we aint ready yet
        return

    error = False
    try:
        # prep message content for use
        args, mc = Support.get_args_from_content(message.content)

        ## BEGIN CHECKS ##

        try:
            is_webhook = message.webhook_id in phyner_webhook_ids
        except:
            log("webhook error", traceback.format_exc())
            return

        if not message.author.bot or is_webhook: # not a bot and webhook we care about
                

            try:
                guild_prefix = guild_prefixes[message.guild.id if message.guild else message.author.id]
            except KeyError:
                guild_prefix = None

            if (
                (
                    host == "PI4" and # is PI4
                    (
                        (
                            message.mentions and 
                            message.mentions[0].id == Support.ids.phyner_id and 
                            str(Support.ids.phyner_id) in args[0]
                        ) or # @Phyner command
                        guild_prefix and mc[:len(str(guild_prefix))+1] == guild_prefix + " " # start of content = guild prefix
                    )
                ) or (
                    host == "PC" and # is PC
                        (args[0] in ["11p", "``p"]) # 11p command
                )
            ):
                log("COMMAND", f"{message.author.id}, '{message.content}'\n")

                phyner = Support.get_phyner_from_channel(message.channel)
                is_mo = message.author.id == Support.ids.mo_id

                message.author = phyner if is_webhook else message.author
                author_perms = Support.get_member_perms(message.channel, message.author)


                ## COMMAND CHECKS ##


                ## CHECK FOR UPCOMING RESTART ##

                restart_delta = (restart_time - datetime.utcnow()).seconds
                if restart_delta < restart_interval and not is_mo:
                    description = f"**{phyner.mention} is about to {'restart' if restart else 'shut down'}. "
                    if restart:
                        description += f"Try again in {restart_delta + restart_interval} seconds, or watch for its status to change.**" 
                    else:
                        description += "Try again when it comes back online.**"

                    await Support.simple_bot_response(message.channel, description=description, reply_message=message)
                    return


                ## MO ##

                if is_mo:
                    if args[1] == "test":
                        import Test
                        await Test.test(client, message, args)
                        return
                        
                    elif args[1] == "setavatar":
                        with open('Images/9b9c9f.png', 'rb') as f:
                            await client.user.edit(avatar=f.read())
                        return

                    elif args[1] == "guild":
                        guild = client.get_guild(int(args[2]))

                        description = f"**Members:** {len(guild.members)}\n"
                        description += f"**Joined:** {datetime.strftime(phyner.joined_at, Support.short_date_1)}\n\n"

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

                if args[1] in ["?", "search"]:
                    await Help.search(message, args)

                elif args[1] in ["help", "h"]:
                    await Help.send_help_embed(client, message, Help.help_links.general)

                elif args[1] in ["commands", "cmds"]:
                    await Help.send_help_embed(client, message, Help.help_links.command_list_1)

                elif args[1] in ["invite"]:
                    await Support.simple_bot_response(message.channel,description=f"**{phyner.mention} is still a work in progress and is not publically available, yet. Join the [Phyner Support Server](https://discord.gg/suAQ2mUBYs) to stay up-to-date.**")
                    # await Help.send_help_embed(client, message, Help.help_links.invite_phyner) # FIXME NO INVITE RESPONSE

                elif args[1] in ["ids", "id"]:
                    await Help.send_help_embed(client, message, Help.help_links.ids)

                elif args[1] == "ping":
                    await General.send_ping(client, message)

                elif args[1] in Delete.delete_aliases:
                    await Delete.main(client, message, args, author_perms)

                elif args[1] in General.say_aliases:
                    await General.say(client, message, args[2:])

                elif args[1] in Support.edit_aliases:
                    await General.say(client, message, args[2:], is_edit=True)

                elif args[1] in General.feedback_aliases:
                    await General.feedback(client, message, args[1:])


                
                ## COPY ##

                elif args[1] in Copy.copy_aliases + Copy.replace_aliases:
                    await Copy.main(client, message, args[1:], author_perms)

                
                ## CUSTOM COMMANDS ##

                elif args[1] in CustomCommands.custom_command_aliases:
                    command, is_new = await CustomCommands.main(client, message, args[2:], author_perms)
                    if is_new:
                        phyner_custom_command_guild_ids = CustomCommands.get_guild_ids()

                    if args[2] in CustomCommands.create_aliases: # because main returns after create statment, we gotta check if we need to send the edit_command bit
                        await CustomCommands.edit_command(client, message, command)


                ## EMBED ##

                elif args[1] in Embeds.embed_aliases:
                    await Embeds.main(client, message, args, author_perms)



                ## GUILDS ##

                elif args[1] == "prefix":
                    phyner_guild, guild_prefixes = await Guilds.set_prefix(message, args, author_perms)


                ## MORSE ##

                elif args[1] == "morse":
                    await Morse.main(client, message, args)


                ## ROLE ##

                elif args[1] in Role.role_aliases:
                    await Role.main(client, message, args[2:], author_perms)

                
                ## TABLES ##
                
                elif args[1] in Tables.table_aliases:
                    await Tables.main(client, message, args[1:], author_perms)


                ## WATCH ##

                elif args[1] in Events.events_aliases + Events.watching_aliases:
                    events = await Events.main(client, message, args[1:], author_perms)

                    if events:
                        if events[0].object.type == "webhook":
                            phyner_webhook_ids = Events.get_object_ids(Events.get_events(), "webhook")

                        elif events[0].event == "reaction_add":
                            phyner_reaction_adds = Events.get_event_events(Events.get_events(), "reaction_add")

                        elif events[0].event == "reaction_remove":
                            phyner_reaction_removes = Events.get_event_events(Events.get_events(), "reaction_remove")



                else:
                    await Help.send_help_embed(client, message, Help.help_links.simple)

                    if args[1]: # >= 1 arg given, gimme that insight
                        await Logger.log_error(client, f"command not recognized {message.content}")

                ''' END COMMAND CHECKS '''

            
            ''' CUSTOM COMMAND CHECKS '''

            if message.guild.id in phyner_custom_command_guild_ids: # custom command exists in this guild, check for existing prefix
                guild_commands = CustomCommands.get_guild_comamnds(guild_id=message.guild.id, prefix=args[0])

                if guild_commands: # command exists
                    await message.channel.trigger_typing()
                    await guild_commands[0].send_command(client, message)

            ''' END CUSTOM COMMAND CHECKS '''
            
            

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

        phyner = Support.get_phyner_from_channel(message.channel)

        remove_reaction = False
        if user: # message and user are found

            if not user.bot: # not bot reaction

                restart_delta = (restart_time - datetime.utcnow()).seconds
                if restart_delta < restart_interval:
                    return


                ## PHYNER REACTION ADD CHECKS 

                for event in phyner_reaction_adds:
                    if all([
                        event.guild_id == message.guild.id if message.guild else False,
                        event.condition.id == message.id,
                        str(event.object.id) == str(payload.emoji)
                    ]):
                        remove_reaction = await Events.perform_action(client, message, user, event)


                ## PHYNER REACTION REMOVE CHECKS 

                for event in phyner_reaction_removes:
                    if all([
                        event.guild_id == message.guild.id if message.guild else False,
                        event.condition.id == message.id,
                        str(event.object.id) == str(payload.emoji)
                    ]):
                        t_event = copy.deepcopy(event)

                        # need to do inverse
                        t_event.action.action = "remove_role" if event.action.action == "add_role" else t_event.action.action
                        t_event.action.action = "add_role" if event.action.action == "remove_role" else t_event.action.action

                        if t_event.action.action != event.action.action:
                            await Events.perform_action(client, message, user, t_event)


                ## EMBED CHECKS ##

                embed = message.embeds[0] if message.embeds else []

                if embed: # has embed
                    pass

                    if embed.title: # has title 
                        pass


                ## SERVER CHECKS ##

                # this is used to enable testing whilst running pi version
                okay_mobot_support = Support.ids.mobot_support_id if os.getenv("HOST") == "PC" else 0
                okay_phyner_support = Support.ids.phyner_support_id if okay_mobot_support else 0

                if message.guild:
                    if message.guild.id in [ # Templar Leagues
                        TemplarLeagues.templar_leagues_id,
                        TemplarLeagues.staff_templar_leagues_id, 
                        okay_mobot_support,
                        okay_phyner_support
                    ]:
                        await TemplarLeagues.on_reaction_add(client, message, user, payload)


                ## PHYNER AUTHOR ##

                if message.author.id == phyner.id: # phyner message

                    if payload.emoji.name == Support.emojis.counter_clockwise_arrows_emoji: # refresh button clicked

                        poss_table = Tables.get_table(message.id, message.guild.id if message.guild else message.author.id)
                        
                        if poss_table:
                            await message.add_reaction(Support.emojis._9b9c9f_emoji)
                            await poss_table[0].send_table(client)
                            await Support.remove_reactions(message, phyner, Support.emojis._9b9c9f_emoji)
                            remove_reaction = True


    

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


                ## PHYNER REACTION ADD CHECKS 

                for event in phyner_reaction_adds:
                    if all([
                        event.guild_id == message.guild.id if message.guild else False,
                        event.condition.id == message.id,
                        str(event.object.id) == str(payload.emoji)
                    ]):
                        t_event = copy.deepcopy(event)

                        # need to do inverse
                        t_event.action.action = "remove_role" if event.action.action == "add_role" else t_event.action.action
                        t_event.action.action = "add_role" if event.action.action == "remove_role" else t_event.action.action

                        if t_event.action.action != event.action.action:
                            await Events.perform_action(client, message, user, t_event)


                ## PHYNER REACTION REMOVE CHECKS 

                for event in phyner_reaction_removes:
                    if all([
                        event.guild_id == message.guild.id if message.guild else False,
                        event.condition.id == message.id,
                        str(event.object.id) == str(payload.emoji)
                    ]):
                        await Events.perform_action(client, message, user, event)

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
            type=discord.ActivityType.playing, name="@Phyner is finer."
        ),
        status=discord.Status.online
    )
# end startup

log("Connection", f"{host} Controller Connecting")

client.loop.create_task(startup())

client.run(os.getenv("TOKEN"))
print(restart)