from enum import Enum
from fastapi import APIRouter
from starlette.requests import Request

from Utils import Auth, Redis
from Utils.Responses import bad_request_response

router = APIRouter()


class ConfigSection(Enum):
    general = "GENERAL"
    roles = "ROLES"
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

        server_info = await Redis.ask_the_bot("guild_info",
                                              user_id=request.session["user_id"],
                                              guild_id=guild_id
                                              )

        print(server_info)

        return server_info

    return await Auth.handle_it(request, handler)


@router.get("/{guild_id}/config/{section}")
async def get_config_section(request: Request, guild_id: int, section: str):
    async def handler():
        if guild_id is None or section is None or ConfigSection[section] is None:
            return bad_request_response
        return await Redis.ask_the_bot("get_config_section", guild_id=guild_id, section=ConfigSection[section].value, user_id=request.session["user_id"])
    return await Auth.handle_it(request, handler)
