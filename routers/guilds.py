from enum import Enum
from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from Utils import Auth, Redis
from Utils.Responses import bad_request_response, unknown_config_response, no_roleid_response

router = APIRouter()


class ConfigSection(Enum):
    general = "GENERAL"
    roles = "ROLES"
    permissions = "PERMISSIONS"
    dash_security = "DASH_SECURITY"
    log_channels = "LOG_CHANNELS"
    message_logs = "MESSAGE_LOGS"
    censoring = "CENSORING"
    infractions = "INFRACTIONS"
    perm_overrides = "PERM_OVERRIDES"
    raid_handling = "RAID_HANDLING"
    anti_spam = "ANTI_SPAM"


def validate_req_structure(body: dict, required_fields: list):
    if list(body.keys()) != required_fields:
        return False
    return True

def validate_section(section: str):
    # Check for invalid or non-existant sections
    if section not in ConfigSection.__members__:
        return False
    return True

def validate_guild(guild_id: int):
    # Make sure the guild IDs fall into basic constraints
    if guild_id < 20000000000000000 or guild_id > 9223372036854775807:
        return False
    return True

def is_numeric(value):
    if type(value) == bool:
        return False
    try:
        int(value)
        return True
    except ValueError:
        return False


@router.get("/")
@Auth.auth_required
async def guild_list_endpoint(request: Request):
    # Grab the user's guilds from Discord
    return_value = await Redis.ask_the_bot("guild_perms", user_id=request.session["user_id"])
    return return_value


@router.get("/{guild_id}/info")
async def guild_stats_endpoint(request: Request, guild_id: int):
    async def handler():
        if not validate_guild(guild_id):
            return bad_request_response

        server_info = await Redis.ask_the_bot(
            "guild_info",
            user_id=request.session["user_id"],
            guild_id=guild_id
        )
        return server_info

    return await Auth.handle_it(request, handler)


@router.get("/{guild_id}/config/{section}")
async def get_config_section(request: Request, guild_id: int, section: str):
    async def handler():
        if not validate_guild(guild_id):
            return bad_request_response
        elif not validate_section(section):
            return unknown_config_response

        s = ConfigSection[section]
        return await Redis.ask_the_bot(
            "get_config_section",
            guild_id=guild_id,
            section=s.value,
            user_id=request.session["user_id"]
        )

    return await Auth.handle_it(request, handler)


@router.post("/{guild_id}/config/{section}")
async def update_config_section(request: Request, guild_id: int, section: str, config_values: dict):
    async def handler():
        if not validate_guild(guild_id):
            return bad_request_response
        elif not validate_section(section):
            return unknown_config_response

        s = ConfigSection[section]
        return await Redis.ask_the_bot(
            "replace_config_section",
            guild_id=guild_id,
            section=s.value,
            modified_values=config_values,
            user_id=request.session["user_id"]
        )

    return await Auth.handle_it(request, handler)

@router.patch("/{guild_id}/config/{section}")
async def update_config_section(request: Request, guild_id: int, section: str, config_values: dict):
    async def handler():
        if not validate_guild(guild_id):
            return bad_request_response
        elif not validate_section(section):
            return unknown_config_response

        s = ConfigSection[section]
        return await Redis.ask_the_bot(
            "update_config_section",
            guild_id=guild_id,
            section=s.value,
            modified_values=config_values,
            user_id=request.session["user_id"]
        )

    return await Auth.handle_it(request, handler)


@router.post("/{guild_id}/mute")
async def setup_mute(request: Request, guild_id: int, body: dict):
    async def handler():
        if not validate_guild(guild_id):
            return bad_request_response

        # Make sure the required parts are in the body
        if "role_id" not in body:
            return no_roleid_response
        elif "action" not in body:
            return bad_request_response

        # Be strict, only allow a properly formatted request
        if not validate_req_structure(body, ["action", "role_id"]):
            return bad_request_response

        # Make sure the role is a *possibly* valid 
        if not is_numeric(body["role_id"]) or int(body["role_id"]) <= 0:
            return bad_request_response

        # Make sure the action is valid
        if body["action"] not in ["setup", "cleanup"]:
            return bad_request_response

        return await Redis.ask_the_bot(
            f"{body['action']}_mute",
            guild_id=guild_id,
            role_id=body["role_id"],
            user_id=int(request.session["user_id"])
        )

    return await Auth.handle_it(request, handler)
