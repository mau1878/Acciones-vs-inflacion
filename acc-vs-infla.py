import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import streamlit as st

# Load inflation data from CSV
inflation_data = pd.read_csv('inflaciónargentina2.csv', parse_dates=['Date'], dayfirst=True)

# Convert monthly inflation rates into daily cumulative inflation
inflation_data['CPI_MoM'] = inflation_data['CPI_MoM'].astype(float)
# Start with a cumulative factor of 1 for inflation, and calculate the daily inflation compounded
inflation_data['Cumulative_Inflation'] = (1 + inflation_data['CPI_MoM']).cumprod()

# Set up stock tickers (you can add more stocks here)
arg_stocks = ['GGAL.BA', 'YPFD.BA', 'PAMP.BA']
arg_stocks_data = {}

# Fetch stock data
for stock in arg_stocks:
    # Fetch stock data from Yahoo Finance
    stock_data = yf.download(stock, start='2010-01-01', end=pd.to_datetime('today'))
    # Forward-fill missing values
    stock_data.fillna(method='ffill', inplace=True)
    # Store the stock data
    arg_stocks_data[stock] = stock_data

# Create Streamlit app
st.title('Argentine Stocks and CEDEARs vs. Cumulative Inflation-Adjusted Returns')

# Stock selector in Streamlit
selected_stocks = st.multiselect('Select stocks to compare:', arg_stocks)

# Create figure
fig = go.Figure()

# Add cumulative inflation data
fig.add_trace(go.Scatter(x=inflation_data['Date'], y=inflation_data['Cumulative_Inflation'],
                         mode='lines', name='Cumulative Inflation',
                         line=dict(color='orange', width=2)))

# Update figure with selected stocks
if selected_stocks:
    for stock in selected_stocks:
        # Calculate cumulative returns for each stock
        stock_data = arg_stocks_data[stock]
        cumulative_returns = (1 + stock_data['Adj Close'].pct_change().fillna(0)).cumprod()

        # Merge stock data with inflation data on date
        merged_data = pd.merge(stock_data[['Adj Close']], inflation_data, how='inner', left_index=True, right_on='Date')

        # Calculate inflation-adjusted returns (stock returns minus cumulative inflation)
        inflation_adjusted_returns = cumulative_returns.loc[merged_data['Date'].values] / merged_data['Cumulative_Inflation'].values

        # Add adjusted stock returns to the plot
        fig.add_trace(go.Scatter(x=merged_data['Date'], y=inflation_adjusted_returns,
                                 mode='lines', name=f'{stock} (Adjusted)',
                                 line=dict(width=2)))

# Customize layout
fig.update_layout(title='Argentine Stocks vs. Inflation-Adjusted Returns',
                  xaxis_title='Date',
                  yaxis_title='Cumulative Returns (Inflation Adjusted)',
                  yaxis_type="log",  # Log scale to better visualize inflation vs. stocks
                  template='plotly_dark')

# Display figure in Streamlit
st.plotly_chart(fig, use_container_width=True)
