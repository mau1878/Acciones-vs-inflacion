import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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

# Función para ajustar precios por splits
def ajustar_precios_por_splits(df, ticker):
    df.index = pd.to_datetime(df.index)

    if ticker == 'AGRO.BA':
        df.loc[df.index < datetime(2023, 11, 3), 'Close'] /= 6
        df.loc[df.index == datetime(2023, 11, 3), 'Close'] *= 2.1
    else:
        divisor = splits.get(ticker, 1)
        df.loc[df.index <= datetime(2024, 1, 23), 'Close'] /= divisor

    return df

# Función para calcular inflación diaria acumulada dentro de un rango de fechas
def calcular_inflacion_diaria_rango(df, start_year, start_month, end_year, end_month):
    cumulative_inflation = [1]

    for year in range(start_year, end_year + 1):
        if year not in inflation_rates:
            continue

        monthly_inflation = inflation_rates[year]

        if year == start_year:
            months = range(start_month - 1, 12)
        elif year == end_year:
            months = range(0, end_month)
        else:
            months = range(0, 12)

        for month in months:
            days_in_month = (df.index.year == year) & (df.index.month == month + 1)
            if days_in_month.sum() > 0:
                daily_rate = (1 + monthly_inflation[month] / 100) ** (1 / days_in_month.sum()) - 1
                for _ in range(days_in_month.sum()):
                    cumulative_inflation.append(cumulative_inflation[-1] * (1 + daily_rate))

    return cumulative_inflation[1:]

# Función para generar y mostrar gráfico
def generar_grafico(portfolio_data, cumulative_inflation, year_start):
    # Calculate the total portfolio value
    total_value = sum(data['value'] for data in portfolio_data.values() if 'value' in data)
    
    # Ensure the graph handles the case where total_value could be empty or None
    if total_value is not None:
        # Here, you would create and display your graph using Plotly, Matplotlib, etc.
        st.line_chart(total_value, title=f"Valor total de la cartera en {year_start.year}")
    else:
        st.warning("No se puede mostrar el gráfico porque el valor total es nulo.")

# Streamlit UI
st.title("Análisis de Ticker y Comparación con Inflación")

# Asegúrese de que la entrada del ticker esté en mayúsculas
ticker = st.text_input("Ingrese el ticker (por defecto GGAL.BA):", "GGAL.BA").upper()

# Nueva entrada para los pesos de la cartera
portfolio_input = st.text_input("Ingrese su cartera (ejemplo: GGAL.BA*0.5 + PAMP.BA*0.2 + SPY.BA*0.05 + YPFD.BA*0.25):", 
                                 "GGAL.BA*0.5 + PAMP.BA*0.2 + SPY.BA*0.05 + YPFD.BA*0.25")

# Opción para elegir entre análisis por año o por rango de fechas
analysis_type = st.selectbox("Seleccione tipo de análisis:", ('Por año (predeterminado)', 'Por rango de fechas'))

# Variables de fechas iniciales y finales
start_date = None
end_date = None

if analysis_type == 'Por rango de fechas':
    start_date = st.date_input("Fecha de inicio", datetime(2023, 1, 1))
    end_date = st.date_input("Fecha de fin", datetime.today())
else:  # Por año (predeterminado)
    start_date = datetime(2017, 1, 1)
    end_date = datetime.today()  # O modificar a fin de año actual si se desea

# Intenta obtener datos
try:
    if ticker:
        # Loop through the years for portfolio analysis
        for year in range(2017, 2025):
            year_start = datetime(year, 1, 1)
            year_end = datetime(year, 12, 31)
            
            # Get data for the ticker
            df = yf.download(ticker, start=year_start, end=year_end)
            if df.empty:
                st.warning(f"No se encontraron datos para {ticker} en {year}.")
                continue
            
            # Adjust prices for splits
            df = ajustar_precios_por_splits(df, ticker)
            
            # Pass end year and month to calcular_inflacion_diaria_rango
            cumulative_inflation = calcular_inflacion_diaria_rango(df, year_start.year, year_start.month, year_end.year, year_end.month)

            # Process portfolio input
            portfolio_data = {}
            for asset in portfolio_input.split('+'):
                asset_info = asset.strip().split('*')
                asset_ticker = asset_info[0].strip()
                weight = float(asset_info[1].strip()) if len(asset_info) > 1 else 1.0

                # Get the data for each asset ticker
                asset_df = yf.download(asset_ticker, start=year_start, end=year_end)
                if asset_df.empty:
                    st.warning(f"No se encontraron datos para {asset_ticker}.")
                    continue

                # Adjust prices for splits
                asset_df = ajustar_precios_por_splits(asset_df, asset_ticker)

                # Calculate portfolio value
                value = asset_df['Close'][-1] * weight  # Usar el último valor
                portfolio_data[asset_ticker] = {'data': asset_df, 'weight': weight, 'value': value}

            # Generate and show graph
            generar_grafico(portfolio_data, cumulative_inflation, year_start)

except Exception as e:
    st.error(f"Ocurrió un error: {e}")
