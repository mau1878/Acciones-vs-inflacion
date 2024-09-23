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
    # Fetch stock data with adjusted close prices
    stock_data = yf.download(stock, start='2010-01-01', end=pd.to_datetime('today'))
    # Forward-fill missing values
    stock_data.fillna(method='ffill', inplace=True)
    # Store the stock data
    arg_stocks_data[stock] = stock_data

# Fetch cumulative Argentine inflation data
arg_inflation = fred.get_series('ARGCPIALLMINMEI', observation_start='2010-01-01', observation_end=pd.to_datetime('today'))
arg_inflation = pd.DataFrame(arg_inflation, columns=['Inflation'])

# Calculate cumulative inflation (assuming monthly inflation data, converting to daily)
arg_inflation['Cumulative_Inflation'] = (1 + arg_inflation['Inflation'].pct_change().fillna(0)).cumprod()

# Create Streamlit app
st.title('Argentine Stocks and CEDEARs vs. Cumulative Inflation')

# Stock selector in Streamlit
selected_stocks = st.multiselect('Select stocks to compare:', arg_stocks)

# Create figure
fig = go.Figure()

# Add cumulative Argentine inflation data
fig.add_trace(go.Scatter(x=arg_inflation.index, y=arg_inflation['Cumulative_Inflation'], 
                         mode='lines', name='Argentine Inflation', 
                         line=dict(color='orange', width=2)))

# Update figure with selected stocks
if selected_stocks:
    for stock in selected_stocks:
        # Calculate cumulative returns for each stock
        cumulative_returns = (1 + arg_stocks_data[stock]['Adj Close'].pct_change().fillna(0)).cumprod()
        fig.add_trace(go.Scatter(x=arg_stocks_data[stock].index, y=cumulative_returns, 
                                 mode='lines', name=stock, 
                                 line=dict(width=2)))

# Customize layout
fig.update_layout(title='Argentine Stocks and CEDEARs vs. Cumulative Inflation',
                  xaxis_title='Date', 
                  yaxis_title='Cumulative Returns',
                  yaxis_type="log",  # Log scale to better visualize inflation vs. stocks
                  template='plotly_dark')  # Better contrast for lines

# Display figure in Streamlit
st.plotly_chart(fig, use_container_width=True)
