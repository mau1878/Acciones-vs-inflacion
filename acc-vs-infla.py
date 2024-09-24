import yfinance as yf
from datetime import datetime, date
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import investpy  # Importing InvestPy for fetching data from Investing.com

# Your existing inflation rates and splits dictionaries here...

# Inflación mensual estimada (datos corregidos)
inflation_rates = {
    2017: [1.6, 2.5, 2.4, 2.6, 1.3, 1.2, 1.7, 1.4, 1.9, 1.5, 1.4, 3.1],
    2018: [1.8, 2.4, 2.3, 2.7, 2.1, 3.7, 3.1, 3.9, 6.5, 5.4, 3.2, 2.6],
    2019: [2.9, 3.8, 4.7, 3.4, 3.1, 2.7, 2.2, 4.0, 5.9, 3.3, 4.3, 3.7],
    2020: [2.3, 2.0, 3.3, 1.5, 1.5, 2.2, 1.9, 2.7, 2.8, 3.8, 3.2, 4.0],
    2021: [4.0, 3.6, 4.8, 4.1, 3.3, 3.2, 3.0, 2.5, 3.5, 3.5, 2.5, 3.8],
    2022: [3.9, 4.7, 6.7, 6.0, 5.1, 5.3, 7.4, 7.0, 6.2, 6.3, 4.9, 5.1],
    2023: [6.0, 6.6, 7.7, 8.4, 7.8, 6.0, 6.3, 12.4, 12.7, 8.3, 12.8, 25.5],
    2024: [20.6, 13.2, 11.0, 9.2, 4.2, 4.6, 4.2, 3.5, 3.5, 3.3, 3.6, 3.3]  # Estimación ficticia
}

# Diccionario de tickers y sus divisores
splits = {
    'MMM.BA': 2,
    'ADGO.BA': 1,
    'ADBE.BA': 2,
    'AEM.BA': 2,
    'AMGN.BA': 3,
    'AAPL.BA': 2,
    'BAC.BA': 2,
    'GOLD.BA': 2,
    'BIOX.BA': 2,
    'CVX.BA': 2,
    'LLY.BA': 7,
    'XOM.BA': 2,
    'FSLR.BA': 6,
    'IBM.BA': 3,
    'JD.BA': 2,
    'JPM.BA': 3,
    'MELI.BA': 2,
    'NFLX.BA': 3,
    'PEP.BA': 3,
    'PFE.BA': 2,
    'PG.BA': 3,
    'RIO.BA': 2,
    'SONY.BA': 2,
    'SBUX.BA': 3,
    'TXR.BA': 2,
    'BA.BA': 4,
    'TM.BA': 3,
    'VZ.BA': 2,
    'VIST.BA': 3,
    'WMT.BA': 3,
    'AGRO.BA': (6, 2.1)  # Ajustes para AGRO.BA
}
# Function to fetch stock data, including a fallback to Investing.com
def fetch_stock_data(ticker, start_date, end_date):
    try:
        # Try to download data from Yahoo Finance
        stock_data = yf.download(ticker, start=start_date, end=end_date)
        if stock_data.empty:
            raise ValueError("No data found in Yahoo Finance.")
    except Exception as e:
        st.write(f"Error fetching data for {ticker} from Yahoo Finance: {e}")
        # If there's an error, try fetching data from Investing.com
        if ticker == 'VIST.BA':
            st.write(f"Attempting to fetch data for {ticker} from Investing.com...")
            stock_data = investpy.get_stock_historical_data(stock='vistm', 
                                                             country='Argentina', 
                                                             from_date=start_date.strftime('%d/%m/%Y'), 
                                                             to_date=end_date.strftime('%d/%m/%Y'))
        else:
            stock_data = pd.DataFrame()  # Fallback to an empty DataFrame if it's not VIST.BA

    return stock_data

# The rest of your functions (ajustar_precios_por_splits, calcular_inflacion_diaria_rango, generar_grafico) remain the same...

# Streamlit UI code
st.title("Análisis de Ticker y Comparación con Inflación")

ticker = st.text_input("Ingrese el ticker (por defecto GGAL.BA):", "GGAL.BA").upper()

analysis_type = st.radio(
    "Seleccione el tipo de análisis:",
    ('Por año (predeterminado)', 'Por rango de fechas')
)

if analysis_type == 'Por año (predeterminado)':
    for year in range(2017, 2025):
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)

        stock_data = fetch_stock_data(ticker, start_date, end_date)

        if not stock_data.empty:
            stock_data.reset_index(inplace=True)
            stock_data = ajustar_precios_por_splits(stock_data, ticker)  # Adjust prices for splits
            cumulative_inflation = calcular_inflacion_diaria_rango(stock_data, start_date.year, start_date.month, end_date.year, end_date.month)
            generar_grafico(ticker, stock_data, cumulative_inflation, year)
        else:
            st.write(f"No se encontraron datos para {ticker} en el año {year}.")

else:
    start_date = st.date_input("Fecha de inicio", date(2020, 1, 1))
    end_date = st.date_input("Fecha de fin", date(2024, 12, 31))
    
    if start_date < end_date:
        stock_data = fetch_stock_data(ticker, start_date, end_date)

        if not stock_data.empty:
            stock_data.reset_index(inplace=True)
            stock_data = ajustar_precios_por_splits(stock_data, ticker)  # Adjust prices for splits
            cumulative_inflation = calcular_inflacion_diaria_rango(stock_data, start_date.year, start_date.month, end_date.year, end_date.month)
            generar_grafico(ticker, stock_data, cumulative_inflation)
        else:
            st.write(f"No se encontraron datos para {ticker} en el rango de fechas especificado.")
