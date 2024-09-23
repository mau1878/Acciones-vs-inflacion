import requests
import json
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

def get_yahoo_finance_data(symbol, start_date, end_date):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={int(start_date.timestamp())}&period2={int(end_date.timestamp())}&interval=1d"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    data = json.loads(response.text)
    return data

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

# Streamlit UI
st.title("Análisis de Ticker y Comparación con Inflación")
ticker = st.text_input("Ingrese el ticker (por defecto GGAL.BA):", "GGAL.BA")

for year in range(2017, 2025):
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)

    stock_data = get_yahoo_finance_data(ticker, start_date, end_date)

    if stock_data and 'chart' in stock_data and 'result' in stock_data['chart'] and stock_data['chart']['result']:
        result = stock_data['chart']['result'][0]

        df = pd.DataFrame({
            'Date': pd.to_datetime(result['timestamp'], unit='s'),
            'Close': result['indicators']['quote'][0]['close']
        })

        # Calcular la inflación acumulada correctamente
        monthly_inflation = inflation_rates[year]
        daily_inflation = []
        for month, rate in enumerate(monthly_inflation):
            days_in_month = (df['Date'].dt.month == month + 1).sum()
            daily_rate = (1 + rate / 100) ** (1 / days_in_month) - 1
            daily_inflation.extend([daily_rate] * days_in_month)

        # Ajustar la longitud de daily_inflation si es necesario
        daily_inflation = daily_inflation[:len(df)]

        # Calcular la inflación acumulada
        cumulative_inflation = [1]
        for rate in daily_inflation:
            cumulative_inflation.append(cumulative_inflation[-1] * (1 + rate))
        cumulative_inflation = cumulative_inflation[1:]  # Remover el 1 inicial

        # Calcular la línea de inflación
        inflation_line = df['Close'].iloc[0] * pd.Series(cumulative_inflation)

        # Calcular rendimientos
        stock_return = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100
        inflation_return = ((cumulative_inflation[-1] - 1) * 100)

        # Create figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name=ticker))
        fig.add_trace(go.Scatter(x=df['Date'], y=inflation_line, name='Inflación', line=dict(dash='dash', color='red')))

        fig.update_layout(
            title=f"{ticker} vs Inflación ({year})",
            xaxis_title='Fecha',
            yaxis_title='Precio (ARS)',
            height=600,
            width=900,
            dragmode='pan',
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
            paper_bgcolor="LightSteelBlue",
        )

        st.plotly_chart(fig)

        st.write(f"Año {year}:")
        st.write(f"Rendimiento de {ticker}: {stock_return:.2f}%")
        st.write(f"Inflación en Argentina: {inflation_return:.2f}%")
        st.write(f"Diferencia: {stock_return - inflation_return:.2f}%")
    else:
        st.write(f"No se encontraron datos para {ticker} en el año {year}.")
