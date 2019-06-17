from secrets import token_urlsafe

from fastapi import APIRouter
from starlette.responses import RedirectResponse
from starlette.requests import Request

router = APIRouter()

from api import API_LOCATION, REDIRECT_URI, CLIENT_ID, CLIENT_URL, KEY_CYCLE_LENGTH
from Utils import Auth, Redis

# Code Generation
@router.get("/login")
async def discord_oauth_redir():
    discord_redir_url = RedirectResponse(
        f"{API_LOCATION}/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify guilds",
        status_code=307
    )
    return discord_redir_url


# Callback handling
@router.get("/callback")
async def handle_callback(code: str, request: Request):
    bearer_token, refresh_token = await Auth.get_bearer_token(code, False, None, request)

    user_id = await get_discord_user_info((bearer_token, refresh_token), request)
    refresh_key = f"drefreshtoken:{user_id}"

    redis = await Redis.get_redis(1)
    pipeline = redis.pipeline()
    pipeline.set(refresh_key, refresh_token)
    pipeline.expire(refresh_key, KEY_CYCLE_LENGTH.total_seconds())
    await pipeline.execute()

    user = {
        "id": user_id,
        "token": bearer_token
    }
    
    dashboard_redir = RedirectResponse(CLIENT_URL)

    user_token = Auth.generate_access_token(user, request)
    dashboard_redir.set_cookie("authtoken", user_token)

    return dashboard_redir

async def get_discord_user_info(tokens, request: Request):
    refresh_token = tokens[1]
    token = tokens[0]

    session_pool = request.app.session_pool

    async with session_pool.get(f"{API_LOCATION}/users/@me",
        headers={"Authorization": f"Bearer {token}"}) as user_resp:
        
        if user_resp.status == 401:
            #TODO: Proper refresh token support...
            print("The token expired!")

        user_info = await user_resp.json()
        print(user_info)
        return user_info["id"]
