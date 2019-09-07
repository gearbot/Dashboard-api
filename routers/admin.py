from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request

from Utils import Redis
from Utils.Configuration import UPDATE_KEY
from Utils.Responses import unauthorized_response

router = APIRouter()


class Body(BaseModel):
    key: str
    type: str


@router.post("/update")
async def update(request: Request, body: Body):
    # Disable endpoint by default. Re-enable by generating a update key in the config
    if UPDATE_KEY == None or body.key != UPDATE_KEY:
        return unauthorized_response
    await Redis.send_to_bot("update", type=body.type)
