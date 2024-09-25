import yfinance as yf
from datetime import datetime, date
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import numpy as np
import numexpr as ne
import re
import logging

# ------------------------------
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
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

# ------------------------------
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

# ------------------------------
# Función para ajustar precios por splits
def ajustar_precios_por_splits(df, ticker):
    try:
        if ticker == 'AGRO.BA':
            # Ajuste para AGRO.BA
            split_date = datetime(2023, 11, 3)
            df.loc[df['Date'] < split_date, 'Close'] /= 6
            df.loc[df['Date'] == split_date, 'Close'] *= 2.1
        else:
            divisor = splits.get(ticker, 1)  # Valor por defecto es 1 si no está en el diccionario
            split_threshold_date = datetime(2024, 1, 23)
            df.loc[df['Date'] <= split_threshold_date, 'Close'] /= divisor
    except Exception as e:
        logger.error(f"Error ajustando splits para {ticker}: {e}")
    return df

# ------------------------------
# Función para calcular inflación diaria acumulada dentro de un rango de fechas
def calcular_inflacion_diaria_rango(df, start_year, start_month, end_year, end_month):
    cumulative_inflation = [1]  # Comienza con 1 para no alterar los valores

    try:
        for year in range(start_year, end_year + 1):
            if year not in inflation_rates:
                continue

            monthly_inflation = inflation_rates[year]

            # Define the range of months para el año actual
            if year == start_year:
                months = range(start_month - 1, 12)  # Desde el mes de inicio hasta diciembre
            elif year == end_year:
                months = range(0, end_month)  # Desde enero hasta el mes final
            else:
                months = range(0, 12)  # Año completo

            for month in months:
                # Días dentro de este mes en el dataframe
                days_in_month = (df['Date'].dt.year == year) & (df['Date'].dt.month == month + 1)
                num_days = days_in_month.sum()
                if num_days > 0:
                    # Inflación diaria para ese mes
                    try:
                        daily_rate = (1 + monthly_inflation[month] / 100) ** (1 / num_days) - 1
                    except ZeroDivisionError:
                        logger.error(f"ZeroDivisionError for daily_rate in year {year}, month {month+1}")
                        daily_rate = 0

                    # Optimized appending using list comprehension
                    inflation_growth = [(1 + daily_rate) ** i for i in range(1, num_days + 1)]
                    cumulative_inflation.extend([cumulative_inflation[-1] * factor for factor in inflation_growth])
    except Exception as e:
        logger.error(f"Error calculando inflación: {e}")

    return cumulative_inflation[1:]  # Remover el valor inicial de 1

# ------------------------------
# Función para generar y mostrar gráfico
def generar_grafico(expression_str, df, cumulative_inflation, year=None, date_range=False):
    try:
        if df.empty:
            st.warning("El DataFrame está vacío. No se puede generar el gráfico.")
            return

        initial_value = df['Result'].iloc[0]
        # Ensure that the lengths match
        min_length = min(len(cumulative_inflation), len(df))
        inflation_line = initial_value * pd.Series(cumulative_inflation[:min_length], index=df.index[:min_length])

        # Calcular rendimientos
        expression_return = ((df['Result'].iloc[min_length-1] - initial_value) / initial_value) * 100
        inflation_return = ((cumulative_inflation[min_length-1] - 1) * 100)

        # Crear la figura
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'].iloc[:min_length], y=df['Result'].iloc[:min_length],
                                 name=expression_str, mode='lines'))
        fig.add_trace(go.Scatter(x=df['Date'].iloc[:min_length], y=inflation_line,
                                 name='Inflación', line=dict(dash='dash', color='red'), mode='lines'))

        title_text = f"{expression_str} vs Inflación ({year})" if year else f"{expression_str} vs Inflación (Rango de Fechas)"
        fig.update_layout(
            title=title_text,
            xaxis_title='Fecha',
            yaxis_title='Valor (ARS)',
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
            )
        )
        st.plotly_chart(fig)

        st.write(f"Rendimiento de la expresión: {expression_return:.2f}%")
        st.write(f"Rendimiento ajustado por inflación: {inflation_return:.2f}%")
    except Exception as e:
        logger.error(f"Error generando gráfico: {e}")
        st.warning("Hubo un error generando el gráfico.")
