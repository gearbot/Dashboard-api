from fastapi import APIRouter, Cookie
from starlette.responses import JSONResponse
from starlette.requests import Request

router = APIRouter()

from Utils import Auth, Redis

from time import perf_counter_ns

bad_request_resp = JSONResponse({ "status": "BAD REQUEST"}, status_code=400)

@router.get("/")
async def read_root():
    return {"status": "WIP"}


@router.get("/test")
async def test(request: Request):
    request.session["test"] = "testing"
    return {"status": "TESTING"}


@router.get("/test2")
async def get_test(request: Request):
    return {"test": request.session["test"]}


@router.get("/logout")
@Auth.auth_required
async def logout(request: Request):
    for k in ["user_id", "refresh_token", "access_token", "expires_at"]:
        del request.session[k]
    return JSONResponse(dict(status="Success"))


@router.get("/whoami")
@Auth.auth_required
async def identify_endpoint(request: Request):
    return await Redis.ask_the_bot("user_info", user_id=request.session["user_id"])

@router.get("/guilds")
@Auth.auth_required
async def guild_list_endpoint(request: Request):
    # Grab the user's guilds from Discord

    start_time = perf_counter_ns()

    return_value = await Redis.ask_the_bot("guild_perms", user_id=request.session["user_id"])

    finish_time = perf_counter_ns()
    final_time = (finish_time - start_time) / 1000000
    print("The request took a total of: " + str(final_time))

    return return_value

@router.get("/guilds/{guild_id}/stats")
async def guild_stats_endpoint(guild_id: int, request: Request):
    print(request)
    print(guild_id)
    return "Made it"
    if guild_id == None:
        return bad_request_resp
    
    server_info = await Redis.ask_the_bot("guild_info", 
        user_id=request.session["user_id"],
        guid=guild_id
    )

    print(server_info)

    return server_info