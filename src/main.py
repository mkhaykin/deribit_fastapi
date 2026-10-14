from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def hello() -> dict:
    return {"msg": "Hello World"}
