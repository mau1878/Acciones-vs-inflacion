import yfinance as yf
from datetime import datetime, date
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import re

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
  if ticker == 'AGRO.BA':
      # Ajuste para AGRO.BA
      split_date = datetime(2023, 11, 3)
      df.loc[df['Date'] < split_date, 'Close'] /= 6
      df.loc[df['Date'] == split_date, 'Close'] *= 2.1
  else:
      divisor = splits.get(ticker, 1)  # Valor por defecto es 1 si no está en el diccionario
      split_threshold_date = datetime(2024, 1, 23)
      df.loc[df['Date'] <= split_threshold_date, 'Close'] /= divisor
  return df

# ------------------------------
# Función para calcular inflación diaria acumulada dentro de un rango de fechas
def calcular_inflacion_diaria_rango(df, start_year, start_month, end_year, end_month):
  cumulative_inflation = [1]  # Comienza con 1 para no alterar los valores

  for year in range(start_year, end_year + 1):
      if year not in inflation_rates:
          continue

      monthly_inflation = inflation_rates[year]

      # Define the range of months to consider para el año actual
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
              daily_rate = (1 + monthly_inflation[month] / 100) ** (1 / num_days) - 1
              for _ in range(num_days):
                  cumulative_inflation.append(cumulative_inflation[-1] * (1 + daily_rate))

  return cumulative_inflation[1:]  # Remover el valor inicial de 1

# ------------------------------
# Función para generar y mostrar gráfico
def generar_grafico(expression_str, df, cumulative_inflation, year=None, date_range=False):
  if df.empty:
      st.write("El DataFrame está vacío. No se puede generar el gráfico.")
      return

  initial_value = df['Result'].iloc[0]
  inflation_line = initial_value * pd.Series(cumulative_inflation, index=df.index)

  # Calcular rendimientos
  expression_return = ((df['Result'].iloc[-1] - initial_value) / initial_value) * 100
  inflation_return = ((cumulative_inflation[-1] - 1) * 100)

  # Crear la figura
  fig = go.Figure()
  fig.add_trace(go.Scatter(x=df['Date'], y=df['Result'], name=expression_str))
  fig.add_trace(go.Scatter(x=df['Date'], y=inflation_line, name='Inflación', line=dict(dash='dash', color='red')))

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
      ),
      margin=dict(l=50, r=50, b=100, t=100),
      paper_bgcolor="Black",
  )
  
  # Configurar el color de fondo de la figura
  fig.update_layout(plot_bgcolor='white')

  st.plotly_chart(fig)
  st.write(f"**Rendimiento de {expression_str}:** {expression_return:.2f}%")
  st.write(f"**Inflación en Argentina:** {inflation_return:.2f}%")
  st.write(f"**Diferencia:** {expression_return - inflation_return:.2f}%")

# ------------------------------
# Función para parsear la expresión y extraer tickers
def parse_expression(input_str):
  # Definir transformaciones para permitir multiplicación implícita, etc.
  transformations = (standard_transformations + (implicit_multiplication_application,))
  
  # Extraer tickers usando regex
  potential_tickers = set(re.findall(r'[A-Za-z0-9\._]+', input_str))
  
  # Crear símbolos permitidos
  allowed_symbols = {}
  for t in potential_tickers:
      allowed_symbols[t] = sp.Symbol(t)
  
  # Parsear expresión
  try:
      expr = parse_expr(input_str, local_dict=allowed_symbols, transformations=transformations)
  except Exception as e:
      raise ValueError(f"Expresión inválida: {e}")
  
  # Extraer tickers únicos utilizados en la expresión
  tickers = sorted([str(symbol) for symbol in expr.free_symbols])
  
  return expr, tickers

# ------------------------------
# Función para evaluar la expresión sobre el DataFrame
def evaluate_expression(expr, df):
  # Extraer símbolos (tickers) de la expresión
  symbols_in_expr = expr.free_symbols
  
  # Crear función lambdificada con argumentos nombrados
  func = sp.lambdify(symbols_in_expr, expr, modules='numpy')
  
  # Preparar argumentos con valores de cada ticker
  args_dict = {str(s): df[str(s)] for s in symbols_in_expr}
  
  # Evaluar la expresión
  try:
      result = func(**args_dict)
  except ZeroDivisionError:
      raise ZeroDivisionError("División por cero ocurrió al evaluar la expresión.")
  except Exception as e:
      raise ValueError(f"Error al evaluar la expresión: {e}")
  
  return result

# ------------------------------
# Streamlit UI
st.title("Análisis de Expresiones con Tickers y Comparación con Inflación")

st.markdown("""
Esta aplicación permite analizar expresiones matemáticas complejas que involucran diferentes tickers bursátiles y compararlos con la inflación en Argentina.

**Ejemplos de expresiones válidas:**
- `VIST/(YPFD.BA/YPF)`
- `GGAL.BA + TXR.BA/ALUA.BA`
- `AAPL.BA * 2 - GOOGL.BA / MSFT.BA`
""")

# Input for expression
expression_input = st.text_input(
  "Ingrese la expresión con tickers (por ejemplo `VIST/(YPFD.BA/YPF)` o `GGAL.BA + TXR.BA/ALUA.BA`):",
  "GGAL.BA*1"
)

