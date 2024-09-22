import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import streamlit as st
from fredapi import Fred

# Set up FRED API
fred = Fred(api_key='204e074d636f343ecb4aa8ab55e47200')

# Fetch Argentine stocks and CEDEARs data
arg_stocks = ['GGAL.BA', 'YPFD.BA', 'PAMP.BA']  # Add more stocks as needed
arg_stocks_data = {}
for stock in arg_stocks:
  arg_stocks_data[stock] = yf.download(stock, start='2010-01-01', end=pd.to_datetime('today'))

# Fetch cumulative Argentine inflation data
arg_inflation = fred.get_series('ARGCPIALLMINMEI', observation_start='2010-01-01', observation_end=pd.to_datetime('today'))
arg_inflation = pd.DataFrame(arg_inflation, columns=['Inflation'])

# Create figure
fig = go.Figure()

# Add Argentine inflation data
fig.add_trace(go.Scatter(x=arg_inflation.index, y=arg_inflation['Inflation'], name='Argentine Inflation'))

# Create Streamlit app
st.title('Argentine Stocks and CEDEARs vs. Cumulative Inflation')

# Add stock selector
selected_stocks = st.multiselect('Select stocks to compare:', arg_stocks)

# Update figure with selected stocks
if selected_stocks:
  fig.data = [fig.data[0]]  # Keep inflation data
  for stock in selected_stocks:
      fig.add_trace(go.Scatter(x=arg_stocks_data[stock].index, y=(1 + arg_stocks_data[stock]['Adj Close'].pct_change()).cumprod(), name=stock))

# Customize layout
fig.update_layout(title='Argentine Stocks and CEDEARs vs. Cumulative Inflation',
                xaxis_title='Date',
                yaxis_title='Cumulative Returns')

# Display figure
st.plotly_chart(fig, use_container_width=True)
