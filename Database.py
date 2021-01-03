import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()

def connect_database(db_name=os.getenv("DB_NAME")):
  class JirosDB:
    def __init__(self, connection, cursor):
      self.connection = connection
      self.cursor = cursor
  # end JirosDB

  db_connection = mysql.connector.connect(
    host = os.getenv("DB_HOST"),
    user = os.getenv("DB_USER"),
    password = os.getenv("DB_PASSWORD"),

    database = db_name,
    charset = "utf8mb4",
    use_unicode = True,
    buffered = True
  )
  db_cursor = db_connection.cursor()
  return JirosDB(db_connection, db_cursor)
# end connect_database

def replace_chars(bad_string):
  return bad_string.replace("'", "''").replace("\\", "\\\\")
# end replace_chars