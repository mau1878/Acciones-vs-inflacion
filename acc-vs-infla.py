# Función actualizada para calcular inflación diaria en un rango de fechas
def calcular_inflacion_acumulada(df, start_date, end_date):
    cumulative_inflation = [1]
    
    # Loop through the years in the range
    for year in range(start_date.year, end_date.year + 1):
        if year in inflation_rates:
            monthly_inflation = inflation_rates[year]
            
            # Handle the starting and ending months based on the date range
            if year == start_date.year:
                start_month = start_date.month - 1
            else:
                start_month = 0
            
            if year == end_date.year:
                end_month = end_date.month - 1
            else:
                end_month = 11  # December
            
            # Loop through months and calculate inflation
            for month in range(start_month, end_month + 1):
                days_in_month = (df['Date'].dt.month == month + 1).sum()
                if days_in_month > 0:
                    monthly_rate = monthly_inflation[month] / 100
                    daily_rate = (1 + monthly_rate) ** (1 / days_in_month) - 1
                    daily_inflation = [daily_rate] * days_in_month
                    for rate in daily_inflation:
                        cumulative_inflation.append(cumulative_inflation[-1] * (1 + rate))
    
    return cumulative_inflation[1:]  # Remove the initial 1

# Función actualizada para el gráfico para un rango de fechas
def generar_grafico_rango_fechas(ticker, df, cumulative_inflation):
    inflation_line = df['Close'].iloc[0] * pd.Series(cumulative_inflation)

    # Calcular rendimientos
    stock_return = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100
    inflation_return = ((cumulative_inflation[-1] - 1) * 100)

    # Create figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name=ticker))
    fig.add_trace(go.Scatter(x=df['Date'], y=inflation_line, name='Inflación', line=dict(dash='dash', color='red')))

    title_text = f"{ticker} vs Inflación (Rango de Fechas)"
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
    st.write(f"Inflación acumulada en Argentina: {inflation_return:.2f}%")
    st.write(f"Diferencia: {stock_return - inflation_return:.2f}%")

# Actualización en la lógica de Streamlit para análisis por rango de fechas
if analysis_type == 'Por rango de fechas':
    start_date = st.date_input("Seleccione la fecha de inicio (desde 2017):", datetime(2017, 1, 1))
    end_date = st.date_input("Seleccione la fecha de fin:", datetime.now())

    if start_date < datetime(2017, 1, 1):
        st.error("La fecha de inicio no puede ser anterior al 1 de enero de 2017.")
    elif start_date >= end_date:
        st.error("La fecha de inicio debe ser anterior a la fecha de fin.")
    else:
        # Fetching data for the selected date range
        stock_data = yf.download(ticker, start=start_date, end=end_date)

        if not stock_data.empty:
            stock_data.reset_index(inplace=True)  # Reset index to access date as a column

            # Calcular inflación acumulada para el rango de fechas
            cumulative_inflation = calcular_inflacion_acumulada(stock_data, start_date, end_date)
            generar_grafico_rango_fechas(ticker, stock_data, cumulative_inflation)
        else:
            st.write(f"No se encontraron datos para {ticker} en el rango de fechas seleccionado.")
