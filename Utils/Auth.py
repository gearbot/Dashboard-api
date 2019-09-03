import secrets
import time
from datetime import datetime

from starlette.requests import Request
from starlette.responses import JSONResponse

from aiohttp import client
from tortoise.exceptions import DoesNotExist

from Utils.Configuration import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, API_LOCATION, ALLOWED_USERS
from Utils.DataModels import Dashsession
from Utils.Responses import unauthorized_response

# kill all active sessions by the specified user, used when we detect something fishy is going on
from routers.websocket import socket_by_user


async def deauth_user(user_id):
    await Dashsession.filter(user_id=user_id).delete()
    if user_id in socket_by_user:
        # copy to protect against concurrent modifications, as well as preventing sending user data as we can delete
        todo = socket_by_user[user_id].copy()
        del socket_by_user[user_id]
        # make sure the client knows they are no longer who they think they are
        for websocket in todo:
            websocket.auth_info = None
            await websocket.send_json({
                "type": "hello",
                "content": {"authorized": False}
            })

# Currently, nothing ever hits this decorator, so it does nothing.
def auth_required(handler):
    async def wrapper(request: Request):
        async def h(): return await handler(request)

        return await handle_it(request, h)

    wrapper.__name__ = handler.__name__
    return wrapper


def if_authorized(handler):
    async def wrapper(request: Request):
        return await handle_it(request, handler)

    wrapper.__name__ = handler.__name__
    return wrapper


async def handle_it(request, handler):
    if any(k not in request.session for k in [
        "user_id",
        "refresh_token",
        "access_token",
        "expires_at"
    ]): return unauthorized_response  # Either the cookie expired or was tampered with

    response = await handler()
    if not isinstance(response, JSONResponse):
        response = JSONResponse(response)
    return response


async def get_token_info(token):
    # validate token, close socket if it's a bad token
    try:
        info = await Dashsession.get(id=token).prefetch_related("user")
    except DoesNotExist:
        return None  # invalid token pretend it's not there
    else:
        # is the session still valid?
        return info if await check_session(info) else None


async def check_session(info):
    if info.expires_at > datetime.now():
        # dashboard token is still valid, reset the timer
        info.expires_at = datetime.utcfromtimestamp(time.time() + 60 * 60 * 24 * 7)

        # is the discord token still valid?
        if info.user.expires_at > datetime.now():
            session_pool = client.ClientSession()
            # should we refresh it?
            if info.user.expires_at < datetime.utcfromtimestamp(time.time() + 60 * 60 * 24 * 3):

                body = {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": info.user.refresh_token,
                    "redirect_uri": REDIRECT_URI,
                    "scope": "identify guilds"
                }
                async with session_pool.post(f"{API_LOCATION}/oauth2/token", data=body) as token_resp:
                    token_return = await token_resp.json()
                    if "access_token" in token_return:
                        info.user.api_token = token_return["access_token"]
                        info.user.refresh_token = token_return["refresh_token"]
                        info.user.expires_at = datetime.utcfromtimestamp(int(time.time() + token_return["expires_in"]))
                        await info.user.save(update_fields=["api_token", "refresh_token", "expires_at"])
                    else:
                        # unable to refresh, terminate
                        await deauth_user(info.user.id)
                        await info.delete()
                        return False

            headers = {
                "Authorization": f"Bearer {info.user.api_token}"
            }

            async with session_pool.get(f"{API_LOCATION}/users/@me", headers=headers) as resp:
                user_info = await resp.json()
                if "id" not in user_info or int(user_info["id"]) not in ALLOWED_USERS:
                    await deauth_user(info.user.id)
                    await info.delete()
                    return False

            await session_pool.close()
        else:
            # nope, kill it
            await deauth_user(info.user.id)
            await info.delete()
            return False

        await info.save(update_fields=["expires_at"])
        return True
    else:
        await info.delete()
        return False
