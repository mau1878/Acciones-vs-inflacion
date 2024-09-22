import yfinance as yf
import investpy
import pandas as pd
import plotly.graph_objs as go
import streamlit as st

# Fetch Argentine stocks and CEDEARs data
arg_stocks = ['GGAL.BA', 'YPFD.BA', 'PAMP.BA']  # Add more stocks as needed
arg_stocks_data = {}
for stock in arg_stocks:
  arg_stocks_data[stock] = yf.download(stock, start='2010-01-01', end=pd.to_datetime('today'))

# Fetch cumulative Argentine inflation data
arg_inflation = investpy.get_inflation_historical('Argentina', as_json=False)
arg_inflation = arg_inflation.set_index('Date')
arg_inflation.index = pd.to_datetime(arg_inflation.index)

# Calculate returns for Argentine stocks and CEDEARs
arg_stocks_returns = {}
for stock, data in arg_stocks_data.items():
  arg_stocks_returns[stock] = data['Adj Close'].pct_change()

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
      fig.add_trace(go.Scatter(x=arg_stocks_returns[stock].index, y=(1 + arg_stocks_returns[stock]).cumprod(), name=stock))

# Customize layout
fig.update_layout(title='Argentine Stocks and CEDEARs vs. Cumulative Inflation',
                xaxis_title='Date',
                yaxis_title='Cumulative Returns')

# Display figure
st.plotly_chart(fig, use_container_width=True)
