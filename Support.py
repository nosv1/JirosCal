''' IMPORTS '''

import asyncio
from bs4 import BeautifulSoup as bsoup
import discord
import gspread
import json
import re
import requests
import traceback
from types import SimpleNamespace

import os
from dotenv import load_dotenv
load_dotenv()

import Logger


''' CONSTANTS '''

host = os.getenv("HOST")

short_date_1 = "%b. %d, %Y"
short_date_2 = "%b. %d, %Y %H:%M"

## IDs ##
ids = SimpleNamespace(**{
    # user ids
    'mo_id' : 405944496665133058,
    'jiros_id' : 295650056189771776,
    'jc_id' : 794922853631000616,

    # guild ids
    'test_server' : 449249093059870720,

    # channel ids

})


## COLORS ##
colors = SimpleNamespace(**{
    'jc_grey' : 0x404040,
})


## CHARACTERS / EMOJIS ##
emojis = SimpleNamespace(**{
    'zero_width' : chr(8203), # or the thing in bewteen the dashes -​-
    'space_char' : "⠀",
    'bullet' : "•",
    'x_emoji' : "❌",
    'tick_emoji' : "✅",
    'ok_emoji' : "🆗",
    'i_emoji' : "🛈",
    'number_emojis' : ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"],
    'exclamation_emoji' : "❗",
    'question_emoji' : "❓",
    'clipboard_emoji' : "📋",
    'film_frames_emoji' : "🎞️",
    'pencil_emoji' : "✏️",
    'floppy_disk_emoji' :"💾",
    "_9b9c9f_emoji" : "<:9b9c9f:791658919948189736>",
    "pushpin_emoji" : "📌",
    "wrench_emoji" : "🔧",
    "wastebasket_emoji" : "🗑️",
    "zany_emoji" : "🤪",
    "robot_emoji" : "🤖",
    "counter_clockwise_arrows_emoji" : "🔄",
    "calendar_emoji" : "📆",
    "letter_emojis" : {"a" : "🇦", "b" : "🇧", "c" : "🇨", "d" : "🇩", "e" : "🇪", "f" : "🇫", "g" : "🇬", "h" : "🇭", "i" : "🇮", "j" : "🇯", "k" : "🇰", "l" : "🇱", "m" : "🇲", "n" : "🇳", "o" : "🇴", "p" : "🇵", "q" : "🇶", "r" : "🇷", "s" : "🇸", "t" : "🇹", "u" : "🇺", "v" : "🇻", "w" : "🇼", "x" : "🇽", "y" : "🇾", "z" : "🇿"}
})

## COMMON ALIASES ##
add_aliases = ["add", "+"]
remove_aliases = ["remove", "-"]
create_aliases = ["create", "new"] + add_aliases
edit_aliases = ["edit"]


''' SUPPORT FUNCTIONS '''

async def previous_action_error(client, message):
    jc = get_jc_from_channel(message.channel)

    description = f"**The previous action caused an error. {jc.mention} Support has been notified, and they are very sorry for the inconvenience.**\n\n"
    description += f"If you just inputted a command, double check your input, and see the `@{jc} <your_command> help` message. Also feel free to check `@{jc} bug help` for other options about reporting issues and getting help."

    embed = await simple_bot_response(message.channel,
        description=description,
        send=False
    )
    embed.add_field(name=emojis.space_char, value=f"{emojis.x_emoji} to dismiss")

    msg = await message.reply(embed=embed)
    await msg.add_reaction(emojis.x_emoji)

    await Logger.log_error(client, traceback.format_exc())

    def reaction_check(reaction, r_user):
        return (
            reaction.message == msg and
            r_user.id != client.user.id and
            str(reaction.emoji) in [emojis.x_emoji]
        )
    # end reaction_check

    try:
        reaction, user = await client.wait_for("reaction_add", check=reaction_check, timeout=90)
        await msg.delete()

    except asyncio.TimeoutError:
        embed = delete_last_field(embed)
        await msg.edit(embed=embed)
        await remove_reactions(msg, client.user, emojis.x_emoji)
# end previous_action_error


async def missing_permission(missing_permission, message):
    await simple_bot_response(message.channel,
        title="Missing Permission",
        description=f"You must have the `{missing_permission}` to use this command.",
        reply_message=message
    )
# end missing_permission



## gspread stuff

def find_value_in_range(r, value, lower=False):
    """
        returns index of value
    """

    for i, c in enumerate(r):
        if c.value == value or (lower and c.value.lower() == value.lower()):
            return i

    return -1
