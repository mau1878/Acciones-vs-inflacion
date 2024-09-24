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
                daily_rate = (1 + monthly_inflation[month] / 100) ** (1 / days_in_month.sum()) - 1
                for _ in range(days_in_month.sum()):
                    cumulative_inflation.append(cumulative_inflation[-1] * (1 + daily_rate))

    return cumulative_inflation[1:]  # Remover el valor inicial de 1

# Función para generar y mostrar gráfico
def generar_grafico(ticker, df, cumulative_inflation, year=None, date_range=False):
    inflation_line = df['Close'].iloc[0] * pd.Series(cumulative_inflation)

    # Calcular rendimientos
    stock_return = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100
    inflation_return = ((cumulative_inflation[-1] - 1) * 100)

    # Create figure
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
    st.write(f"Rendimiento de {ticker}: {stock_return:.2f}%")
    st.write(f"Inflación en Argentina: {inflation_return:.2f}%")
    st.write(f"Diferencia: {stock_return - inflation_return:.2f}%")

# Streamlit UI
st.title("Análisis de Ticker y Comparación con Inflación")
ticker = st.text_input("Ingrese el ticker (por defecto GGAL.BA):", "GGAL.BA")

# Option to choose between per-year analysis or date range analysis
analysis_type = st.radio(
    "Seleccione el tipo de análisis:",
    ('Por año (predeterminado)', 'Por rango de fechas')
)

if analysis_type == 'Por año (predeterminado)':
    # Analyze one graph per year (default)
    for year in range(2017, 2025):
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)

        # Fetching data using yfinance
        stock_data = yf.download(ticker, start=start_date, end=end_date)

        if not stock_data.empty:
            stock_data.reset_index(inplace=True)  # Reset index to access date as a column
            cumulative_inflation = calcular_inflacion_diaria_rango(stock_data, year, 1, year, 12)
            generar_grafico(ticker, stock_data, cumulative_inflation, year=year)
        else:
            st.write(f"No se encontraron datos para {ticker} en el año {year}.")
else:
    # Analyze for a custom date range
    start_date = st.date_input("Seleccione la fecha de inicio (desde 2017):", date(2017, 1, 1))
    end_date = st.date_input("Seleccione la fecha de fin:", date.today())

    if start_date < date(2017, 1, 1):
        st.error("La fecha de inicio no puede ser anterior al 1 de enero de 2017.")
    elif start_date >= end_date:
        st.error("La fecha de inicio debe ser anterior a la fecha de fin.")
    else:
        # Fetching data for the selected date range
        stock_data = yf.download(ticker, start=start_date, end=end_date)

        if not stock_data.empty:
            stock_data.reset_index(inplace=True)  # Reset index to access date as a column

            # Inflación acumulada para cada año en el rango seleccionado
            cumulative_inflation = calcular_inflacion_diaria_rango(stock_data, start_date.year, start_date.month, end_date.year, end_date.month)
            generar_grafico(ticker, stock_data, cumulative_inflation, date_range=True)
        else:
            st.write(f"No se encontraron datos para {ticker} en el rango de fechas seleccionado.")
