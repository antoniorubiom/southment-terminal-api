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
    
    # Mapeo de periodos
    valid_periods = {
        "1d": "1d", "5d": "5d", "1m": "1mo", "6m": "6mo", 
        "ytd": "ytd", "1y": "1y", "5y": "5y", "10y": "10y", "max": "max"
    }
    
    y_period = valid_periods.get(period, "1y")
    
    # Intervalo para que el gráfico se vea bonito
    interval = "1d"
    if y_period == "1d": interval = "5m"
    elif y_period == "5d": interval = "15m"
    elif y_period in ["5y", "10y", "max"]: interval = "1wk"

    try:
        stock = yf.Ticker(ticker)
        
        # 1. OBTENER HISTORIAL
        hist = stock.history(period=y_period, interval=interval)
        
        if hist.empty:
            return {"error": "No data found"}
            
        dates = hist.index.strftime('%Y-%m-%d %H:%M').tolist()
        closes = hist['Close'].tolist()
        
        # Precio actual (último disponible)
        current_price = closes[-1] if closes else 0
        
        # 2. CÁLCULO DEL RENDIMIENTO ACUMULADO (Ajuste solicitado)
        # Si es '1d', comparamos con el cierre de ayer (variación diaria).
        # Si es '1m', '1y', etc., comparamos con el PRIMER dato del gráfico (acumulado).
        
        previous_close = 0
        
        if y_period == "1d":
            # Para 1 día, usamos el cierre previo oficial de Yahoo
            previous_close = stock.fast_info.previous_close
        else:
            # Para periodos largos, usamos el precio al inicio del periodo
            # Así el % reflejará "Cuánto ha crecido en este año"
            previous_close = closes[0] if len(closes) > 0 else current_price

        # 3. OBTENER DATOS DE LA EMPRESA (Nombre completo)
        market_cap = 0
        pe_ratio = None
        roe = None
        div_yield = None
        short_name = ticker # Por defecto el ticker si falla todo
        
        # Intento blindado de obtener el nombre largo
        try:
            info = stock.info
            # Priorizamos 'longName', luego 'shortName', luego el ticker
            short_name = info.get("longName") or info.get("shortName") or ticker
            
            # Métricas
            market_cap = info.get("marketCap", 0)
            pe_ratio = info.get("trailingPE") or info.get("forwardPE")
            roe = info.get("returnOnEquity")
            div_yield = info.get("dividendYield")
        except:
            # Si Yahoo bloquea info, intentamos fast_info para lo básico
            try:
                if stock.fast_info.market_cap: market_cap = stock.fast_info.market_cap
            except: pass

        return {
            "symbol": ticker,
            "shortName": short_name, # Aquí irá "Apple Inc." en vez de AAPL
            "currentPrice": current_price,
            "previousClose": previous_close, # Este valor cambia según el periodo seleccionado
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
