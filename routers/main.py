from fastapi import APIRouter
from starlette.responses import RedirectResponse

router = APIRouter()


@router.get("/")
async def read_root():
    return {"status": "WIP"}

@router.get("/redirect")
async def test():
    return RedirectResponse(f"https://discordapp.com/api/oauth2/authorize?client_id=365497403928870914&response_type=code&scope=identify guilds&redirect_uri=http://localhost:8000/api/discord/callback/", status_code=307)