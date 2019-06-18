from fastapi import APIRouter
from starlette.responses import RedirectResponse
from starlette.requests import Request
from Utils.Configuration import CLIENT_ID, REDIRECT_URI, CLIENT_URL

router = APIRouter()

from Utils import Auth
from Utils.Configuration import API_LOCATION

# Code Generation
@router.get("/login")
async def discord_oauth_redir():
    return RedirectResponse(
        f"{API_LOCATION}/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify guilds",
        status_code=307
    )

# Callback handling
@router.get("/callback")
async def handle_callback(code: str, request: Request):
    await Auth.get_bearer_token(request=request, auth_code=code)
    return RedirectResponse(f"{CLIENT_URL}/pleaseclosethispopupformektxh", status_code=307)
