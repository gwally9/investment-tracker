### seems to fail using Tk -- rewrite using Flask or an alternative framework

### I'll rewrite the application using Flask with a modern web interface. This will be much more reliable and provide a better user experience.


`Flask Portfolio Tracker`

I've rewritten the application using Flask with a modern web interface. This solution is much more reliable and provides a better user experience than the tkinter version.

## Key Features:
### Web-Based Interface:
- Modern, responsive design that works on desktop and mobile
- Professional styling with hover effects and smooth interactions
- Real-time updates without page refreshes

### All Original Features Maintained:
- Add, edit, and delete financial positions
- Live price data from Yahoo Finance with smart caching
- Profit/Loss calculations with accounting format (red losses in parentheses)
- Portfolio summary with totals and percentage gains/losses
- CSV export functionality
- Data persistence in JSON format

### Enhanced User Experience:
- Modal dialogs for adding/editing positions
- Status notifications for all operations
- Responsive table design
- Color-coded gains (green) and losses (red)
- Mobile-friendly responsive layout

## Installation & Usage:
1. Install required packages:
`pip install flask yfinance`
2.Run the application:
`python portfolio_tracker.py`
3. Open your browser: Navigate to http://localhost:5000

## How to Use:
1. Add Positions: Click "Add Position" to enter new investments
2. Edit/Delete: Use the buttons in each row to modify positions
3. Refresh Prices: Click "Refresh Prices" to update market values
4. Export Data: Click "Export CSV" to download your portfolio data
## Technical Advantages:
- Reliability: No GUI framework compatibility issues
- Cross-platform: Works on any device with a web browser
- Scalability: Can easily be deployed to cloud services
- Modern UI: Professional appearance with responsive design
- API-based: Clean separation between frontend and backend
<br>
The application automatically creates the HTML template and starts a web server. All your portfolio data is saved locally in portfolio_data.json and the interface provides real-time feedback for all operations.