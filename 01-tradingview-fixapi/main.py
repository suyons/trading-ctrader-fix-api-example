from fastapi import FastAPI
import requests
import json

app = FastAPI()

with open("config.json") as config_file:
    config = json.load(config_file)
    TELEGRAM_BOT_TOKEN = config["TelegramBotToken"]
    TELEGRAM_CHAT_ID = config["TelegramChatID"]


@app.get("/")
async def hello_ctrader():
    return {"message": "Hello cTrader!"}


@app.post("/")
async def trade_signal(tv_body: dict):
    tg_body = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "Trade signal received!\n\n"
        + f"Symbol: {tv_body['symbol']}\n"
        + f"Action: {tv_body['action']}\n"
        + f"Price: {tv_body['price']}",
    }
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=tg_body
    )

    if response.status_code == 200:
        return {"message": "Trade signal received and sent to Telegram!"}, 200
    else:
        return {"message": "Failed to send trade signal to Telegram!"}, 500
