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
ALLOWED_USERS = config["allowed_users"]

r = config["redis"]
if r.get("socket", None) is None:
    REDIS_ADDRESS = (r["host"], r["port"])
else:
    REDIS_ADDRESS = r["socket"]
CORS_ORGINS: list = config["cors_orgins"]
TRUSTED_HOSTS: list = config["trusted_hosts"]