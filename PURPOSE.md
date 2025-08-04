need a simple python app to track financial data regarding  purchases and sales of financial instruments. it should include name/description, ticker, purchase price, quantity, total cost, fees, current prices (get live or near live data from yahoo finance or another source), display profit or loss from purchase (loss in red accounting format) and the current price. Include in a summary header the overall purchase total, current market value of all investment and a percent gain or loss since acquiring the investments.

I've created a comprehensive financial portfolio tracker application with all the features you requested. Here's what the application includes:

## Key Features:
### Portfolio Management:

Add, edit, and delete financial positions
Track name/description, ticker symbol, quantity, purchase price, fees
Automatic data validation and ticker verification

### Real-time Price Data:

Fetches live prices from Yahoo Finance
Smart caching system (refreshes every 5 minutes) to avoid rate limiting
Background price updates with threading

### Financial Calculations:

Total cost calculation (quantity × price + fees)
Current market value
Profit/Loss in accounting format (losses shown in red with parentheses)
Percentage gains/losses
Overall portfolio summary with totals

### Summary Dashboard:

Total investment amount
Current market value of all holdings
Overall profit/loss with percentage
Color-coded gains (green) and losses (red)

### Additional Features:

Data persistence (saves to JSON file)
CSV export functionality
Professional GUI with sortable columns
Status updates and error handling
Scrollable table for large portfolios

## Installation & Usage:

1. Install the required package:
`pip install yfinance`

2. Run the application:
`python portfolio_tracker.py`

3. Using the app:

- Click "Add Position" to add new investments
- Use "Refresh Prices" to update current market values
- Double-click entries to edit them
- Export your data to CSV for external analysis



The application automatically validates ticker symbols by attempting to fetch their data from Yahoo Finance. All data is saved locally in a `portfolio_data.json` file, and you can export reports to CSV format.

The interface uses accounting format for losses (red text with parentheses) and shows gains in green, making it easy to quickly assess your portfolio's performance.