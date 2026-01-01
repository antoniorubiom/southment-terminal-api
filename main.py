from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import requests

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
    return {"status": "Southment API is Live"}

@app.get("/api/stock")
def get_stock_data(ticker: str):
    ticker = ticker.upper().strip()
    
    try:
        # 1. TRUCO DE IDENTIDAD: Creamos una sesión que finge ser un navegador Chrome
        # Esto evita que Yahoo bloquee la descarga de las métricas (P/E, ROE, etc)
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # Inicializamos el Ticker con esa sesión
        stock = yf.Ticker(ticker, session=session)
        
        # 2. OBTENER GRÁFICO (Esto ya te funcionaba, lo dejamos igual)
        hist = stock.history(period="1y")
        if hist.empty:
            return {"error": "No historical data found"}
        
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        closes = hist['Close'].tolist()
        current_price = closes[-1] if closes else 0
        previous_close = closes[-2] if len(closes) > 1 else current_price

        # 3. OBTENER MÉTRICAS (Aquí estaba el fallo)
        # Usamos estrategias mixtas para asegurar datos
        
        info = {}
        try:
            info = stock.info
        except:
            info = {} # Si falla, seguimos con dicc vacío
            
        # Estrategia blindada para Market Cap (fast_info es más fiable que info)
        market_cap = 0
        try:
            market_cap = stock.fast_info.market_cap
        except:
            market_cap = info.get("marketCap", 0)

        # Extracción segura de métricas con valores por defecto
        # Nota: SPY y ETFs a veces no tienen P/E o ROE, es normal que salga None.
        pe_ratio = info.get("trailingPE") or info.get("forwardPE")
        roe = info.get("returnOnEquity")
        div_yield = info.get("dividendYield") or info.get("trailingAnnualDividendYield")

        # 4. PREPARAR RESPUESTA
        return {
            "symbol": info.get("symbol", ticker),
            "shortName": info.get("shortName", ticker),
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
        print(f"Server Error: {e}")
        return {"error": str(e)}
