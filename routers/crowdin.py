from pydantic import BaseModel

from Utils import Redis
from fastapi import APIRouter

router = APIRouter()


class Exported(BaseModel):
    event: str
    project: str
    project_id: int
    language: str
    source_string_id: str
    old_translation_id: str = None
    new_translation_id: str = None
    user: str = None
    user_id: str = None
    file_id: str
    file: str


@router.post("/", include_in_schema=False)
async def crowdin_webhook(info: Exported):
    if info.file != "/bot/commands.json": return
    print(f"Crowdin event recieved: {info.event} for file {info.file} in {info.language}")
    link = await Redis.get_redis()
    await link.publish_json("dash-bot-messages", dict(type="crowdin_webhook",
                                                      info=dict(event=info.event, project=info.project,
                                                                project_id=info.project_id,
                                                                language=info.language,
                                                                source_string_id=info.source_string_id,
                                                                old_translation_id=info.old_translation_id,
                                                                new_translation_id=info.new_translation_id,
                                                                user=info.user, user_id=info.user_id,
                                                                file_id=info.file_id, file=info.file)))
