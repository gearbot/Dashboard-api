from time import perf_counter_ns

from fastapi import APIRouter
from starlette.requests import Request

from Utils import Auth, Redis
from Utils.Responses import bad_request_response

router = APIRouter()


@router.get("/")
@Auth.auth_required
async def guild_list_endpoint(request: Request):
    # Grab the user's guilds from Discord

    start_time = perf_counter_ns()

    return_value = await Redis.ask_the_bot("guild_perms", user_id=request.session["user_id"])

    finish_time = perf_counter_ns()
    final_time = (finish_time - start_time) / 1000000
    print("The request took a total of: " + str(final_time))

    return return_value


@router.get("/{guild_id}/stats")
async def guild_stats_endpoint(request: Request, guild_id: int):
    async def handler():
        if guild_id is None:
            return bad_request_response

        server_info = await Redis.ask_the_bot("guild_info",
                                          user_id=request.session["user_id"],
                                          guid=guild_id
                                          )

        print(server_info)

        return server_info
    return await Auth.handle_it(request, handler)
