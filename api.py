import aioredis as aioredis
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


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


redis_link = None


async def get_redis():
    global redis_link
    if redis_link is None:
        redis_link = await aioredis.create_redis_pool(("192.168.0.128", 6379), encoding="utf-8", db=0,
                                                      maxsize=2)  # size 2: one send, one receive
    return redis_link


@app.get("/api/")
async def read_root():
    return {"status": "WIP"}


@app.post("/api/crowdin-webhook/", include_in_schema=False)
async def crowdin_webhook(info: Exported):
    if info.file != "/bot/commands.json": return
    print(f"Crowdin event recieved: {info.event} for file {info.file} in {info.language}")
    link = await get_redis()
    await link.publish_json("dash-bot-messages", dict(type="crowdin_webhook", info=dict(event=info.event, project=info.project, project_id=info.project_id,
                                                                                        language=info.language, source_string_id=info.source_string_id,
                                                                                        old_translation_id=info.old_translation_id, new_translation_id=info.new_translation_id,
                                                                                        user=info.user, user_id=info.user_id, file_id=info.file_id, file=info.file)))




import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info", reload=True)
