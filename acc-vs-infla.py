import yfinance as yf
from datetime import datetime
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

# Streamlit UI
st.title("Análisis de Ticker y Comparación con Inflación")
ticker = st.text_input("Ingrese el ticker (por defecto GGAL.BA):", "GGAL.BA")

# New feature: Option to choose date range
date_range_mode = st.checkbox("Comparar en un solo gráfico por rango de fechas", value=False)

if date_range_mode:
    # Select a date range from 2017 onwards
    start_date = st.date_input("Fecha de inicio", value=datetime(2017, 1, 1), min_value=datetime(2017, 1, 1))
    end_date = st.date_input("Fecha de fin", value=datetime(2024, 12, 31), min_value=datetime(2017, 1, 1))

    # Fetching data using yfinance
    stock_data = yf.download(ticker, start=start_date, end=end_date)

    if not stock_data.empty:
        stock_data.reset_index(inplace=True)
        df = stock_data[['Date', 'Close']]

        # Calcular inflación acumulada para el rango de fechas
        cumulative_inflation = [1]
        for year in range(start_date.year, end_date.year + 1):
            if year in inflation_rates:
                monthly_inflation = inflation_rates[year]
                for month, rate in enumerate(monthly_inflation):
                    days_in_month = (df['Date'].dt.month == month + 1).sum()
                    if days_in_month > 0:
                        daily_rate = (1 + rate / 100) ** (1 / days_in_month) - 1
                        cumulative_inflation += [cumulative_inflation[-1] * (1 + daily_rate)] * days_in_month

        cumulative_inflation = cumulative_inflation[:len(df)]

        # Calcular la línea de inflación
        inflation_line = df['Close'].iloc[0] * pd.Series(cumulative_inflation)

        # Crear la gráfica para el rango de fechas
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name=ticker))
        fig.add_trace(go.Scatter(x=df['Date'], y=inflation_line, name='Inflación', line=dict(dash='dash', color='red')))

        fig.update_layout(
            title=f"{ticker} vs Inflación ({start_date.year} - {end_date.year})",
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
            paper_bgcolor="Black",
        )

        st.plotly_chart(fig)
else:
    # Default behavior: one graph per year
    for year in range(2017, 2025):
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)

        # Fetching data using yfinance
        stock_data = yf.download(ticker, start=start_date, end=end_date)

        if not stock_data.empty:
            stock_data.reset_index(inplace=True)
            df = stock_data[['Date', 'Close']]

            # Calcular la inflación acumulada correctamente
            monthly_inflation = inflation_rates[year]
            daily_inflation = []
            for month, rate in enumerate(monthly_inflation):
                days_in_month = (df['Date'].dt.month == month + 1).sum()
                daily_rate = (1 + rate / 100) ** (1 / days_in_month) - 1
                daily_inflation.extend([daily_rate] * days_in_month)

            daily_inflation = daily_inflation[:len(df)]

            # Calcular la inflación acumulada
            cumulative_inflation = [1]
            for rate in daily_inflation:
                cumulative_inflation.append(cumulative_inflation[-1] * (1 + rate))
            cumulative_inflation = cumulative_inflation[1:]

            # Calcular la línea de inflación
            inflation_line = df['Close'].iloc[0] * pd.Series(cumulative_inflation)

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
                paper_bgcolor="Black",
            )

            st.plotly_chart(fig)

            st.write(f"Año {year}:")
            st.write(f"Rendimiento de {ticker}: {stock_return:.2f}%")
            st.write(f"Inflación en Argentina: {inflation_return:.2f}%")
            st.write(f"Diferencia: {stock_return - inflation_return:.2f}%")
        else:
            st.write(f"No se encontraron datos para {ticker} en el año {year}.")
