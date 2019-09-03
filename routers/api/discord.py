import secrets
import time
from datetime import datetime

from aiohttp import client
from fastapi import APIRouter, Cookie
from starlette.responses import RedirectResponse
from starlette.requests import Request
from tortoise.exceptions import DoesNotExist

from Utils.Auth import deauth_user
from Utils.Configuration import CLIENT_ID, REDIRECT_URI, CLIENT_URL, API_LOCATION, CLIENT_SECRET
from Utils import Auth
from secrets import token_urlsafe

from Utils.DataModels import Dashsession, UserInfo
from Utils.Prometheus import notice_session
from Utils.Responses import bad_oauth_response

router = APIRouter()


# Code Generation
@router.get("/login")
async def discord_oauth_redir():
    state_key = token_urlsafe(20)
    response = RedirectResponse(
        f"{API_LOCATION}/oauth2/authorize?client_id={CLIENT_ID}&state={state_key}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify guilds&prompt=none",
        status_code=307
    )
    # We won't need this cookie 5 minutes later
    response.set_cookie(key="state_key", value=state_key, expires=300)
    return response


# Callback handling
@router.get("/callback")
async def handle_callback(error: str = None, code: str = None, state: str = None, request: Request = None,
                          state_key: str = Cookie(None)):
    if error is not None:  # They must of denied the auth request if this errors
        return RedirectResponse(f"{CLIENT_URL}")

    if state != state_key or code is None:
        return bad_oauth_response

    # we got a code, grab auth token
    session_pool = client.ClientSession()

    body = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify guilds",
        "grant_type": "authorization_code"
    }

    async with session_pool.post(f"{API_LOCATION}/oauth2/token", data=body) as token_resp:
        token_return = await token_resp.json()
        print(token_return)
        access_token = token_return["access_token"]
        refresh_token = token_return["refresh_token"]
        expires_at = datetime.utcfromtimestamp(int(time.time() + token_return["expires_in"]))

    # Fetch user info
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    async with session_pool.get(f"{API_LOCATION}/users/@me", headers=headers) as resp:
        user_info = await resp.json()
        print(user_info)
        user_id = int(user_info["id"])

    await session_pool.close()
    token = secrets.token_urlsafe()

    # we got the tokens and they are valid, check if we already had tokens for this user
    try:
        info = await UserInfo.get(id=user_id)
    except DoesNotExist:
        # we didn't have info for this user yet
        info = await UserInfo.create(id=user_id, api_token=access_token, refresh_token=refresh_token,
                                     expires_at=expires_at)
        session = Dashsession(id=token, expires_at=datetime.utcfromtimestamp(time.time() + 60 * 60 * 24 * 7),
                              user=info)
        await session.save()

    else:
        # we already have a token, is it the same?
        if info.api_token != access_token:
            # different token, nuke all sessions as we probably are re-authorizing after a de-auth
            await deauth_user(user_id)
            info.api_token = access_token
            info.refresh_token = refresh_token
            info.expires_at = expires_at
            await info.save(update_fields=["api_token", "refresh_token", "expires_at"])  # if we don't explicty do this it'll try to do all of them, including the PK and get a key violation
            session = Dashsession(id=token, expires_at=datetime.utcfromtimestamp(time.time() + 60 * 60 * 24 * 7),
                                  user=info)
        else:
            session = Dashsession(id=token, expires_at=datetime.utcfromtimestamp(time.time() + 60 * 60 * 24 * 7),
                                  user=info)
        await session.save()

    response = RedirectResponse(CLIENT_URL, status_code=307)
    response.set_cookie("token", token, max_age=60*60*24*7)
    return response
