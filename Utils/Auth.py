import time

from starlette.requests import Request

from Utils import Redis, Configuration
from Utils.Configuration import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, API_LOCATION


async def query_endpoint(request, method, endpoint, data=None):
    if "uid" not in request.session:
        raise RuntimeError("No clue who this is")
    session_pool = request.app.session_pool
    pool = Redis.get_redis()
    key = f"tokens:{request.session['uid']}"
    expiry = await pool.hget(key, 'expires_in')
    if time.time() + 3 * 24 * 60 * 60  >= int(expiry):
        token = await get_bearer_token(request=request, refresh=True)
    else:
        token = await pool.hget(key, 'access_token')
    headers = dict(Authorization= f"Bearer {token}")
    async with getattr(session_pool, method)(f"{API_LOCATION}/{endpoint}", data=data, headers=headers) as response:
        return await response.json()


async def get_bearer_token(request: Request, refresh: bool = False, auth_code: str = ""):
    session_pool = request.app.session_pool
    pool = Redis.get_redis()

    body = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify guilds"
    }

    if refresh:
        # do we know who this is supposed to be?
        if "uid" not in request.session:
            raise RuntimeError("No clue who you are mate")

        refresh_token = await pool.get(f"refresh:{request.session['uid']}")
        if refresh_token is None or refresh_token is 0:
            raise RuntimeError("No refresh token available for this user!")
        body["grant_type"] = "refresh_token"
        body["refresh_token"] = refresh_token

    else:
        body["grant_type"] = "authorization_code"

    print("Fetching token...")

    async with session_pool.post(f"{API_LOCATION}/oauth2/token", data=body) as token_resp:
        token_return = await token_resp.json()

        access_token = token_return["access_token"]
        refresh_token = token_return["refresh_token"]
        expires_in = time.time() + token_return["expires_in"]

    # fetch user info
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    async with session_pool.get(f"{API_LOCATION}/users/@me", headers=headers) as resp:
        user_info = await resp.json()
        user_id = user_info["id"]

    # store refresh token in redis

    pipe = pool.pipeline()
    key = f"tokens:{user_id}"
    pipe.hmset_dict(key, dict(refresh_token=refresh_token, access_token=access_token, expires_in=expires_in))
    pipe.expire(key, Configuration.SESSION_TIMEOUT_LEN)
    await pipe.execute()

    request.session["uid"] = user_id

    return access_token
