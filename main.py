from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Southment API v3.0 (Accumulated Return)"}

@app.get("/api/stock")
def get_stock_data(ticker: str, period: str = "1y"):
    ticker = ticker.upper().strip()
    
    valid_periods = {
        "1d": "1d", "5d": "5d", "1m": "1mo", "6m": "6mo", 
        "ytd": "ytd", "1y": "1y", "5y": "5y", "10y": "10y", "max": "max"
    }
    
    y_period = valid_periods.get(period, "1y")
    
    interval = "1d"
    if y_period == "1d": interval = "5m"
    elif y_period == "5d": interval = "15m"
    elif y_period in ["5y", "10y", "max"]: interval = "1wk"

    try:
        stock = yf.Ticker(ticker)
        
        # 1. HISTORIAL
        hist = stock.history(period=y_period, interval=interval)
        
        if hist.empty:
            return {"error": "No data found"}
            
        dates = hist.index.strftime('%Y-%m-%d %H:%M').tolist()
        closes = hist['Close'].tolist()
        
        current_price = closes[-1] if closes else 0
        
        # 2. RENDIMIENTO ACUMULADO
        
        previous_close = 0
        
        if y_period == "1d":
            previous_close = stock.fast_info.previous_close
        else:
            previous_close = closes[0] if len(closes) > 0 else current_price

        # 3. DATOS DE LA EMPRESA
        market_cap = 0
        pe_ratio = None
        roe = None
        div_yield = None
        short_name = ticker
        
        try:
            info = stock.info
            short_name = info.get("longName") or info.get("shortName") or ticker
            
            market_cap = info.get("marketCap", 0)
            pe_ratio = info.get("trailingPE") or info.get("forwardPE")
            roe = info.get("returnOnEquity")
            div_yield = info.get("dividendYield")
        except:
            try:
                if stock.fast_info.market_cap: market_cap = stock.fast_info.market_cap
            except: pass

        return {
            "symbol": ticker,
            "shortName": short_name,
            "currentPrice": current_price,
            "previousClose": previous_close,
            "marketCap": market_cap,
            "trailingPE": pe_ratio,
            "returnOnEquity": roe,
            "dividendYield": div_yield,
            "chartHistory": {
                "Date": dates,
                "Close": closes
            },
            "period": period
        }

    except Exception as e:
        return {"error": str(e)}
