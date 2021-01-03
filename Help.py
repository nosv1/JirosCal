''' IMPORTS '''

import asyncio
from types import SimpleNamespace

import discord


# import Embeds
import Guilds
import Logger
import Support



''' CONSTANTS '''

help_aliases = ["help", "h", "?", " ", ""] # these are used for command words' help, not ..p help

# Help Embed Links
help_links = SimpleNamespace(**{
    "simple" : {"link" : "https://discord.com/channels/789181254120505386/789566872139726938/789566903605002270"},

    "general" : {"link" : "https://discord.com/channels/789181254120505386/789181637748588544/789187242006020126"},

    "command_list_1" : {"link" : "https://discord.com/channels/789181254120505386/789586399975178252/789586453978021898"},
    "command_list_2" : {"link" : "https://discord.com/channels/789181254120505386/789586399975178252/791420646713458718"},

    "invite_jc" : {"link" : "https://discord.com/channels/789181254120505386/791034004174405642/791034163230408724"},

    "ids" : {
        "link" : "https://discord.com/channels/789181254120505386/789523955751976970/789565197312065546",

        "demo" : "https://cdn.discordapp.com/attachments/789218327473160243/790481979794653215/ids.gif"
        },

    "embed_menu" : {"link" : "https://discord.com/channels/789181254120505386/791231253822439455/791231381685927936"},
    "creating_and_editing_embeds" : {"link" : "https://discord.com/channels/789181254120505386/791231253822439455/791233860896948227"},

    "event_menu" : {"link" : "https://discord.com/channels/789181254120505386/791985443808739338/791993599990562847"},
    "watching_emojis" : {"link" : "https://discord.com/channels/789181254120505386/791985443808739338/792009489138188338"},
    "add_remove_role" : {"link" : "https://discord.com/channels/789181254120505386/791985443808739338/792017098363764774"},
    "create_private_text_channel" : {"link" : "https://discord.com/channels/789181254120505386/791985443808739338/792029111307468810"},
})


''' FUNCTIONS '''

async def search(message, args):
    """
        Sending a git hub search result
        https://github.com/nosv1/jc/search?q=&type=wikis
    """

    jc = Support.get_jc_from_channel(message.channel)
    

    query = " ".join(args[2:]).strip()
    results = None

    if query:
        results = Support.search_github(query)

        results_description = ""
        outputted = 0
        for result in results:
            if len(results_description) < 1000:
                outputted += 1

                # **title** - `command`
                title = result['title'].split("`") # title should be >> title `command` >> [title, command, '']
                command = title[1] if len(title) > 1 else ""
                results_description += f"**{title[0]}** - `{command}`\n"
                # results_description += f"**[{title[0]}]({result['link']})**" + (f" - `{command}`\n" if command else "\n")

                # p = result['p'].split("\n") + [" "] # [@jc command help, snippet]
                # results_description += f"`{p[0].strip().replace('**', '')}`\n\n"

                # \/ old, used to be Title \n Command \n Body
                # results_description += f"`{p[0].strip().replace('**', '')}`\n{p[1].strip()}\n\n"


        if not results_description: # no results
            results_description += f"{jc} help\n"


        await Support.simple_bot_response(message.channel,
            title = f"{len(results)} Result{'s' if outputted != 1 else ''}",
            description=results_description
        )

        Logger.log("search", results_description)


    else:
        description = f"`@{jc} ? <search_words>`\n"
        description += f"`@{jc} ? custom embeds`"
        await Support.simple_bot_response(message.channel,
            title="No Search Words Provided",
            description=description,
            reply_message=message
        )

        Logger.log("Bot Reponse", "Simple Help Search")
# end search


''' HELP EMBEDS '''

async def send_help_embed(client, msg, embed_link, default_footer=True, demo=False):
    """
        Help embeds are saved in /Embeds as well as in jc Support's HELP EMBEDS category
        The links are saved in the global variables at the top of this channel and sent using the saved versions in /Embeds
    """

    guild_prefix = Guilds.get_guild_prefix(msg.guild.id if msg.guild else msg.author.id)
    reactions = []
    message_author = None
    def reaction_check(reaction, r_user):
        return (
            reaction.message == msg and
            r_user.id == message_author.id and
            str(reaction.emoji) in reactions
        )
    # end reaction_check

    while True: # every iteration the thing that changes is the embed_link

        # get embed, message and channel
        channel = msg.channel
        embed, message, msg = Support.messageOrMsg(msg)
        message_author = message.author if message else message_author

        embed = Embeds.get_saved_embeds(link=embed_link["link"])[0].embed
        if demo:
            embed.set_image(url=embed_link["demo"])


        # add a footer if needed
        footer = []
        reactions = []
        if default_footer:
            if embed_link not in [help_links.general]: # not general help embed
                footer.append(f"{Support.emojis.question_emoji} `{guild_prefix} help`")
                reactions.append(Support.emojis.question_emoji)

            if embed_link not in [help_links.command_list_1, help_links.command_list_2]: # not command list embed, this check is also in the wait portion below
                footer.append(f"{Support.emojis.clipboard_emoji} `{guild_prefix} commands`")
                reactions.append(Support.emojis.clipboard_emoji)

            else: # is command list
                reactions += Support.emojis.number_emojis[1:3] ## NOTICE THE 1:3 ##

            if "demo" in embed_link: # has demo
                footer.append(f"{Support.emojis.film_frames_emoji} `Demo`")
                reactions.append(Support.emojis.film_frames_emoji)

            if footer:
                embed.add_field(name=Support.emojis.space_char, value=" **|** ".join(footer))

                if msg:
                    await Support.clear_reactions(msg)


        # send embed
        jc = Support.get_jc_from_channel(channel)
        embed.color = jc.roles[-1].color if type(jc) == discord.member.Member else Support.colors.jc_blue
        
        if msg:
            await msg.edit(embed=embed)

        else:
           msg = await channel.send(embed=embed)


        # add rections
        for reaction in reactions:
            await msg.add_reaction(reaction)

        Logger.log("Help Embed", embed_link)


        # wait
        if footer:
            try:
                reaction, user = await client.wait_for("reaction_add", check=reaction_check, timeout=120)

                if str(reaction.emoji) == Support.emojis.question_emoji: # toggle general help
                    embed_link = help_links.general

                elif str(reaction.emoji) == Support.emojis.clipboard_emoji: # toggle page one of command list
                    embed_link = help_links.command_list_1

                elif str(reaction.emoji) == Support.emojis.film_frames_emoji: # toggle demo
                    demo = not demo


                if (
                    embed_link in [help_links.command_list_1, help_links.command_list_2] and # is command list
                    str(reaction.emoji) in Support.emojis.number_emojis[1:3] # and number emoji clicked,       ## NOTICE THE 1:3 ##
                ):
                    embed_link = eval(f"help_links.command_list_{Support.emojis.number_emojis.index(str(reaction.emoji))}")


            except asyncio.TimeoutError:
                await Support.clear_reactions(msg)
                embed = Support.delete_last_field(embed)
                try:
                    await msg.edit(embed=embed)
                except discord.errors.NotFound:
                    pass
                break
            
        else:
            break

    # end while

    return msg
# end send_help_embed