# end find_value_in_range


def messageOrMsg(msg):  
    """
        figure out if bot msg or user message, once again got tired of typing this :D
        returns embed, message, msg
    """

    embed = msg.embeds[0] if msg and msg.embeds else discord.Embed()
    message = None if msg and msg.author.id in [ids.jc_id] else msg  # is user message
    msg = None if message else msg  # is bot msg

    return embed, message, msg
# end messageOrMsg

def get_jc_from_channel(channel):
    if channel.type != discord.ChannelType.private:
        return [member for member in channel.members if member.id == ids.jc_id][0]
    else:
        return channel.me
# end get_jc_from_channel


def get_id_from_str(str):
    """
        returns list
    """
    return [int(i) for i in re.findall(r"(\d{17,})", str)]
# end get_id_from_str


def get_args_from_content(content):
    """
        returns args, content
    """
    content = re.sub(r"[“”]", '"', content)
    content = re.sub(r"[\n\t\r]", ' ', content)
    content += " "
    while "  " in content:
        content = content.replace("  ", " ")
    args = content.split(" ")

    return args, content
# end get_args_from_content



## embed stuff ##

def load_embed_from_Embeds(path):
    """
        in path
        return embed
    """

    with open(path, "r") as embed_file:
        embed = discord.Embed().from_dict(json.load(embed_file))

    return embed
# end load_embed_from_Embeds


def convert_embed_dict_to_create_messages(embed_dict):

    create_messages = ["```"]

    for key in embed_dict:

        line = ""

        if key in ["color", "colour"]:
            line += f".{key} #{str(hex(int(embed_dict[key])))[2:]}\n"

        elif key in ["title", "description"]:
            line += f".{key} {embed_dict[key]}\n"


        elif key in ["author", "footer"]:
            for f_key in embed_dict[key]:
                if f_key in ["text", "name"]:
                    line += f".{key} {embed_dict[key][f_key]}\n"

                elif f_key in ["icon_url", "url"]:
                    line += f".{key}_{f_key} {embed_dict[key][f_key]}\n"


        elif key in ["thumbnail", "image"]:
            line += f".{key}_url {embed_dict[key]['url']}\n"


        if not line:
            if key in ["fields"]:
                for i in range(len(embed_dict[key])):
                    
                    f_line = ""
                    for f_key in embed_dict[key][i]:
                        f_line += f".{key[:-1]}{i+1}_{f_key} {embed_dict[key][i][f_key]}\n"
                    
                    f_line = f_line.replace("```", "`\`\`\`") + "\n"
                    if len(create_messages[-1] + f_line) < 1000:
                        create_messages[-1] += f_line

                    else:
                        create_messages[-1] += "```"
                        create_messages.append(f"```{f_line}")
            continue

        line = line.replace('```', '\`\`\`') + "\n"
        if len(create_messages[-1] + line) < 1000:
            create_messages[-1] += line

        else:
            create_messages[-1] += "```"
            create_messages.append(f"```{line}")



    create_messages[-1] += "```"
    return [c_m.replace(f"{emojis.space_char}", "\\s").replace(f"{emojis.bullet}", "\\b").replace(f"{emojis.zero_width}", "\\z") for c_m in create_messages]
# end convert_embed_dict_to_create_messages


def update_field_value(embed, name, value):
    embed = embed.to_dict()
    for i in range(len(embed["fields"])):
        if name in embed["fields"][i]["name"]:
            embed["fields"][i]["value"] = value
            break
    embed = discord.Embed().from_dict(embed)
    return embed
# end update_field_value


def confirm_input_last_field(embed):
    embed = embed.to_dict()
    field_footer = embed["fields"][-1]["value"]
    embed["fields"][-1]["value"] = "**Confirming Input...**"
    embed = discord.Embed().from_dict(embed)
    return field_footer, embed
# end confirm_input_last_field


def revert_confirm_input_last_field(field_footer, embed):
    embed = embed.to_dict()
    embed["fields"][-1]["value"] = field_footer
    embed = discord.Embed().from_dict(embed)
    return embed
# end revert_confirm_input_last_field


def revert_confirm_input_last_field_exclamation(field_footer, embed):
    lines = field_footer.split("\n")
    lines[-2] = f"**{lines[-2]} {emojis.exclamation_emoji}**"

    embed = embed.to_dict()
    embed["fields"][-1]["value"] = "\n".join(lines)
    embed = discord.Embed().from_dict(embed)
    return embed
# end revert_confirm_input_last_field


