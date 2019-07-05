from enum import Enum
from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse

from Utils import Auth, Redis
from Utils.Responses import bad_request_response, unknown_config_response

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


@router.get("/")
@Auth.auth_required
async def guild_list_endpoint(request: Request):
    # Grab the user's guilds from Discord
    return_value = await Redis.ask_the_bot("guild_perms", user_id=request.session["user_id"])
    return return_value


@router.get("/{guild_id}/info")
async def guild_stats_endpoint(request: Request, guild_id: int):
    async def handler():
        if guild_id is None:
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
        if guild_id is None or section is None:
            return bad_request_response
        try:
            s = ConfigSection[section]
            return await Redis.ask_the_bot(
                "get_config_section",
                guild_id=guild_id,
                section=s.value,
                user_id=request.session["user_id"]
            )
        except KeyError:
            return unknown_config_response

    return await Auth.handle_it(request, handler)


@router.patch("/{guild_id}/config/{section}")
async def update_config_section(request: Request, guild_id: int, section: str, config_values: dict):
    async def handler():
        if guild_id is None or section is None:
            return bad_request_response
        try:
            s = ConfigSection[section]
            return await Redis.ask_the_bot(
                "update_config_section",
                guild_id=guild_id,
                section=s.value,
                modified_values=config_values,
                user_id=request.session["user_id"]
            )
        except KeyError:
            return unknown_config_response

    return await Auth.handle_it(request, handler)


def is_numeric(value):
    try:
        int(value)
        return True
    except ValueError:
        return False

@router.post("/{guild_id}/setup_mute")
async def setup_mute(request: Request, guild_id: int, body: dict):
    if "role_id" not in body:
        return JSONResponse({"status": "BAD REQUEST", "errors": ["missing role_id"]}, status_code=400)

    async def handler():
        return await Redis.ask_the_bot("setup_mute", guild_id=guild_id, role_id=body["role_id"], user_id=int(request.session["user_id"]))

    return await Auth.handle_it(request, handler)


@router.post("/{guild_id}/cleanup_mute")
async def setup_mute(request: Request, guild_id: int, body: dict):
    if "role_id" not in body:
        return JSONResponse({"status": "BAD REQUEST", "errors": ["missing role_id"]}, status_code=400)

    async def handler():
        return await Redis.ask_the_bot("cleanup_mute", guild_id=guild_id, role_id=body["role_id"], user_id=int(request.session["user_id"]))

    return await Auth.handle_it(request, handler)
