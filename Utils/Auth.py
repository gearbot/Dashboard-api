from datetime import datetime, timedelta
import base64

import jwt
from jwt import exceptions, PyJWTError

from starlette.requests import Request

from result import Ok, Err

from api import API_LOCATION, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SESSION_TIMEOUT_LEN
from api import HMAC_KEY

from Utils import Redis

ALGORITHM = "HS256"

# This will return a Base64 encoded version of the token by default
def generate_access_token(data: dict, request: Request, expire_delta: timedelta = None):
    to_encode = data.copy()
    if expire_delta:
        expire_dt = datetime.utcnow() + expire_delta
    else:
        expire_dt = datetime.utcnow() + timedelta(days = SESSION_TIMEOUT_LEN)

    to_encode.update({"exp": expire_dt})

    print(HMAC_KEY)
    jwt_token = jwt.encode(to_encode, request.app.HMAC_KEY, algorithm=ALGORITHM)
    return base64.urlsafe_b64encode(jwt_token)

async def verify_user(user_token: str):
    try:
        valid_token = jwt.decode(user_token, algorithms=ALGORITHM, verify=True)

        user_id = valid_token.get("id")
        token = valid_token.get("token")
    except PyJWTError as ex:
        if ex == exceptions.ExpiredSignature:
            return Err("The token expired")
        else:
            return Err("The token was tampered with!")

    user = {
        "id": user_id,
        "token": token
    }

    return Ok(user)


async def get_bearer_token(auth_code: str, refresh: bool, user_id: int, request):
    session_pool = request.app.session_pool
    
    # TODO: Proper token refresh support
    if refresh:
        # UserID can *only* be accessed inside this block
        #redis = Redis.get_redis(1)
        #refresh_token = await redis.get(f"drefreshtoken:{user_id}")
        # Some logic here....
        pass

    print("Fetching bearer token...")

    token_fetch_body = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token" if refresh else "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify guilds"
    }

    async with session_pool.post(f"{API_LOCATION}/oauth2/token",
        data = token_fetch_body) as token_resp:

        token_return = await token_resp.json()

        access_token = token_return["access_token"]
        refresh_token = token_return["refresh_token"]

        return (access_token, refresh_token)
