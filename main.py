from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import os

app = FastAPI()

# Configuración de seguridad (CORS) para que tu web pueda leer los datos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite acceso desde cualquier web
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Southment API is running"}

@app.get("/api/stock")
def get_stock_data(ticker: str):
    try:
        # Limpiamos el ticker
        ticker = ticker.upper().strip()
        stock = yf.Ticker(ticker)
        
        # Forzamos la descarga de info
        info = stock.info
        
        # Obtenemos historial (1 año) para el gráfico
        hist = stock.history(period="1y")
        
        if hist.empty:
             return {"error": "No data found"}

        # Preparamos datos para el gráfico
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        closes = hist['Close'].tolist()

        return {
            "symbol": info.get("symbol", ticker),
            "shortName": info.get("shortName", ticker),
            "currentPrice": info.get("currentPrice", 0),
            "previousClose": info.get("previousClose", 0),
            "marketCap": info.get("marketCap", 0),
            "trailingPE": info.get("trailingPE", None),
            "returnOnEquity": info.get("returnOnEquity", None),
            "dividendYield": info.get("dividendYield", None),
            "chartHistory": {
                "Date": dates,
                "Close": closes
            }
        }
    except Exception as e:
        return {"error": str(e)}
