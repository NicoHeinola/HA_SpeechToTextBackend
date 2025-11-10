import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
from routes.index import router as index_router
from routes.speech_to_text_routes import router as speech_to_text_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")

app = FastAPI()

# Include routes
app.include_router(index_router)
app.include_router(speech_to_text_router, prefix="/listener")

if __name__ == "__main__":
    load_dotenv()

    HOST: str = os.getenv("HOST", "")
    PORT: int = int(os.getenv("PORT", ""))

    uvicorn.run(app, host=HOST, port=PORT)