# Option to choose between per-year analysis or date range analysis
analysis_type = st.radio(
  "Seleccione el tipo de análisis:",
  ('Por año (predeterminado)', 'Por rango de fechas')
)

# ------------------------------
if analysis_type == 'Por año (predeterminado)':
  # Analyze one graph per year (default)
  for year in range(2017, 2025):
      st.header(f"Análisis para el año {year}")
      start_date = datetime(year, 1, 1)
      end_date = datetime(year, 12, 31)

      # Parse the expression and extract tickers
      try:
          expr, tickers = parse_expression(expression_input)
          if not tickers:
              st.write("No se encontraron tickers en la expresión.")
              continue
      except ValueError as ve:
          st.error(f"Error al parsear la expresión: {ve}")
          break

      # Descargar datos para los tickers
      data_frames = []
      for ticker in tickers:
          stock_data = yf.download(ticker, start=start_date, end=end_date)
          if not stock_data.empty:
              stock_data.reset_index(inplace=True)
              stock_data = ajustar_precios_por_splits(stock_data, ticker)
              stock_data = stock_data[['Date', 'Close']].rename(columns={'Close': ticker})
              data_frames.append(stock_data)
          else:
              st.warning(f"No se encontraron datos para {ticker} en el año {year}.")

      if data_frames:
          # Merge all data frames on 'Date'
          df_expression = data_frames[0]
          for df in data_frames[1:]:
              df_expression = pd.merge(df_expression, df, on='Date', how='outer')

          # Sort by Date
          df_expression.sort_values('Date', inplace=True)
          # Fill missing values
          df_expression.fillna(method='ffill', inplace=True)
          df_expression.fillna(method='bfill', inplace=True)

          # Evaluar la expresión
          try:
              df_expression['Result'] = evaluate_expression(expr, df_expression)
          except ZeroDivisionError as zde:
              st.error(f"Error en la expresión para el año {year}: {zde}")
              continue
          except ValueError as ve:
              st.error(f"Error en la expresión para el año {year}: {ve}")
              continue

          # Calcular inflación acumulada
          cumulative_inflation = calcular_inflacion_diaria_rango(
              df_expression, start_date.year, start_date.month, end_date.year, end_date.month
          )

          # Verificar que el número de días coincida
          if len(cumulative_inflation) != len(df_expression):
              st.warning(f"Desajuste en el cálculo de inflación para el año {year}.")

          # Agregar la columna de inflación
          df_expression['Inflación'] = cumulative_inflation

          # Generar el gráfico
          generar_grafico(expression_input, df_expression[['Date', 'Result']], cumulative_inflation, year)

      else:
          st.warning(f"No se pudieron obtener datos para los tickers en el año {year}.")

# ------------------------------
else:
  # Date range analysis
  st.header("Análisis por Rango de Fechas")
  col1, col2 = st.columns(2)
  with col1:
      start_date = st.date_input("Fecha de inicio", date(2020, 1, 1))
  with col2:
      end_date = st.date_input("Fecha de fin", date(2024, 12, 31))
  
  if start_date < end_date:
      # Parse the expression and extract tickers
      try:
          expr, tickers = parse_expression(expression_input)
          if not tickers:
              st.write("No se encontraron tickers en la expresión.")
      except ValueError as ve:
          st.error(f"Error al parsear la expresión: {ve}")
          st.stop()

      # Descargar datos para los tickers
      data_frames = []
      for ticker in tickers:
          stock_data = yf.download(ticker, start=start_date, end=end_date)
          if not stock_data.empty:
              stock_data.reset_index(inplace=True)
              stock_data = ajustar_precios_por_splits(stock_data, ticker)
              stock_data = stock_data[['Date', 'Close']].rename(columns={'Close': ticker})
              data_frames.append(stock_data)
          else:
              st.warning(f"No se encontraron datos para {ticker} en el rango de fechas especificado.")

      if data_frames:
          # Merge all data frames on 'Date'
          df_expression = data_frames[0]
          for df in data_frames[1:]:
              df_expression = pd.merge(df_expression, df, on='Date', how='outer')

          # Sort by Date
          df_expression.sort_values('Date', inplace=True)
          # Fill missing values
          df_expression.fillna(method='ffill', inplace=True)
          df_expression.fillna(method='bfill', inplace=True)

          # Evaluar la expresión
          try:
              df_expression['Result'] = evaluate_expression(expr, df_expression)
          except ZeroDivisionError as zde:
              st.error(f"Error en la expresión: {zde}")
              st.stop()
          except ValueError as ve:
              st.error(f"Error en la expresión: {ve}")
              st.stop()

          # Calcular inflación acumulada
          cumulative_inflation = calcular_inflacion_diaria_rango(
              df_expression, start_date.year, start_date.month, end_date.year, end_date.month
          )

          # Verificar que el número de días coincida
          if len(cumulative_inflation) != len(df_expression):
              st.warning("Desajuste en el cálculo de inflación para el rango de fechas seleccionado.")

          # Agregar la columna de inflación
          df_expression['Inflación'] = cumulative_inflation

          # Generar el gráfico
          generar_grafico(expression_input, df_expression[['Date', 'Result']], cumulative_inflation)
      else:
          st.warning("No se pudieron obtener datos para los tickers en el rango de fechas especificado.")
  else:
      st.error("La fecha de inicio debe ser anterior a la fecha de fin.")
