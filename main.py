from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import sys # Para imprimir errores en los logs de Render

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
    return {"status": "API is live"}

@app.get("/api/stock")
def get_stock_data(ticker: str):
    ticker = ticker.upper().strip()
    print(f"Buscando datos para: {ticker}...", file=sys.stderr) # Log visible en Render

    try:
        stock = yf.Ticker(ticker)
        
        # INTENTO 1: Obtener historial (Lo más importante para el gráfico)
        try:
            hist = stock.history(period="1y")
            if hist.empty:
                print("Historial vacío. Ticker podría no existir.", file=sys.stderr)
                return {"error": "No historical data found"}
            
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            closes = hist['Close'].tolist()
            previous_close = hist['Close'].iloc[-2] if len(hist) > 1 else 0
        except Exception as e:
            print(f"Error bajando historial: {e}", file=sys.stderr)
            return {"error": "Error fetching history"}

        # INTENTO 2: Obtener Info (Métricas) con Fallback
        # A veces stock.info falla en la nube. Usamos fast_info como respaldo.
        info = {}
        try:
            info = stock.info
        except Exception as e:
            print(f"Advertencia: stock.info falló ({e}). Usando fast_info...", file=sys.stderr)
            # Si falla info, intentamos construir datos básicos con fast_info
            try:
                fast = stock.fast_info
                info = {
                    "symbol": ticker,
                    "shortName": ticker,
                    "currentPrice": fast.last_price,
                    "previousClose": previous_close,
                    "marketCap": fast.market_cap,
                    "trailingPE": None, # fast_info no tiene PE
                    "returnOnEquity": None,
                    "dividendYield": None
                }
            except:
                pass # Si todo falla, enviamos datos vacíos pero con gráfico

        # Construir respuesta final
        return {
            "symbol": info.get("symbol", ticker),
            "shortName": info.get("shortName", ticker),
            "currentPrice": info.get("currentPrice", 0),
            "previousClose": info.get("previousClose", previous_close),
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
        print(f"ERROR CRÍTICO: {e}", file=sys.stderr)
        return {"error": str(e)}
