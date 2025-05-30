import yfinance as yf
from datetime import datetime, date
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import numpy as np
import numexpr as ne
import re
import logging
import requests

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
    2024: [20.6, 13.2, 11.0, 9.2, 4.2, 4.6, 4.0, 4.2, 3.5, 2.7, 2.4, 2.7],
    2025: [2.2, 2.3, 3.7, 2.2, 2.0, 0.018, 0.017, 0.016, 0.016]  # Estimación ficticia
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
                        logger.error(f"ZeroDivisionError for daily_rate in year {year}, month {month + 1}")
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
      expression_return = ((df['Result'].iloc[min_length - 1] - initial_value) / initial_value) * 100
      inflation_return = ((cumulative_inflation[min_length - 1] - 1) * 100)

      # Crear la figura
      fig = go.Figure()
      fig.add_trace(go.Scatter(x=df['Date'].iloc[:min_length], y=df['Result'].iloc[:min_length],
                               name="Activo", mode='lines'))
      fig.add_trace(go.Scatter(x=df['Date'].iloc[:min_length], y=inflation_line,
                               name='Inflación', line=dict(dash='dash', color='red'), mode='lines'))

      title_text = f"{expression_str} vs Inflación ({year})" if year else f"{expression_str} vs Inflación (Rango de Fechas)"

      # Add watermark
      fig.add_annotation(
          text="MTaurus - X: @MTaurus_ok",
          xref="paper",
          yref="paper",
          x=0.5,
          y=0.5,
          showarrow=False,
          font=dict(
              size=30,
              color="rgba(150,150,150,0.3)"
          ),
          textangle=-30,
          opacity=0.3
      )

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
      fig.update_layout(plot_bgcolor='black')

      st.plotly_chart(fig)
      st.markdown(f"**Rendimiento de {expression_str}:** {expression_return:.2f}%")
      st.markdown(f"**Inflación en Argentina:** {inflation_return:.2f}%")
      st.markdown(f"**Diferencia:** {expression_return - inflation_return:.2f}%")
  except Exception as e:
      logger.error(f"Error generando gráfico: {e}")
      st.error("Ocurrió un error al generar el gráfico. Por favor, inténtalo de nuevo.")


# ------------------------------
# Función para parsear la expresión y extraer tickers
def parse_expression(input_str):
    # Extraer tickers usando regex, mejor especificar que termina con .BA o similar
    potential_tickers = set(re.findall(r'\b[A-Za-z0-9\._]+\b', input_str))

    # Map tickers to valid variable names by replacing '.' with '_'
    ticker_mapping = {ticker: ticker.replace('.', '_') for ticker in potential_tickers}

    # Replace tickers in the expression with their mapped names
    expression_mapped = input_str
    for ticker, var_name in ticker_mapping.items():
        # Escape special regex characters in ticker
        escaped_ticker = re.escape(ticker)
        # Replace ticker with var_name using regex word boundaries to avoid partial replacements
        expression_mapped = re.sub(r'\b{}\b'.format(escaped_ticker), var_name, expression_mapped)

    # Verify that the expression only contains allowed characters
    if not re.match(r'^[A-Za-z0-9_\+\-\*\/\^\(\)\s]+$', expression_mapped):
        raise ValueError("La expresión contiene caracteres inválidos.")

    # Extract unique variable names used in the expression
    variables = set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', expression_mapped))

    # Remove known functions/operators if any; numexpr handles operators automatically
    # Optionally, you can implement a whitelist of allowed functions

    return expression_mapped, ticker_mapping


