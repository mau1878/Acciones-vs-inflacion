import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import streamlit as st

# Load inflation data from CSV
inflation_data = pd.read_csv('inflaciónargentina2.csv', parse_dates=['Date'], dayfirst=True)

# Ensure 'Date' column is in datetime format
inflation_data['Date'] = pd.to_datetime(inflation_data['Date'])

# Calculate cumulative inflation from monthly inflation rates
inflation_data['CPI_MoM'] = inflation_data['CPI_MoM'].astype(float)
inflation_data['Cumulative_Inflation'] = (1 + inflation_data['CPI_MoM']).cumprod() - 1

# Create Streamlit app
st.title('Argentine Stocks vs. Inflation-Adjusted Returns')
st.write("Note: Argentine stock tickers must have the suffix '.BA'. For example, 'YPFD.BA'.")

# Date selection for analysis
start_date = st.date_input("Select start date:", pd.to_datetime('2010-01-01'))
end_date = st.date_input("Select end date:", pd.to_datetime('today'))

# Input for custom stock tickers
tickers_input = st.text_input("Enter stock tickers separated by commas (e.g., GGAL.BA, YPFD.BA, PAMP.BA):")
tickers = [ticker.strip().upper() for ticker in tickers_input.split(',') if ticker.strip()]

# Validate tickers
invalid_tickers = [ticker for ticker in tickers if not ticker.endswith('.BA')]
if invalid_tickers:
    st.error(f"The following tickers are invalid (they must end with '.BA'): {', '.join(invalid_tickers)}")

# Proceed with calculations if valid tickers
if tickers and not invalid_tickers:
    arg_stocks_data = {}

    # Fetch stock data
    for stock in tickers:
        try:
            stock_data = yf.download(stock, start=start_date, end=end_date)
            stock_data.fillna(method='ffill', inplace=True)
            arg_stocks_data[stock] = stock_data
        except Exception as e:
            st.error(f"Failed to fetch data for {stock}: {e}")

    # Create figure
    fig = go.Figure()

    # Filter inflation data within the selected date range
    inflation_filtered = inflation_data[(inflation_data['Date'] >= start_date) & (inflation_data['Date'] <= end_date)]

    # Add cumulative inflation line to the plot
    fig.add_trace(go.Scatter(x=inflation_filtered['Date'], 
                             y=inflation_filtered['Cumulative_Inflation'] * 100,
                             mode='lines', 
                             name='Cumulative Inflation (%)',
                             line=dict(color='orange', width=2)))

    # Calculate and plot adjusted returns for each stock
    for stock in tickers:
        if stock in arg_stocks_data:
            stock_data = arg_stocks_data[stock]

            # Calculate cumulative returns as a percentage
            cumulative_returns = (1 + stock_data['Adj Close'].pct_change().fillna(0)).cumprod() - 1

            # Merge stock data with inflation data based on date
            merged_data = pd.merge(stock_data[['Adj Close']], inflation_filtered, how='inner', left_index=True, right_on='Date')

            # Calculate inflation-adjusted returns
            inflation_adjusted_returns = cumulative_returns.loc[merged_data['Date'].values] * 100 - (merged_data['Cumulative_Inflation'].values * 100)

            # Add adjusted stock returns to the plot
            fig.add_trace(go.Scatter(x=merged_data['Date'], 
                                     y=inflation_adjusted_returns,
                                     mode='lines', 
                                     name=f'{stock} (Adjusted)',
                                     line=dict(width=2)))

    # Customize layout
    fig.update_layout(title='Argentine Stocks vs. Inflation-Adjusted Returns',
                      xaxis_title='Date',
                      yaxis_title='Adjusted Returns (%)',
                      template='plotly_dark')

    # Display the figure in Streamlit
    st.plotly_chart(fig, use_container_width=True)
