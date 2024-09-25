import yfinance as yf
from datetime import datetime, date
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
    if ticker == 'AGRO.BA':
        df.loc[df['Date'] < datetime(2023, 11, 3), 'Close'] /= 6
        df.loc[df['Date'] == datetime(2023, 11, 3), 'Close'] *= 2.1
    else:
        divisor = splits.get(ticker, 1)
        df.loc[df['Date'] <= datetime(2024, 1, 23), 'Close'] /= divisor
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
            days_in_month = (df['Date'].dt.year == year) & (df['Date'].dt.month == month + 1)
            if days_in_month.sum() > 0:
                daily_rate = (1 + monthly_inflation[month] / 100) ** (1 / days_in_month.sum()) - 1
                for _ in range(days_in_month.sum()):
                    cumulative_inflation.append(cumulative_inflation[-1] * (1 + daily_rate))

    return cumulative_inflation[1:]

# Función para generar y mostrar gráfico
def generar_grafico(ticker, df, cumulative_inflation, year=None, date_range=False):
    inflation_line = df['Close'].iloc[0] * pd.Series(cumulative_inflation)

    stock_return = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100
    inflation_return = ((cumulative_inflation[-1] - 1) * 100)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name=ticker))
    fig.add_trace(go.Scatter(x=df['Date'], y=inflation_line, name='Inflación', line=dict(dash='dash', color='red')))

    title_text = f"{ticker} vs Inflación ({year})" if year else f"{ticker} vs Inflación (Rango de Fechas)"
    fig.update_layout(
        title=title_text,
        xaxis_title='Fecha',
        yaxis_title='Precio (ARS)',
        height=600,
        width=900,
        dragmode='zoom',
        hovermode='x unified',
        xaxis=dict(
            rangeslider=dict(visible=False),
            showline=True,
            showgrid=True
        ),
        yaxis=dict(
            showline=True,
            showgrid=True
        ),
        margin=dict(l=50, r=50, b=100, t=100),
        paper_bgcolor="Black",
    )
    
    st.plotly_chart(fig)
    st.write(f"Rendimiento de {ticker}: {stock_return:.2f}%")
    st.write(f"Inflación en Argentina: {inflation_return:.2f}%")
    st.write(f"Diferencia: {stock_return - inflation_return:.2f}%")

# Streamlit UI
st.title("Análisis de Ticker y Comparación con Inflación")

# Ensure ticker input is in uppercase
ticker = st.text_input("Ingrese el ticker (por defecto GGAL.BA):", "GGAL.BA").upper()

# New input for portfolio weights
portfolio_input = st.text_input("Ingrese su cartera (ejemplo: GGAL.BA*0.5 + PAMP.BA*0.2 + SPY.BA*0.05 + YPFD.BA*0.25):", 
                                 "GGAL.BA*0.5 + PAMP.BA*0.2 + SPY.BA*0.05 + YPFD.BA*0.25")

# Option to choose between per-year analysis or date range analysis
analysis_type = st.radio(
    "Seleccione el tipo de análisis:",
    ('Por año (predeterminado)', 'Por rango de fechas')
)

# Function to calculate portfolio value based on user input
def calcular_portafolio(portfolio_str, start_date, end_date):
    stocks = portfolio_str.split("+")
    stock_values = []
    for stock in stocks:
        parts = stock.strip().split("*")
        ticker = parts[0].strip()
        weight = float(parts[1].strip()) if len(parts) > 1 else 1.0
        
        # Fetch stock data
        df = yf.download(ticker, start=start_date, end=end_date)
        df = ajustar_precios_por_splits(df, ticker)
        
        stock_values.append((df['Close'].iloc[-1] - df['Close'].iloc[0]) * weight)
    return sum(stock_values)

if analysis_type == 'Por año (predeterminado)':
    year = st.selectbox("Seleccione el año:", range(2017, 2025))
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    # Get stock data
    df = yf.download(ticker, start=start_date, end=end_date)
    df = ajustar_precios_por_splits(df, ticker)
    
    # Calculate inflation
    cumulative_inflation = calcular_inflacion_diaria_rango(df, year, 1, year, 12)

    # Generate graph
    generar_grafico(ticker, df, cumulative_inflation, year)

    # Calculate portfolio value
    portfolio_value = calcular_portafolio(portfolio_input, start_date, end_date)
    st.write(f"Valor total de la cartera: {portfolio_value:.2f} ARS")

else:
    start_date = st.date_input("Seleccione la fecha de inicio:", date(2024, 1, 1))
    end_date = st.date_input("Seleccione la fecha de fin:", date(2024, 12, 31))

    # Ensure end date is after start date
    if end_date >= start_date:
        # Get stock data
        df = yf.download(ticker, start=start_date, end=end_date)
        df = ajustar_precios_por_splits(df, ticker)
        
        # Calculate inflation
        cumulative_inflation = calcular_inflacion_diaria_rango(df, start_date.year, start_date.month, end_date.year, end_date.month)

        # Generate graph
        generar_grafico(ticker, df, cumulative_inflation)

        # Calculate portfolio value
        portfolio_value = calcular_portafolio(portfolio_input, start_date, end_date)
        st.write(f"Valor total de la cartera: {portfolio_value:.2f} ARS")
    else:
        st.error("La fecha de fin debe ser posterior a la fecha de inicio.")
