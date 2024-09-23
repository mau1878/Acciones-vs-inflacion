import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import streamlit as st

# Load inflation data from CSV
inflation_data = pd.read_csv('inflaciónargentina2.csv', parse_dates=['Date'], dayfirst=True)

# Convert monthly inflation rates into cumulative inflation
inflation_data['CPI_MoM'] = inflation_data['CPI_MoM'].astype(float)
inflation_data['Cumulative_Inflation'] = (1 + inflation_data['CPI_MoM']).cumprod() - 1  # Convert to cumulative inflation

# Create Streamlit app
st.title('Argentine Stocks vs. Inflation-Adjusted Returns')

# Explain the .BA suffix requirement
st.write("Please note: Argentine stock tickers must have the suffix '.BA'. For example, 'YPFD.BA'.")

# Add a date picker for start and end dates
start_date = st.date_input("Select start date:", pd.to_datetime('2010-01-01'))
end_date = st.date_input("Select end date:", pd.to_datetime('today'))

# Allow the user to enter custom stock tickers
tickers_input = st.text_input("Enter stock tickers separated by commas (e.g., GGAL.BA, YPFD.BA, PAMP.BA):")
tickers = [ticker.strip().upper() for ticker in tickers_input.split(',') if ticker.strip()]

# Validate that tickers include the ".BA" suffix
invalid_tickers = [ticker for ticker in tickers if not ticker.endswith('.BA')]

# If there are invalid tickers, show a warning message
if invalid_tickers:
    st.error(f"The following tickers are invalid (they must end with '.BA'): {', '.join(invalid_tickers)}")

# If tickers are valid, proceed with the calculations
if tickers and not invalid_tickers:
    arg_stocks_data = {}

    # Fetch stock data for each ticker
    for stock in tickers:
        try:
            # Fetch stock data from Yahoo Finance
            stock_data = yf.download(stock, start=start_date, end=end_date)
            # Forward-fill missing values
            stock_data.fillna(method='ffill', inplace=True)
            # Store the stock data
            arg_stocks_data[stock] = stock_data
        except Exception as e:
            st.error(f"Failed to fetch data for {stock}: {e}")

    # Create figure
    fig = go.Figure()

    # Filter inflation data within the selected date range
    inflation_filtered = inflation_data[(inflation_data['Date'] >= pd.to_datetime(start_date)) &
                                        (inflation_data['Date'] <= pd.to_datetime(end_date))]

    # Add cumulative inflation data
    fig.add_trace(go.Scatter(x=inflation_filtered['Date'], y=inflation_filtered['Cumulative_Inflation'] * 100,
                             mode='lines', name='Cumulative Inflation (%)',
                             line=dict(color='orange', width=2)))

    # Update figure with selected stocks
    for stock in tickers:
        if stock in arg_stocks_data:
            stock_data = arg_stocks_data[stock]

            # Calculate cumulative returns as a percentage
            cumulative_returns = (1 + stock_data['Adj Close'].pct_change().fillna(0)).cumprod() - 1  # Convert to percentage

            # Get the cumulative inflation corresponding to the stock data dates
            merged_data = pd.merge(stock_data[['Adj Close']], inflation_filtered, how='inner', left_index=True, right_on='Date')

            # Calculate inflation-adjusted returns (cumulative returns minus cumulative inflation)
            inflation_adjusted_returns = cumulative_returns.loc[merged_data['Date'].values] * 100 - (merged_data['Cumulative_Inflation'].values * 100)

            # Add adjusted stock returns to the plot
            fig.add_trace(go.Scatter(x=merged_data['Date'], y=inflation_adjusted_returns,
                                     mode='lines', name=f'{stock} (Adjusted)',
                                     line=dict(width=2)))

    # Customize layout
    fig.update_layout(title='Argentine Stocks vs. Inflation-Adjusted Returns',
                      xaxis_title='Date',
                      yaxis_title='Adjusted Returns (%)',
                      template='plotly_dark')

    # Display figure in Streamlit
    st.plotly_chart(fig, use_container_width=True)