# ------------------------------
# Función para evaluar la expresión sobre el DataFrame usando numexpr
def evaluate_expression_numexpr(expr_str, df):
    try:
        # numexpr evaluates the expression with the dataframe columns as variables
        # Ensure that all variables in the expression exist in the dataframe
        variables = {var: df[var].values for var in re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', expr_str)}

        # Evaluate the expression
        result = ne.evaluate(expr_str, local_dict=variables)
    except ZeroDivisionError:
        logger.error("División por cero ocurrió al evaluar la expresión.")
        raise ZeroDivisionError("División por cero ocurrió al evaluar la expresión.")
    except Exception as e:
        logger.error(f"Error al evaluar la expresión: {e}")
        raise ValueError(f"Error al evaluar la expresión: {e}")

    return result


# ------------------------------
# Función para parsear el portafolio (Mantenida para compatibilidad)
def parse_portfolio(input_str):
    portfolio = []
    for part in input_str.split('+'):
        part = part.strip()
        if '*' in part:
            ticker, weight = part.split('*')
            ticker = ticker.strip()
            try:
                weight = float(weight.strip())
            except ValueError:
                weight = 1.0  # Default weight if parsing fails
        else:
            ticker = part.strip()
            weight = 1.0  # Default weight
        portfolio.append((ticker.upper(), weight))
    return portfolio


# ------------------------------
# Caching functions to optimize performance
@st.cache_data(ttl=86400)  # Cache data for one day
def descargar_datos(ticker, start, end, source='YFinance'):
  if source == 'YFinance':
      return descargar_datos_yfinance(ticker, start, end)
  elif source == 'AnálisisTécnico.com.ar':
      return descargar_datos_analisistecnico(ticker, start, end)
  elif source == 'IOL (Invertir Online)':
      return descargar_datos_iol(ticker, start, end)
  elif source == 'ByMA Data':
      return descargar_datos_byma(ticker, start, end)
  else:
      logger.error(f"Unknown data source: {source}")
      return pd.DataFrame()

# Create a separate function for yfinance (original implementation)
def descargar_datos_yfinance(ticker, start, end):
  try:
      stock_data = yf.download(ticker, start=start, end=end)

      if not stock_data.empty:
          stock_data = stock_data.reset_index()

          if isinstance(stock_data.columns, pd.MultiIndex):
              close_price = stock_data[('Close', ticker)]
              stock_data = pd.DataFrame({
                  'Date': stock_data['Date'],
                  ticker.replace('.', '_'): close_price
              })
          else:
              stock_data = ajustar_precios_por_splits(stock_data, ticker)
              var_name = ticker.replace('.', '_')
              stock_data = stock_data[['Date', 'Close']].rename(columns={'Close': var_name})

      return stock_data
  except Exception as e:
      logger.error(f"Error downloading data for {ticker}: {e}")
      return pd.DataFrame()

def descargar_datos_analisistecnico(ticker, start_date, end_date):
  try:
      # Convert dates to timestamps
      from_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp())
      to_timestamp = int(datetime.combine(end_date, datetime.max.time()).timestamp())

      cookies = {
          'ChyrpSession': '0e2b2109d60de6da45154b542afb5768',
          'i18next': 'es',
          'PHPSESSID': '5b8da4e0d96ab5149f4973232931f033',
      }

      headers = {
          'accept': '*/*',
          'content-type': 'text/plain',
          'dnt': '1',
          'referer': 'https://analisistecnico.com.ar/',
          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
      }

      # Remove .BA suffix and handle special cases if needed
      symbol = ticker.replace('.BA', '')

      params = {
          'symbol': symbol,
          'resolution': 'D',
          'from': str(from_timestamp),
          'to': str(to_timestamp),
      }

      response = requests.get(
          'https://analisistecnico.com.ar/services/datafeed/history',
          params=params,
          cookies=cookies,
          headers=headers,
      )

      if response.status_code == 200:
          data = response.json()

          # Check if we got a valid response
          if data.get('s') != 'ok':
              logger.error(f"Error in API response for {ticker}: {data.get('s')}")
              return pd.DataFrame()

          # Create DataFrame with all available data
          df = pd.DataFrame({
              'Date': pd.to_datetime(data['t'], unit='s'),
              'Close': data['c'],
              'High': data['h'],
              'Low': data['l'],
              'Open': data['o'],
              'Volume': data['v']
          })

          # Sort by date and remove any duplicates
          df = df.sort_values('Date').drop_duplicates(subset=['Date'])

          # Apply splits adjustment if needed
          df = ajustar_precios_por_splits(df, ticker)

          # Rename Close column to ticker name and select only needed columns
          var_name = ticker.replace('.', '_')
          df = df[['Date', 'Close']].rename(columns={'Close': var_name})

          logger.info(f"Successfully downloaded data for {ticker} from analisistecnico.com.ar")
          logger.info(f"Data range: {df['Date'].min()} to {df['Date'].max()}")
          logger.info(f"Number of records: {len(df)}")

          return df

      else:
          logger.error(f"Error fetching data for {ticker}: Status code {response.status_code}")
          return pd.DataFrame()

  except Exception as e:
      logger.error(f"Error downloading data from analisistecnico for {ticker}: {e}")
      return pd.DataFrame()

