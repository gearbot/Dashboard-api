from fastapi import FastAPI
from routers import crowdin, main

app = FastAPI()


app.include_router(main.router, prefix="/api", responses={404: {"description": "Not found"}})
app.include_router(crowdin.router, prefix="/api/crowdin-webhook", responses={404: {"description": "Not found"}})

import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info", reload=True)
