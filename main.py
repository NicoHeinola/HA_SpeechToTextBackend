import os
from dotenv import load_dotenv
from fastapi import FastAPI, Body
import uvicorn

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Speech to Text API is running."}


if __name__ == "__main__":
    load_dotenv()

    HOST: str = os.getenv("HOST", "")
    PORT: int = int(os.getenv("PORT", ""))

    uvicorn.run(app, host=HOST, port=PORT)