def descargar_datos_iol(ticker, start_date, end_date):
  try:
      # Convert dates to timestamps
      from_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp())
      to_timestamp = int(datetime.combine(end_date, datetime.max.time()).timestamp())

      cookies = {
          'intencionApertura': '0',
          '__RequestVerificationToken': 'DTGdEz0miQYq1kY8y4XItWgHI9HrWQwXms6xnwndhugh0_zJxYQvnLiJxNk4b14NmVEmYGhdfSCCh8wuR0ZhVQ-oJzo1',
          'isLogged': '1',
          'uid': '1107644',
      }

      headers = {
          'accept': '*/*',
          'content-type': 'text/plain',
          'referer': 'https://iol.invertironline.com',
          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
      }

      # Remove .BA suffix for IOL
      symbol = ticker.replace('.BA', '')

      params = {
          'symbolName': symbol,
          'exchange': 'BCBA',
          'from': str(from_timestamp),
          'to': str(to_timestamp),
          'resolution': 'D',
      }

      response = requests.get(
          'https://iol.invertironline.com/api/cotizaciones/history',
          params=params,
          cookies=cookies,
          headers=headers,
      )

      if response.status_code == 200:
          data = response.json()

          # Check if we got a valid response
          if data.get('status') != 'ok' or 'bars' not in data:
              logger.error(f"Error in API response for {ticker}: {data.get('status')}")
              return pd.DataFrame()

          # Extract bars data and create DataFrame
          bars = data['bars']
          df = pd.DataFrame(bars)

          # Rename columns to match our standard format
          df = df.rename(columns={
              'time': 'Date',
              'close': 'Close',
              'open': 'Open',
              'high': 'High',
              'low': 'Low',
              'volume': 'Volume'
          })

          # Convert timestamp to datetime
          df['Date'] = pd.to_datetime(df['Date'], unit='s')

          # Sort by date and remove any duplicates
          df = df.sort_values('Date').drop_duplicates(subset=['Date'])

          # Apply splits adjustment if needed
          df = ajustar_precios_por_splits(df, ticker)

          # Rename Close column to ticker name and select only needed columns
          var_name = ticker.replace('.', '_')
          df = df[['Date', 'Close']].rename(columns={'Close': var_name})

          logger.info(f"Successfully downloaded data for {ticker} from IOL")
          logger.info(f"Data range: {df['Date'].min()} to {df['Date'].max()}")
          logger.info(f"Number of records: {len(df)}")

          return df

      else:
          logger.error(f"Error fetching data for {ticker}: Status code {response.status_code}")
          return pd.DataFrame()

  except Exception as e:
      logger.error(f"Error downloading data from IOL for {ticker}: {e}")
      return pd.DataFrame()

