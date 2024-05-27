import json, requests
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from ctrader_fix.ctrader import Ctrader
import asyncio


app = FastAPI()


with open("config.json") as config_file:
    config = json.load(config_file)
    HOST_NAME = config["Host"]
    SENDER_COMPID = config["SenderCompID"]
    PASSWORD = config["Password"]
    TELEGRAM_BOT_TOKEN = config["TelegramBotToken"]
    TELEGRAM_CHAT_ID = config["TelegramChatID"]
global api
api = Ctrader(HOST_NAME, SENDER_COMPID, PASSWORD)

qty_mult: int = 2


class LoginModel(BaseModel):
    server: str
    account: str
    password: str


class SymbolModel(BaseModel):
    symbols: list[str]


class OrderModel(BaseModel):
    symbol: str
    volume: float
    stoploss: float = None
    takeprofit: float = None
    price: float = None


class ModifyModel(BaseModel):
    id: str
    stoploss: float
    takeprofit: float
    price: float = None


class IdModel(BaseModel):
    id: str


async def check():
    return api.isconnected()


async def telegram_request(tg_body: dict):
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json=tg_body,
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=500, detail="Telegram connection error.")


@app.post("/login")
async def login():
    api = Ctrader(HOST_NAME, SENDER_COMPID, PASSWORD)
    return {"connected": api.isconnected()}


@app.get("/quote/{symbol}")
async def quote(symbol: str = None):
    if symbol:
        quote = api.quote(symbol)
    else:
        quote = api.quote()
    return quote


@app.post("/buy")
async def buy(order: OrderModel):
    for i in range(qty_mult):
        api.buy(order.symbol, order.volume, order.stoploss, order.takeprofit)
        tg_body = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"📈 BUY {order.symbol} ({order.volume})",
        }
        await telegram_request(tg_body)
        await asyncio.sleep(1)


@app.post("/sell")
async def sell(order: OrderModel):
    for i in range(qty_mult):
        api.sell(order.symbol, order.volume, order.stoploss, order.takeprofit)
        tg_body = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"📉 SELL {order.symbol} ({order.volume})",
        }
        await telegram_request(tg_body)
        await asyncio.sleep(1)


@app.post("/buyLimit")
async def buy_limit(order: OrderModel):
    return {"Order": api.buyLimit(order.symbol, order.volume, order.price)}


@app.post("/sellLimit")
async def sell_limit(order: OrderModel):
    return {"Order": api.sellLimit(order.symbol, order.volume, order.price)}


@app.post("/buyStop")
async def buy_stop(order: OrderModel):
    return {"Order": api.buyStop(order.symbol, order.volume, order.price)}


@app.post("/sellStop")
async def sell_stop(order: OrderModel):
    return {"Order": api.sellStop(order.symbol, order.volume, order.price)}


@app.get("/positions")
async def positions():
    return api.positions()


@app.get("/orders")
async def orders():
    return api.orders()


@app.post("/orderCancelById")
async def order_cancel_by_id(id_model: IdModel):
    api.orderCancelById(id_model.id)
    return {"message": "Order cancelled"}


@app.post("/positionCloseById")
async def position_close_by_id(id_model: IdModel):
    api.positionCloseById(id_model.id)
    return {"message": "Position closed"}


@app.post("/cancel_all")
async def cancel_all():
    api.cancel_all()
    return {"message": "All orders cancelled"}


@app.post("/close_all")
async def close_all():
    api.close_all()
    return {"message": "All positions closed"}


@app.post("/logout")
async def logout():
    return {"message": api.logout()}


@app.post("/status")
async def status():
    return {"connected": api.isconnected()}


@app.post("/subscribe")
async def subscribe(subscription: SymbolModel):
    for symbol in subscription.symbols:
        api.subscribe(symbol)
    return {"message": "Subscribed to symbols"}
