import asyncio

from fastapi import APIRouter, Cookie
from starlette.responses import RedirectResponse
from starlette.requests import Request
from Utils.Configuration import CLIENT_ID, REDIRECT_URI, CLIENT_URL, API_LOCATION
from Utils import Auth
from secrets import token_urlsafe

from Utils.Prometheus import notice_session

router = APIRouter()

# Code Generation
@router.get("/login")
async def discord_oauth_redir():
    state_key = token_urlsafe(20)
    response = RedirectResponse(
        f"{API_LOCATION}/oauth2/authorize?client_id={CLIENT_ID}&state={state_key}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify guilds",
        status_code=307
    )
    # We won't need this cookie 5 minutes later
    response.set_cookie(key="state_key", value=state_key, expires=300)
    return response

# Callback handling
@router.get("/callback")
async def handle_callback(error: str=None, code: str=None, state: str=None, request: Request=None, state_key: str = Cookie(None)):
    if error != None: # They must of denied the auth request if this errors
        return RedirectResponse(f"{CLIENT_URL}")

    if state != state_key:
        return RedirectResponse("https://i.imgur.com/vN5jG9r.mp4")

    if code != None:
        _, user_id = await Auth.get_bearer_token(request=request, auth_code=code)

        # Track the current number of sessions we know of
        loop = asyncio.get_running_loop()
        loop.create_task(notice_session(user_id, True))

        return RedirectResponse(f"{CLIENT_URL}/pleaseclosethispopupformektxh", status_code=307)
    else:
        return RedirectResponse("https://i.imgur.com/vN5jG9r.mp4")
