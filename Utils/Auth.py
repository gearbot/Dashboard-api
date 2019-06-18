import time

from starlette.requests import Request
from starlette.responses import JSONResponse

from Utils import Redis, Configuration
from Utils.Configuration import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, API_LOCATION


bad_auth_resp = JSONResponse({"status": "Unauthorized"}, status_code=401)

async def query_endpoint(request, method, endpoint, data=None):
    # Due to the weird way the SessionMiddleware handles bad session cookies, this exists
    # The libary will simply null all the values if it has either expired or failed to verify

    if request.session == {}: # This would indicate a error occured verifying the cookie
        return bad_auth_resp

    # After this point, we can guarantee `user_id` exists. If it didn't, the verifying would of failed
    session_pool = request.app.session_pool
    pool = Redis.get_redis()
    key = f"tokens:{request.session['user_id']}"
    expiry = await pool.hget(key, "expires_at")
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
        if "user_id" not in request.session:
            raise RuntimeError("No clue who you are mate")

        refresh_token = await pool.hget(f"tokens:{request.session['user_id']}", "refresh_token")
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
        expires_at = int(time.time() + token_return["expires_in"])

    # Fetch user info
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    async with session_pool.get(f"{API_LOCATION}/users/@me", headers=headers) as resp:
        user_info = await resp.json()
        user_id = user_info["id"]

    # Store refresh token in redis
    pipe = pool.pipeline()
    key = f"tokens:{user_id}"
    pipe.hmset_dict(key, dict(refresh_token=refresh_token, access_token=access_token, expires_at=expires_at))
    pipe.expire(key, Configuration.SESSION_TIMEOUT_LEN)
    await pipe.execute()

    request.session["user_id"] = user_id

    return access_token


# Currently, nothing ever hits this decorator, so it does nothing.
def auth_required(handler):
    async def wrapper(request, *args, **kwargs):
        if request.session == {}: # Either the cookie expired or was tampered with
            return bad_auth_resp
        return await handler(*args, **kwargs)
    wrapper.__name__ = handler.__name__
    return wrapper
