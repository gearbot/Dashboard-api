import json

with open("config.json") as config_file:
    config = json.load(config_file)

CLIENT_ID: int = config["clientID"]
CLIENT_SECRET: str = config["clientSecret"]
REDIRECT_URI: str = config["redirect_uri"]
CLIENT_URL: str = config["client_url"]
SESSION_TIMEOUT_LEN: int = config["session_timeout_length"] * 60*60*24
SESSION_KEY: str = config["session_key"]
API_LOCATION = "https://discordapp.com/api/v6"

__REDIS_PARTS = config["redis_address"]
REDIS_ADDRESS = (__REDIS_PARTS[0], __REDIS_PARTS[1])
CORS_ORGINS: list = config["cors_orgins"]
TRUSTED_HOSTS: list = config["trusted_hosts"]