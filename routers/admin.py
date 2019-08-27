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
    if body.key != UPDATE_KEY:
        return unauthorized_response
    await Redis.send_to_bot("update", dict(type=body.type))
