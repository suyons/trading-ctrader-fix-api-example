# TradingView webhook + cTrader FIX API

## Building simple strategy

### Check the Pine script code [here](/01-tradingview-fixapi/indicators/)

I built some simple indicator that is derived from [RSI](https://en.wikipedia.org/wiki/Relative_strength_index).

There are 4 oscillators of each timeframe (default timeframe: 5, 15, 60, 240)

### Demonstration

The indicator makes BUY signal when `RSI_4 > 50` and `ta.crossover(RSI_1, val_low)`

I set the 1st condition to classify the trend, and 2nd conditon to spot the oversold point.

That's all, isn't it really simple?

### Demo

I plotted the horizontal line on `OANDA:EURUSD`

Each line means a limit order.

![EURUSD image](/01-tradingview-fixapi/docs/EURUSD_2024-05-22_12-58-35.png)
