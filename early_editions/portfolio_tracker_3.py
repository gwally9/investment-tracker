from flask import Flask, render_template, request, jsonify, send_file
import yfinance as yf
import json
import os
from datetime import datetime, timedelta
import csv
import io
from threading import Lock

app = Flask(__name__)

class PortfolioManager:
    def __init__(self):
        self.data_file = "portfolio_data.json"
        self.portfolio = []
        self.price_cache = {}
        self.cache_timestamp = {}
        self.lock = Lock()
        self.load_data()
    
    def get_current_price(self, ticker):
        """Get current price from Yahoo Finance with caching"""
        with self.lock:
            now = datetime.now()
            
            # Check cache (refresh every 5 minutes)
            if ticker in self.price_cache and ticker in self.cache_timestamp:
                if now - self.cache_timestamp[ticker] < timedelta(minutes=5):
                    return self.price_cache[ticker]
            
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    self.price_cache[ticker] = current_price
                    self.cache_timestamp[ticker] = now
                    return current_price
                else:
                    return None
            except Exception as e:
                print(f"Error fetching price for {ticker}: {e}")
                return None
    
    def add_position(self, position_data):
        """Add a new position to the portfolio"""
        # Validate ticker
        current_price = self.get_current_price(position_data['ticker'].upper())
        if current_price is None:
            return False, f"Could not fetch data for ticker '{position_data['ticker']}'"
        
        position = {
            'id': len(self.portfolio) + 1,
            'description': position_data['description'],
            'ticker': position_data['ticker'].upper(),
            'quantity': float(position_data['quantity']),
            'purchase_price': float(position_data['purchase_price']),
            'fees': float(position_data['fees']),
            'date_added': datetime.now().isoformat()
        }
        
        self.portfolio.append(position)
        self.save_data()
        return True, "Position added successfully"
    
    def edit_position(self, position_id, position_data):
        """Edit an existing position"""
        for i, position in enumerate(self.portfolio):
            if position['id'] == position_id:
                # Validate ticker if changed
                new_ticker = position_data['ticker'].upper()
                if new_ticker != position['ticker']:
                    current_price = self.get_current_price(new_ticker)
                    if current_price is None:
                        return False, f"Could not fetch data for ticker '{new_ticker}'"
                
                # Update position
                position.update({
                    'description': position_data['description'],
                    'ticker': new_ticker,
                    'quantity': float(position_data['quantity']),
                    'purchase_price': float(position_data['purchase_price']),
                    'fees': float(position_data['fees'])
                })
                
                self.save_data()
                return True, "Position updated successfully"
        
        return False, "Position not found"
    
    def delete_position(self, position_id):
        """Delete a position"""
        for i, position in enumerate(self.portfolio):
            if position['id'] == position_id:
                del self.portfolio[i]
                self.save_data()
                return True, "Position deleted successfully"
        
        return False, "Position not found"
    
    def get_portfolio_data(self):
        """Get portfolio data with current prices and calculations"""
        portfolio_data = []
        total_investment = 0
        total_current_value = 0
        
        for position in self.portfolio:
            ticker = position['ticker']
            quantity = position['quantity']
            purchase_price = position['purchase_price']
            fees = position['fees']
            
            total_cost = (quantity * purchase_price) + fees
            total_investment += total_cost
            
            current_price = self.get_current_price(ticker)
            
            if current_price is not None:
                current_value = quantity * current_price
                total_current_value += current_value
                pl = current_value - total_cost
                pl_percent = (pl / total_cost) * 100 if total_cost > 0 else 0
            else:
                current_value = pl = pl_percent = None
            
            portfolio_data.append({
                'id': position['id'],
                'description': position['description'],
                'ticker': ticker,
                'quantity': quantity,
                'purchase_price': purchase_price,
                'total_cost': total_cost,
                'fees': fees,
                'current_price': current_price,
                'current_value': current_value,
                'pl': pl,
                'pl_percent': pl_percent,
                'date_added': position['date_added']
            })
        
        # Calculate totals
        total_pl = total_current_value - total_investment if total_current_value > 0 else 0
        total_pl_percent = (total_pl / total_investment) * 100 if total_investment > 0 else 0
        
        summary = {
            'total_investment': total_investment,
            'total_current_value': total_current_value,
            'total_pl': total_pl,
            'total_pl_percent': total_pl_percent
        }
        
        return portfolio_data, summary
    
    def refresh_all_prices(self):
        """Clear cache to force price refresh"""
        with self.lock:
            self.price_cache.clear()
            self.cache_timestamp.clear()
    
    def save_data(self):
        """Save portfolio data to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.portfolio, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def load_data(self):
        """Load portfolio data from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.portfolio = json.load(f)
            except Exception as e:
                print(f"Error loading data: {e}")
                self.portfolio = []