def descargar_datos_byma(ticker, start_date, end_date):
  try:
      # Convert dates to timestamps
      from_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp())
      to_timestamp = int(datetime.combine(end_date, datetime.max.time()).timestamp())

      cookies = {
          'JSESSIONID': '5080400C87813D22F6CAF0D3F2D70338',
          '_fbp': 'fb.2.1728347943669.954945632708052302',
      }

      headers = {
          'Accept': 'application/json, text/plain, */*',
          'Accept-Language': 'de-DE,de;q=0.9,es-AR;q=0.8,es;q=0.7,en-DE;q=0.6,en;q=0.5,en-US;q=0.4',
          'Connection': 'keep-alive',
          'DNT': '1',
          'Referer': 'https://open.bymadata.com.ar/',
          'Sec-Fetch-Dest': 'empty',
          'Sec-Fetch-Mode': 'cors',
          'Sec-Fetch-Site': 'same-origin',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
          'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"Windows"',
      }

      # Remove .BA suffix for ByMA
      symbol = ticker.replace('.BA', '') + ' 24HS'

      params = {
          'symbol': symbol,
          'resolution': 'D',
          'from': str(from_timestamp),
          'to': str(to_timestamp),
      }

      # Disable SSL verification
      response = requests.get(
          'https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/chart/historical-series/history',
          params=params,
          cookies=cookies,
          headers=headers,
          verify=False  # Add this line to disable SSL verification
      )

      # Suppress only the specific InsecureRequestWarning
      import urllib3
      urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

      if response.status_code == 200:
          data = response.json()

          # Check if we got a valid response
          if data.get('s') != 'ok':
              logger.error(f"Error in API response for {ticker}: {data.get('s')}")
              return pd.DataFrame()

          # Create DataFrame with all available data
          df = pd.DataFrame({
              'Date': pd.to_datetime(data['t'], unit='s'),
              'Close': data['c'],
              'High': data['h'],
              'Low': data['l'],
              'Open': data['o'],
              'Volume': data['v']
          })

          # Sort by date and remove any duplicates
          df = df.sort_values('Date').drop_duplicates(subset=['Date'])

          # Apply splits adjustment if needed
          df = ajustar_precios_por_splits(df, ticker)

          # Rename Close column to ticker name and select only needed columns
          var_name = ticker.replace('.', '_')
          df = df[['Date', 'Close']].rename(columns={'Close': var_name})

          logger.info(f"Successfully downloaded data for {ticker} from ByMA Data")
          logger.info(f"Data range: {df['Date'].min()} to {df['Date'].max()}")
          logger.info(f"Number of records: {len(df)}")

          return df

      else:
          logger.error(f"Error fetching data for {ticker}: Status code {response.status_code}")
          return pd.DataFrame()

  except Exception as e:
      logger.error(f"Error downloading data from ByMA Data for {ticker}: {e}")
      return pd.DataFrame()

@st.cache_data(ttl=86400)
def obtener_inflacion(df, start_year, start_month, end_year, end_month):
    return calcular_inflacion_diaria_rango(df, start_year, start_month, end_year, end_month)


@st.cache_data(ttl=86400)
def obtener_evaluacion(expr_mapped, expression_mapped, df_expression):
    result = evaluate_expression_numexpr(expr_mapped, df_expression)
    return result


# ------------------------------
# Streamlit UI
st.title("Análisis de Expresiones con Tickers y Comparación con Inflación")

# Add this near the top of the Streamlit UI section
# Modify the sidebar radio button to include IOL
st.sidebar.title("Configuración")
data_source = st.sidebar.radio(
  "Fuente de datos:",
  ('YFinance', 'AnálisisTécnico.com.ar', 'IOL (Invertir Online)', 'ByMA Data')
)

# Update the information section
st.sidebar.markdown("""
### Información sobre fuentes de datos:
- **YFinance**: Datos internacionales, mejor para tickers extranjeros
- **AnálisisTécnico.com.ar**: Datos locales, mejor para tickers argentinos
- **IOL**: Datos locales con acceso a bonos y otros instrumentos

*Nota: Algunos tickers pueden no estar disponibles en todas las fuentes.*
""")

st.markdown("""
Esta aplicación permite analizar expresiones matemáticas complejas que involucran diferentes tickers bursátiles y compararlos con la inflación en Argentina.

**Ejemplos de expresiones válidas (USAR SIEMPRE MAYÚSCULAS!!!!!):**
- `VIST/(YPFD.BA/YPF)`
- `GGAL.BA + TXAR.BA/ALUA.BA`
- `AAPL.BA * 2 - GOOGL.BA / MSFT.BA`
""")

