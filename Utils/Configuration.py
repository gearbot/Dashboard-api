import json

with open("config.json") as config_file:
    config = json.load(config_file)

CLIENT_ID = config["clientID"]
CLIENT_SECRET = config["clientSecret"]
REDIRECT_URI = config["redirect_uri"]
CLIENT_URL = config["client_url"]
SESSION_TIMEOUT_LEN = config["session_timeout_length"] * 60*60*24
SESSION_KEY = config["session_key"]
API_LOCATION = "https://discordapp.com/api/v6"