# Initialize portfolio manager
portfolio_manager = PortfolioManager()

@app.route('/')
def index():
    """Main portfolio page"""
    return render_template('index.html')

@app.route('/api/portfolio')
def get_portfolio():
    """API endpoint to get portfolio data"""
    try:
        portfolio_data, summary = portfolio_manager.get_portfolio_data()
        return jsonify({
            'success': True,
            'portfolio': portfolio_data,
            'summary': summary
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/position', methods=['POST'])
def add_position():
    """API endpoint to add a new position"""
    try:
        data = request.json
        success, message = portfolio_manager.add_position(data)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/position/<int:position_id>', methods=['PUT'])
def edit_position(position_id):
    """API endpoint to edit a position"""
    try:
        data = request.json
        success, message = portfolio_manager.edit_position(position_id, data)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/position/<int:position_id>', methods=['DELETE'])
def delete_position(position_id):
    """API endpoint to delete a position"""
    try:
        success, message = portfolio_manager.delete_position(position_id)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/refresh-prices', methods=['POST'])
def refresh_prices():
    """API endpoint to refresh all prices"""
    try:
        portfolio_manager.refresh_all_prices()
        return jsonify({'success': True, 'message': 'Prices refreshed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/export')
def export_data():
    """API endpoint to export portfolio data as CSV"""
    try:
        portfolio_data, summary = portfolio_manager.get_portfolio_data()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Description', 'Ticker', 'Quantity', 'Purchase Price', 'Total Cost',
            'Fees', 'Current Price', 'Current Value', 'P&L', 'P&L %', 'Date Added'
        ])
        
        # Write data
        for position in portfolio_data:
            writer.writerow([
                position['description'],
                position['ticker'],
                position['quantity'],
                position['purchase_price'],
                position['total_cost'],
                position['fees'],
                position['current_price'] if position['current_price'] else 'N/A',
                position['current_value'] if position['current_value'] else 'N/A',
                position['pl'] if position['pl'] else 'N/A',
                f"{position['pl_percent']:.2f}%" if position['pl_percent'] else 'N/A',
                position['date_added']
            ])
        
        # Create file-like object
        output.seek(0)
        csv_data = output.getvalue()
        output.close()
        
        # Return as downloadable file
        filename = f"portfolio_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return send_file(
            io.BytesIO(csv_data.encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Create templates directory and HTML template
def create_template():
    """Create the HTML template"""
    template_dir = "templates"
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Tracker</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(to bottom, #1a365d, #0f1419);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        h1 {
            text-align: center;
            margin-bottom: 30px;
            color: #FFFFFF;
        }
        
        .summary-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .summary-item {
            text-align: center;
        }
        
        .summary-item h3 {
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 5px;
        }
        
        .summary-item .value {
            font-size: 24px;
            font-weight: bold;
        }
        
        .gain { color: #0e773a; }
        .loss { color: #e74c3c; }
        
        .controls {
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.3s;
        }
        
        .btn-primary {
            background-color: #3498db;
            color: white;
        }
        
        .btn-primary:hover {
            background-color: #2980b9;
        }
        
        .btn-success {
            background-color: #27ae60;
            color: white;
        }
        
        .btn-success:hover {
            background-color: #229954;
        }
        
        .btn-danger {
            background-color: #e74c3c;
            color: white;
        }
        
        .btn-danger:hover {
            background-color: #c0392b;
        }
        
        .portfolio-table {
            background: #e6e6e6;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }
        
        th {
            background-color: #34495e;
            color: white;
            font-weight: 600;
        }
        
        tr:hover {
            background-color: #f8f9fa;
        }
        
        .text-right {
            text-align: right;
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        
        .modal-content {
            background-color: white;
            margin: 5% auto;
            padding: 20px;
            border-radius: 8px;
            width: 90%;
            max-width: 500px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
        }
        
        input[type="text"], input[type="number"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .form-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
        }
        
        .status {
            background: #3498db;
            color: white;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
            display: none;
        }
        
        .status.success {
            background: #27ae60;
        }
        
        .status.error {
            background: #e74c3c;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .controls {
                flex-direction: column;
            }
            
            table {
                font-size: 12px;
            }
            
            th, td {
                padding: 8px 4px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Financial Portfolio Tracker</h1>
        
        <div id="status" class="status"></div>
        
        <div class="summary-section">
            <div class="summary-item">
                <h3>Total Investment</h3>
                <div id="totalInvestment" class="value">$0.00</div>
            </div>
            <div class="summary-item">
                <h3>Current Value</h3>
                <div id="currentValue" class="value">$0.00</div>
            </div>
            <div class="summary-item">
                <h3>Total P&L</h3>
                <div id="totalPL" class="value">$0.00</div>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn-primary" onclick="showAddModal()">Add Position</button>
            <button class="btn-success" onclick="refreshPrices()">Refresh Prices</button>
            <button class="btn-primary" onclick="exportData()">Export CSV</button>
        </div>
        
        <div class="portfolio-table">
            <table>
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Ticker</th>
                        <th class="text-right">Quantity</th>
                        <th class="text-right">Purchase Price</th>
                        <th class="text-right">Total Cost</th>
                        <th class="text-right">Fees</th>
                        <th class="text-right">Current Price</th>
                        <th class="text-right">Current Value</th>
                        <th class="text-right">P&L</th>
                        <th class="text-right">P&L %</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="portfolioTableBody">
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Modal for Add/Edit Position -->
    <div id="positionModal" class="modal">
        <div class="modal-content">
            <h3 id="modalTitle">Add Position</h3>
            <form id="positionForm">
                <div class="form-group">
                    <label for="description">Description:</label>
                    <input type="text" id="description" name="description" required>
                </div>
                <div class="form-group">
                    <label for="ticker">Ticker Symbol:</label>
                    <input type="text" id="ticker" name="ticker" required style="text-transform: uppercase;">
                </div>
                <div class="form-group">
                    <label for="quantity">Quantity:</label>
                    <input type="number" id="quantity" name="quantity" step="any" required>
                </div>
                <div class="form-group">
                    <label for="purchase_price">Purchase Price ($):</label>
                    <input type="number" id="purchase_price" name="purchase_price" step="0.01" required>
                </div>
                <div class="form-group">
                    <label for="fees">Fees ($):</label>
                    <input type="number" id="fees" name="fees" step="0.01" value="0">
                </div>
                <div class="form-actions">
                    <button type="button" onclick="closeModal()">Cancel</button>
                    <button type="submit" class="btn-primary">Save</button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        let currentEditId = null;
        
        // Load portfolio data on page load
        window.onload = function() {
            loadPortfolio();
        };
        
        function loadPortfolio() {
            fetch('/api/portfolio')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateSummary(data.summary);
                        updateTable(data.portfolio);
                    } else {
                        showStatus('Error loading portfolio: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    showStatus('Error: ' + error.message, 'error');
                });
        }
        
        function updateSummary(summary) {
            document.getElementById('totalInvestment').textContent = formatCurrency(summary.total_investment);
            document.getElementById('currentValue').textContent = formatCurrency(summary.total_current_value);
            
            const plElement = document.getElementById('totalPL');
            const pl = summary.total_pl;
            const plPercent = summary.total_pl_percent;
            
            if (pl >= 0) {
                plElement.textContent = `${formatCurrency(pl)} (+${plPercent.toFixed(2)}%)`;
                plElement.className = 'value gain';
            } else {
                plElement.textContent = `(${formatCurrency(Math.abs(pl))}) (${plPercent.toFixed(2)}%)`;
                plElement.className = 'value loss';
            }
        }
        
        function updateTable(portfolio) {
            const tbody = document.getElementById('portfolioTableBody');
            tbody.innerHTML = '';
            
            portfolio.forEach(position => {
                const row = document.createElement('tr');
                
                const pl = position.pl;
                const plClass = pl >= 0 ? 'gain' : 'loss';
                const plText = pl !== null ? (pl >= 0 ? formatCurrency(pl) : `(${formatCurrency(Math.abs(pl))})`) : 'N/A';
                const plPercentText = position.pl_percent !== null ? `${position.pl_percent >= 0 ? '+' : ''}${position.pl_percent.toFixed(2)}%` : 'N/A';
                
                row.innerHTML = `
                    <td>${position.description}</td>
                    <td>${position.ticker}</td>
                    <td class="text-right">${position.quantity.toFixed(0)}</td>
                    <td class="text-right">${formatCurrency(position.purchase_price)}</td>
                    <td class="text-right">${formatCurrency(position.total_cost)}</td>
                    <td class="text-right">${formatCurrency(position.fees)}</td>
                    <td class="text-right">${position.current_price ? formatCurrency(position.current_price) : 'N/A'}</td>
                    <td class="text-right">${position.current_value ? formatCurrency(position.current_value) : 'N/A'}</td>
                    <td class="text-right ${plClass}">${plText}</td>
                    <td class="text-right ${plClass}">${plPercentText}</td>
                    <td>
                        <button class="btn-primary" onclick="editPosition(${position.id})">Edit</button>
                        <button class="btn-danger" onclick="deletePosition(${position.id})">Delete</button>
                    </td>
                `;
                
                tbody.appendChild(row);
            });
        }
        
        function formatCurrency(amount) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            }).format(amount);
        }
        
        function showStatus(message, type = 'info') {
            const statusEl = document.getElementById('status');
            statusEl.textContent = message;
            statusEl.className = `status ${type}`;
            statusEl.style.display = 'block';
            
            setTimeout(() => {
                statusEl.style.display = 'none';
            }, 5000);
        }
        
        function showAddModal() {
            currentEditId = null;
            document.getElementById('modalTitle').textContent = 'Add Position';
            document.getElementById('positionForm').reset();
            document.getElementById('positionModal').style.display = 'block';
        }
        
        function editPosition(id) {
            // Find position data
            fetch('/api/portfolio')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const position = data.portfolio.find(p => p.id === id);
                        if (position) {
                            currentEditId = id;
                            document.getElementById('modalTitle').textContent = 'Edit Position';
                            document.getElementById('description').value = position.description;
                            document.getElementById('ticker').value = position.ticker;
                            document.getElementById('quantity').value = position.quantity;
                            document.getElementById('purchase_price').value = position.purchase_price;
                            document.getElementById('fees').value = position.fees;
                            document.getElementById('positionModal').style.display = 'block';
                        }
                    }
                });
        }
        
        function deletePosition(id) {
            if (confirm('Are you sure you want to delete this position?')) {
                fetch(`/api/position/${id}`, { method: 'DELETE' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showStatus(data.message, 'success');
                            loadPortfolio();
                        } else {
                            showStatus('Error: ' + data.message, 'error');
                        }
                    });
            }
        }
        
        function closeModal() {
            document.getElementById('positionModal').style.display = 'none';
        }
        
        function refreshPrices() {
            showStatus('Refreshing prices...', 'info');
            fetch('/api/refresh-prices', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showStatus(data.message, 'success');
                        loadPortfolio();
                    } else {
                        showStatus('Error: ' + data.message, 'error');
                    }
                });
        }
        
        function exportData() {
            window.location.href = '/api/export';
        }
        
        // Handle form submission
        document.getElementById('positionForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData.entries());
            
            const url = currentEditId ? `/api/position/${currentEditId}` : '/api/position';
            const method = currentEditId ? 'PUT' : 'POST';
            
            fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showStatus(data.message, 'success');
                    closeModal();
                    loadPortfolio();
                } else {
                    showStatus('Error: ' + data.message, 'error');
                }
            });
        });
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('positionModal');
            if (event.target === modal) {
                closeModal();
            }
        }
    </script>
</body>
</html>"""
    
    with open(os.path.join(template_dir, "index.html"), "w") as f:
        f.write(html_content)

if __name__ == "__main__":
    # Create template file
    create_template()
    
    # Check if required packages are installed
    try:
        import yfinance
    except ImportError:
        print("Installing required package: yfinance")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    
    print("Starting Portfolio Tracker...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
    