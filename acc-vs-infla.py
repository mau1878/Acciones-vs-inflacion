import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from datetime import datetime, date
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Your Alpha Vantage API key
ALPHA_VANTAGE_API_KEY = '1O4G91JNDJ8PA6RW'  # Replace with your actual API key

# (Rest of your initial script here...)

# Function to fetch stock data using yfinance or Alpha Vantage
def fetch_stock_data(ticker, start_date, end_date):
  try:
      # Attempt to fetch data using yfinance
      data = yf.download(ticker, start=start_date, end=end_date)
      if not data.empty:
          data.reset_index(inplace=True)
          return data
      else:
          st.write(f"No data found for {ticker} using yfinance. Trying Alpha Vantage...")
          # Try using Alpha Vantage
          data = fetch_data_alpha_vantage(ticker, start_date, end_date)
          return data
  except Exception as e:
      st.write(f"Error fetching data for {ticker}: {e}")
      return pd.DataFrame()

# Function to fetch data from Alpha Vantage
def fetch_data_alpha_vantage(ticker, start_date, end_date):
  ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
  try:
      data, meta_data = ts.get_daily_adjusted(symbol=ticker, outputsize='full')
      data.reset_index(inplace=True)
      data.rename(columns={
          'date': 'Date',
          'adjusted close': 'Close'
      }, inplace=True)
      data['Date'] = pd.to_datetime(data['Date'])
      mask = (data['Date'] >= pd.to_datetime(start_date)) & (data['Date'] <= pd.to_datetime(end_date))
      data = data.loc[mask]
      data.sort_values('Date', inplace=True)
      return data
  except Exception as e:
      st.write(f"Alpha Vantage error for {ticker}: {e}")
      return pd.DataFrame()

# (Rest of your script remains unchanged...)

# Streamlit UI
st.title("Análisis de Portafolio y Comparación con Inflación")

# Input for portfolio
portfolio_input = st.text_input(
  "Ingrese el ticker o portafolio (por ejemplo GGAL.BA*0.5+PAMP.BA*0.2+VIST.BA*0.05+YPFD.BA*0.25):",
  "GGAL.BA*1"
)

# Parse the portfolio input
portfolio = parse_portfolio(portfolio_input)

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

      # Initialize df_portfolio
      df_portfolio = None

      for ticker, weight in portfolio:
          stock_data = fetch_stock_data(ticker, start_date, end_date)
          if not stock_data.empty:
              stock_data = ajustar_precios_por_splits(stock_data, ticker)
              stock_data.rename(columns={'Close': f'Close_{ticker}'}, inplace=True)
              stock_data = stock_data[['Date', f'Close_{ticker}']]
              if df_portfolio is None:
                  df_portfolio = stock_data
              else:
                  df_portfolio = pd.merge(df_portfolio, stock_data, on='Date', how='outer')
          else:
              st.write(f"No data found for {ticker} in the year {year}.")

      if df_portfolio is not None and not df_portfolio.empty:
          # Sort by Date
          df_portfolio.sort_values('Date', inplace=True)
          # Fill missing values
          df_portfolio.fillna(method='ffill', inplace=True)
          df_portfolio.fillna(method='bfill', inplace=True)

          # Compute Portfolio_Value
          df_portfolio['Portfolio_Value'] = 0
          for ticker, weight in portfolio:
              df_portfolio['Portfolio_Value'] += weight * df_portfolio[f'Close_{ticker}']

          # Now, proceed to calculate cumulative inflation
          cumulative_inflation = calcular_inflacion_diaria_rango(
              df_portfolio, start_date.year, start_date.month, end_date.year, end_date.month
          )

          # Prepare 'df' as expected by generar_grafico
          df = df_portfolio[['Date', 'Portfolio_Value']].rename(columns={'Portfolio_Value': 'Close'})

          # Generate the plot
          generar_grafico('Portafolio', df, cumulative_inflation, year)
      else:
          st.write(f"No data found for the portfolio in the year {year}.")

else:
  start_date = st.date_input("Fecha de inicio", date(2020, 1, 1))
  end_date = st.date_input("Fecha de fin", date(2024, 12, 31))

  if start_date < end_date:
      # Initialize df_portfolio
      df_portfolio = None

      for ticker, weight in portfolio:
          stock_data = fetch_stock_data(ticker, start_date, end_date)
          if not stock_data.empty:
              stock_data = ajustar_precios_por_splits(stock_data, ticker)
              stock_data.rename(columns={'Close': f'Close_{ticker}'}, inplace=True)
              stock_data = stock_data[['Date', f'Close_{ticker}']]
              if df_portfolio is None:
                  df_portfolio = stock_data
              else:
                  df_portfolio = pd.merge(df_portfolio, stock_data, on='Date', how='outer')
          else:
              st.write(f"No data found for {ticker} in the specified date range.")

      if df_portfolio is not None and not df_portfolio.empty:
          # Sort by Date
          df_portfolio.sort_values('Date', inplace=True)
          # Fill missing values if needed
          df_portfolio.fillna(method='ffill', inplace=True)
          df_portfolio.fillna(method='bfill', inplace=True)

          # Compute Portfolio_Value
          df_portfolio['Portfolio_Value'] = 0
          for ticker, weight in portfolio:
              df_portfolio['Portfolio_Value'] += weight * df_portfolio[f'Close_{ticker}']

          # Now, proceed to calculate cumulative inflation
          cumulative_inflation = calcular_inflacion_diaria_rango(
              df_portfolio, start_date.year, start_date.month, end_date.year, end_date.month
          )

          # Prepare 'df' as expected by generar_grafico
          df = df_portfolio[['Date', 'Portfolio_Value']].rename(columns={'Portfolio_Value': 'Close'})

          # Generate the plot
          generar_grafico('Portafolio', df, cumulative_inflation)
      else:
          st.write(f"No data found for the portfolio in the specified date range.")
  else:
      st.write("La fecha de inicio debe ser anterior a la fecha de fin.")
