from fastapi import APIRouter, Cookie
from starlette.responses import JSONResponse
from starlette.requests import Request


router = APIRouter()

from Utils import Auth, Redis

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

@router.get("/whoami")
async def identify_endpoint(request: Request):
    if "uid" not in request.session:
        return JSONResponse(dict(status="Unauthorized"), status_code=401)
    print("Sending info request to Gearbot...")
    user_info = await Auth.query_endpoint(request, "get", "users/@me")
    info = await Redis.ask_the_bot("user_info", user_id=request.session["uid"])
    return info
