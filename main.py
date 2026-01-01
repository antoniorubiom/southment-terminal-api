from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import json

app = FastAPI()

# Configuración de seguridad (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Southment API is Live (Robust Mode)"}

@app.get("/api/stock")
def get_stock_data(ticker: str):
    ticker = ticker.upper().strip()
    
    try:
        # Volvemos a la inicialización estándar que funcionaba
        stock = yf.Ticker(ticker)
        
        # --- FASE 1: DATOS CRÍTICOS (Gráfico y Precio) ---
        # Si esto falla, la web no sirve, así que devolvemos error.
        
        hist = stock.history(period="1y")
        
        if hist.empty:
            return {"error": "Ticker not found or no data"}
            
        # Preparar datos del gráfico
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        closes = hist['Close'].tolist()
        
        # Obtener precio actual del historial (es lo más fiable)
        current_price = closes[-1] if closes else 0
        previous_close = closes[-2] if len(closes) > 1 else current_price
        
        # --- FASE 2: MÉTRICAS (Opcionales) ---
        # Aquí es donde Yahoo suele bloquear. Usaremos bloques try/except
        # para que si falla una métrica, NO rompa el gráfico.
        
        market_cap = 0
        pe_ratio = None
        roe = None
        div_yield = None
        short_name = ticker
        
        # Intento A: Usar fast_info (Más robusto en la nube)
        try:
            fast = stock.fast_info
            # fast_info no suele bloquearse
            if fast.market_cap: market_cap = fast.market_cap
            # A veces fast_info tiene el precio más actualizado
            if fast.last_price: current_price = fast.last_price
        except:
            pass # Si falla, seguimos con los datos del historial

        # Intento B: Usar info completa (Propenso a bloqueos)
        # Envolvemos esto en un try "silencioso"
        try:
            info = stock.info
            # Si logramos entrar, llenamos lo que falta
            short_name = info.get("shortName", ticker)
            pe_ratio = info.get("trailingPE") or info.get("forwardPE")
            roe = info.get("returnOnEquity")
            div_yield = info.get("dividendYield")
            
            # Si fast_info falló en market_cap, probamos aquí
            if market_cap == 0:
                market_cap = info.get("marketCap", 0)
        except:
            # Si Yahoo bloquea 'info', no pasa nada. 
            # El usuario verá el gráfico y el precio, pero las métricas dirán "---"
            print(f"Advertencia: No se pudieron cargar métricas extra para {ticker}")

        # --- FASE 3: RESPUESTA FINAL ---
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
            }
        }

    except Exception as e:
        print(f"Critical Error: {e}")
        return {"error": str(e)}
