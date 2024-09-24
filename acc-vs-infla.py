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
    'AGRO.BA': 6  # Divisor para fechas antes de 2023-11-03
}

# Función para ajustar precios por splits y ajustes específicos
def ajustar_precios_por_splits(df, ticker):
    divisor = splits.get(ticker, 1)  # Valor por defecto es 1 si no está en el diccionario
    
    if ticker == 'AGRO.BA':
        for index, row in df.iterrows():
            if row['Date'] < datetime(2023, 11, 3):
                df.at[index, 'Close'] /= 6  # Dividir por 6 antes de 2023-11-03
            elif row['Date'] == datetime(2023, 11, 3):
                df.at[index, 'Close'] *= 2.1  # Multiplicar por 2.1 el 2023-11-03
    else:
        df.loc[df['Date'] <= datetime(2024, 1, 23), 'Close'] /= divisor

    return df

# Función para calcular inflación diaria acumulada dentro de un rango de fechas
def calcular_inflacion_diaria_rango(df, start_year, start_month, end_year, end_month):
    cumulative_inflation = [1]  # Comienza con 1 para no alterar los valores

    for year in range(start_year, end_year + 1):
        if year not in inflation_rates:
            continue

        monthly_inflation = inflation_rates[year]

        # Define the range of months to consider for the year
        if year == start_year:
            months = range(start_month - 1, 12)  # Desde el mes de inicio hasta el final del año
        elif year == end_year:
            months = range(0, end_month)  # Desde el inicio del año hasta el mes final
        else:
            months = range(0, 12)  # Año completo

        for month in months:
            # Días dentro de este mes en el dataframe
            days_in_month = (df['Date'].dt.year == year) & (df['Date'].dt.month == month + 1)
            if days_in_month.sum() > 0:
                # Inflación diaria para ese mes
                daily_rate = (1 + monthly_inflation[month] / 100) ** (1 / (30 if month not in [1, 3, 5, 7, 8, 10, 12] else 28)) - 1
                cumulative_inflation.append(cumulative_inflation[-1] * (1 + daily_rate))

    # Agregar los valores de inflación acumulada al dataframe
    df['Cumulative_Inflation'] = cumulative_inflation[-len(df):]

    return cumulative_inflation

# Función para generar el gráfico
def generar_grafico(ticker, stock_data, cumulative_inflation):
    fig = go.Figure()
    
    # Gráfico de precios ajustados
    fig.add_trace(go.Scatter(x=stock_data['Date'], y=stock_data['Close'], mode='lines', name='Precio Ajustado'))
    
    # Gráfico de inflación acumulada
    fig.add_trace(go.Scatter(x=stock_data['Date'], y=stock_data['Cumulative_Inflation'], mode='lines', name='Inflación Acumulada', line=dict(dash='dash')))
    
    # Títulos y etiquetas
    fig.update_layout(title=f'Análisis de Precios y Ajuste por Inflación para {ticker}',
                      xaxis_title='Fecha',
                      yaxis_title='Valor',
                      hovermode='x unified')

    st.plotly_chart(fig)

# Interfaz de usuario
st.title("Análisis de Precios de Acciones")
ticker = st.text_input("Ingresa el ticker de la acción (por ejemplo, 'AGRO.BA'):", 'AGRO.BA')

if st.button("Obtener Datos"):
    # Verificación de datos
    stock_data = yf.download(ticker, start="2017-01-01", end=date.today())
    
    if not stock_data.empty:
        stock_data.reset_index(inplace=True)  # Reiniciar índice para acceder a la columna de fecha
        stock_data = ajustar_precios_por_splits(stock_data, ticker)  # Ajustar precios por splits
        cumulative_inflation = calcular_inflacion_diaria_rango(stock_data, 2017, 1, date.today().year, date.today().month)
        generar_grafico(ticker, stock_data, cumulative_inflation)
    else:
        st.write(f"No se encontraron datos para {ticker}.")