# Input for expression
expression_input = st.text_input(
    "Ingrese la expresión con tickers (por ejemplo `VIST/(YPFD.BA/YPF)` o `GGAL.BA + TXAR.BA/ALUA.BA`):",
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
            expr_mapped, ticker_mapping = parse_expression(expression_input)
            if not ticker_mapping:
                st.warning("No se encontraron tickers en la expresión.")
                continue
        except ValueError as ve:
            st.error(f"Error al parsear la expresión: {ve}")
            break

        # Descargar datos para los tickers
        data_frames = []
        for original_ticker, var_name in ticker_mapping.items():
            try:
                stock_data = descargar_datos(original_ticker, start_date, end_date, source=data_source)
                if not stock_data.empty:
                    data_frames.append(stock_data)
                else:
                    st.warning(f"No se encontraron datos para {original_ticker} en el año {year}.")
            except Exception as e:
                st.error(f"Error descargando datos para {original_ticker}: {e}")

        if data_frames:
            try:
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
                df_expression['Result'] = obtener_evaluacion(expr_mapped, expression_input, df_expression)

                # Calcular inflación acumulada
                cumulative_inflation = obtener_inflacion(
                    df_expression, start_date.year, start_date.month, end_date.year, end_date.month
                )

                # Verificar que el número de días coincida
                if len(cumulative_inflation) != len(df_expression):
                    st.warning(f"Desajuste en el cálculo de inflación para el año {year}.")

                # Agregar la columna de inflación (opcional)
                df_expression['Inflación'] = cumulative_inflation if len(cumulative_inflation) == len(
                    df_expression) else None

                # Generar el gráfico
                generar_grafico(expression_input, df_expression[['Date', 'Result']], cumulative_inflation, year)

            except ZeroDivisionError as zde:
                st.error(f"Error en la expresión para el año {year}: {zde}")
                continue
            except ValueError as ve:
                st.error(f"Error en la expresión para el año {year}: {ve}")
                continue
            except Exception as e:
                st.error(f"Ocurrió un error inesperado para el año {year}: {e}")
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

    if start_date >= end_date:
        st.error("La fecha de inicio debe ser anterior a la fecha de fin.")
    else:
        # Parse the expression and extract tickers
        try:
            expr_mapped, ticker_mapping = parse_expression(expression_input)
            if not ticker_mapping:
                st.warning("No se encontraron tickers en la expresión.")
        except ValueError as ve:
            st.error(f"Error al parsear la expresión: {ve}")
            st.stop()

        # Descargar datos para los tickers
        data_frames = []
        for original_ticker, var_name in ticker_mapping.items():
            try:
                stock_data = descargar_datos(original_ticker, start_date, end_date, source=data_source)
                if not stock_data.empty:
                    data_frames.append(stock_data)
                else:
                    st.warning(f"No se encontraron datos para {original_ticker} en el rango de fechas especificado.")
            except Exception as e:
                st.error(f"Error descargando datos para {original_ticker}: {e}")

        if data_frames:
            try:
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
                df_expression['Result'] = obtener_evaluacion(expr_mapped, expression_input, df_expression)

                # Calcular inflación acumulada
                cumulative_inflation = obtener_inflacion(
                    df_expression, start_date.year, start_date.month, end_date.year, end_date.month
                )

                # Verificar que el número de días coincida
                if len(cumulative_inflation) != len(df_expression):
                    st.warning("Desajuste en el cálculo de inflación para el rango de fechas seleccionado.")

                # Agregar la columna de inflación (opcional)
                df_expression['Inflación'] = cumulative_inflation if len(cumulative_inflation) == len(
                    df_expression) else None

                # Generar el gráfico
                generar_grafico(expression_input, df_expression[['Date', 'Result']], cumulative_inflation)

            except ZeroDivisionError as zde:
                st.error(f"Error en la expresión: {zde}")
                st.stop()
            except ValueError as ve:
                st.error(f"Error en la expresión: {ve}")
                st.stop()
            except Exception as e:
                st.error(f"Ocurrió un error inesperado: {e}")
        else:
            st.warning("No se pudieron obtener datos para los tickers en el rango de fechas especificado.")
