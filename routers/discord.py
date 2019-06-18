from fastapi import APIRouter, Cookie
from starlette.responses import RedirectResponse
from starlette.requests import Request
from Utils.Configuration import CLIENT_ID, REDIRECT_URI, CLIENT_URL, API_LOCATION
from Utils import Auth
from secrets import token_urlsafe

router = APIRouter()

# Code Generation
@router.get("/login")
async def discord_oauth_redir():
    state_key = token_urlsafe(20)
    response = RedirectResponse(
        f"{API_LOCATION}/oauth2/authorize?client_id={CLIENT_ID}&state={state_key}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify guilds",
        status_code=307
    )
    response.set_cookie(key="state_key", value=state_key)
    return response

# Callback handling
@router.get("/callback")
async def handle_callback(code: str, state: str, request: Request, state_key: str = Cookie(None)):
    if state != state_key:
        return RedirectResponse(f"https://i.imgur.com/vN5jG9r.mp4")
    await Auth.get_bearer_token(request=request, auth_code=code)
    return RedirectResponse(f"{CLIENT_URL}/pleaseclosethispopupformektxh", status_code=307)
