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

OUTAGE_DETECTION: bool = config["bot_outage"]["outage_detection"]
MAX_BOT_OUTAGE_WARNINGS: int = config["bot_outage"]["max_bot_outage_warnings"]
BOT_OUTAGE_WEBHOOK: str = config["bot_outage"]["bot_outage_webhook"]
BOT_OUTAGE_MESSAGE: dict = config["bot_outage"]["bot_outage_message"]
BOT_OUTAGE_PINGED_ROLES: list = config["bot_outage"]["bot_outage_pinged_roles"]

r = config["redis"]
if r.get("socket", None) is None:
    REDIS_ADDRESS = (r["host"], r["port"])
else:
    REDIS_ADDRESS = r["socket"]
CORS_ORGINS: list = config["cors_orgins"]
TRUSTED_HOSTS: list = config["trusted_hosts"]