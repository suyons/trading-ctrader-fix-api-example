from fastapi import FastAPI, HTTPException
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
    """TradingView Webhook body example:
     {
        "symbol": "EURUSD",
        "side": "Buy",
        "price": "1.23456"
    }
    """
    tg_body = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "Trade signal received!\n\n"
        + f"Symbol: {tv_body['symbol']}\n"
        + f"Side: {tv_body['side']}\n"
        + f"Price: {tv_body['price']}",
    }
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=tg_body
    )

    if response.status_code == 200:
        return {"message": "Trade signal received and sent to Telegram."}
    else:
        raise HTTPException(
            status_code=500, detail="Failed to send trade signal to Telegram."
        )