def delete_last_field(embed):
    embed = embed.to_dict() if type(embed) != dict else embed
    del embed["fields"][-1]
    return discord.Embed().from_dict(embed)
# end delete_last_field


def switch_last_two_fields(embed):
    embed = embed.to_dict() if type(embed) != dict else embed
    t_field = embed["fields"][-2]
    del embed["fields"][-2]
    embed["fields"].append(t_field)
    return discord.Embed().from_dict(embed)
# end switch_last_two_fields



def quote(s):
    return f"'{s}'"
# end quote



## clearing reactions ##

async def clear_reactions(msg):
    try:
        await msg.clear_reactions()
    except discord.errors.Forbidden:
        pass
    except discord.errors.NotFound:
        pass
# end clear_reactions


async def remove_reactions(msg, user, reactions):
    reactions = [reactions] if type(reactions) != list else reactions
    for reaction in reactions:
        try:
            await msg.remove_reaction(reaction, user)
        except:
            pass
# end remove_reactions


def is_DMChannel(channel):
    return channel.type == discord.ChannelType.private
# end is_dm


def get_member_perms(channel, member):
    """
        Gets the permissions for a given member for a given channel. If the member is Mo, all permissions are returned as True.
    """

    author_perms = dict(channel.permissions_for(member))
    is_mo = member.id == ids.mo_id
    if is_mo:
        for permission  in author_perms:
            author_perms[permission] = True
    author_perms = SimpleNamespace(**author_perms) # converts dict back to class
    return author_perms
# end get_member_perms


async def simple_bot_response(channel, author=discord.Embed().Empty, author_url=discord.Embed().Empty, author_icon_url=discord.Embed().Empty, title=discord.Embed().Empty, thumbnail_url=discord.Embed().Empty, description=discord.Embed().Empty, footer=discord.Embed().Empty, send=True, reply_message=False, delete_after=None):
    """
        Bot sends message as basic embed
        reply_message is defaulted to False, but expects a discord.Message if declared in call
    """
    # TODO pass in embed_dict as starting point, no overwriting
    is_dm = is_DMChannel(channel)
    jc = get_jc_from_channel(channel)

    embed = discord.Embed()
    embed.colour = colors.jc_grey if is_dm else jc.roles[-1].color

    if author or author_icon_url or author_url:
        embed.set_author(
            name=author if author else emojis.space_char,
            url=author_url,
            icon_url=author_icon_url
        )


    embed.title = title
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    embed.description = description

    if footer:
        embed.set_footer(text=footer)


    if send:
        if type(reply_message) == discord.message.Message:
            msg = await reply_message.reply(embed=embed, delete_after=delete_after)
            
        else:
            msg = await channel.send(embed=embed, delete_after=delete_after)
                
        return msg

    else:
        return embed
# end botResponse

async def process_complete_reaction(message, remove=True, rejected=False):
    await message.add_reaction(emojis.tick_emoji if not rejected else emojis.x_emoji)
    if remove:
        await asyncio.sleep(3)
        await remove_reactions(message, get_jc_from_channel(message.channel), emojis.tick_emoji)
# end process_complete_reaction


def search_github(query):
    """
        search github wiki
        return list of results [{link, title, p}]
    """
    while " " in query:
        query = query.replace(" ", "+")

    html = str(bsoup(requests.get(f"https://github.com/nosv1/JirosCal/search?q={query}&type=wikis").text, "html.parser"))
    results = html.split("class=\"f4 text-normal\"")
    results = results[1:] if len(results) > 1 else []
    for i, result in enumerate(results):
        results[i] = {
            'link' : "https://github.com" + result.split("href=\"")[1].split("\"")[0],
            'title' : result.split("title=\"")[1].split("\"")[0],
            'p' : "\n".join(re.sub(r"(<|(</))(em>)", "**", result.split('<p')[1].split("\">")[1].split("</p>")[0].strip()).split(emojis.space_char))
        }
    return results
# end search


async def restart(client, message, restart_interval, restart=True):
    """
        close or restart pi4 host
    """

    msg = None
    if host == "PI4":
        if restart: # only PI4 has ability to restart
            Logger.log(f"Connection", f"{host} Restarting see you on the other side...")


        await client.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing, 
                name=f"{'Restarting' if restart else 'Temporarily shutting down'} soon!"
            ),
            status=discord.Status.idle
        )

        msg = await simple_bot_response(
            message.channel, 
            description=f"**{'Restarting' if restart else 'Shutting down'} in {restart_interval} seconds.**"
        )

    return (1 if restart else 0), msg
# end restart  