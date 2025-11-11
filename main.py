import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")

from routes.index import router as index_router
from routes.listener_routes import router as speech_to_text_router

app = FastAPI()

# Include routes
app.include_router(index_router)
app.include_router(speech_to_text_router, prefix="/listener")

if __name__ == "__main__":
    load_dotenv()

    HOST: str = os.getenv("HOST", "")
    PORT: int = int(os.getenv("PORT", ""))
    HOT_RELOADING: bool = os.getenv("HOT_RELOADING", "False").lower() in ("true", "1", "t")

    if HOT_RELOADING:
        uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
    else:
        uvicorn.run(app=app, host=HOST, port=PORT)
