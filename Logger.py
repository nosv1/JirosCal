''' IMPORTS '''

import discord
from datetime import datetime
import pathlib

import os
from dotenv import load_dotenv
load_dotenv()

import Support



''' CONSTANTS '''

time_format = "%Y %b %d %H.%M.%S"



''' FUNCTIONS '''

def create_log_file():
    """
        Creates a blank log file in Logs with the current date as the name

        ------
        Most recent log path accessed by:
        import pathlib
        log_path = list(pahtlib.Path(\"Logs\").iterdir())[-1]
    ------
    """

    now = datetime.utcnow()
    log_path = f"Logs/{now.strftime(time_format)}.txt"
    with open(log_path, "a+", encoding="utf-8") as log_file:

        header = ""
        header += "JirosCal\n"
        header += "Creator:\n"
        header += "\tMo#9991\n\n"

        log_file.write(header)

    log("Log", "Created")
# end create_log_file


def open_active_log_file(read_binary=False):
    """
        Opens the most recent log file created.
    """

    logs_folder = pathlib.Path("Logs")
    log_path = sorted(logs_folder.iterdir(), key=os.path.getmtime)[-1]
    log_file = open(log_path, "a+", encoding="utf-8") if not read_binary else open(log_path, "rb")

    return log_file
# end open_log_file


def log(action, detail=""):
    """
        Writes "{current_time} {action} {detail}\n" to the most recent log file

        ------
        Examples:
        log("Log Created")
        03 Dec 20 07.56.04 [LOG CREATED]

        log("Log Created", detail="This is a new log")
        03 Dec 20 07.56.04 [LOG CREATED] This is a new log
        ------
    """

    log_file = open_active_log_file()
    now = datetime.utcnow()

    line = f"{now.strftime(time_format)} [{action.upper()}] {detail}\n" 
    print(line, end="")
    log_file.write(line)
    log_file.close
# end log


async def log_error(client, traceback):
    """ 
        Writes "{current_time} ERROR \ntraceback" to the most recent log file
        Sends Log File to Mo
    """

    log_file = open_active_log_file()
    now = datetime.utcnow()

    line = f"{now.strftime(time_format)} [ERROR]\n{traceback}\n"
    print(line)
    log_file.write(line)
    log_file.close()

    log_file = open_active_log_file(read_binary=True)

    if os.getenv("HOST") != "PC":
        await client.get_user(Support.ids.mo_id).send(content=f"```{traceback}```", file=discord.File(log_file, now.strftime(time_format)))
    log_file.close()
# end log_error