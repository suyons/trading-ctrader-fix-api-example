from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def hello_ctrader():
    return {"message": "Hello cTrader!"}
