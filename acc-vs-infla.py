import yfinance as yf
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Monthly inflation rates
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

# Function to calculate daily inflation within a date range
def calcular_inflacion_diaria_rango(start_date, end_date):
    cumulative_inflation = [1]
    days_in_range = pd.date_range(start=start_date, end=end_date)

    for date in days_in_range:
        year = date.year
        month = date.month - 1  # Adjust for zero-indexing
        if year in inflation_rates:
            daily_rate = (1 + inflation_rates[year][month] / 100) ** (1 / days_in_range.days_in_month) - 1
            cumulative_inflation.append(cumulative_inflation[-1] * (1 + daily_rate))

    return cumulative_inflation[1:]

# Function to adjust prices for splits
def ajustar_precios_por_splits(df, ticker):
    if ticker == 'AGRO.BA':
        # Specific adjustments for AGRO.BA if needed
        pass
    else:
        divisor = 1  # Placeholder for splits, implement as necessary
        df['Close'] /= divisor

    return df

# Function to generate and display the graph
def generar_grafico(portfolio_data, cumulative_inflation):
    fig = go.Figure()

    # Add each stock's data to the graph
    for ticker, data in portfolio_data.items():
        fig.add_trace(go.Scatter(x=data['df'].index, y=data['df']['Close'], name=ticker))

    # Calculate and plot cumulative inflation
    inflation_line = data['df']['Close'].iloc[0] * pd.Series(cumulative_inflation)
    fig.add_trace(go.Scatter(x=data['df'].index, y=inflation_line, name='Inflación', line=dict(dash='dash', color='red')))

    fig.update_layout(
        title="Análisis del Portafolio vs Inflación",
        xaxis_title='Fecha',
        yaxis_title='Precio (ARS)',
        height=600,
        width=900,
        dragmode='zoom',
        hovermode='x unified',
        xaxis=dict(showline=True, showgrid=True),
        yaxis=dict(showline=True, showgrid=True),
        margin=dict(l=50, r=50, b=100, t=100),
        paper_bgcolor="Black",
    )

    st.plotly_chart(fig)

# Streamlit UI
st.title("Análisis de Portafolio y Comparación con Inflación")

# Input for portfolio
portfolio_input = st.text_input("Ingrese su cartera (ejemplo: GGAL.BA*0.5 + PAMP.BA*0.2):", 
                                 "GGAL.BA*0.5 + PAMP.BA*0.2")

# Get date range for analysis
start_date = st.date_input("Fecha de inicio", datetime(2023, 1, 1))
end_date = st.date_input("Fecha de fin", datetime.today())

# Fetch and analyze data
if portfolio_input:
    portfolio_data = {}
    tickers = [item.split('*')[0].strip() for item in portfolio_input.split('+')]
    
    # Process each ticker in the portfolio
    for ticker in tickers:
        try:
            df = yf.download(ticker, start=start_date, end=end_date)
            if df.empty:
                st.warning(f"No se encontraron datos para el ticker {ticker}.")
                continue
            df = ajustar_precios_por_splits(df, ticker)
            portfolio_data[ticker] = {'df': df}

        except Exception as e:
            st.error(f"Se produjo un error al recuperar los datos para {ticker}: {e}")

    # Calculate cumulative inflation
    cumulative_inflation = calcular_inflacion_diaria_rango(start_date, end_date)

    # Generate the graph if data is available
    if portfolio_data:
        generar_grafico(portfolio_data, cumulative_inflation)
