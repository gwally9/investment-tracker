import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import yfinance as yf
import json
import os
from datetime import datetime, timedelta
import threading
import time

class PortfolioTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("Financial Portfolio Tracker")
        self.root.geometry("1200x700")
        
        # Data storage
        self.portfolio = []
        self.data_file = "portfolio_data.json"
        self.load_data()
        
        # Price cache to avoid too many API calls
        self.price_cache = {}
        self.cache_timestamp = {}
        
        self.setup_ui()
        self.refresh_prices()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Summary section
        self.setup_summary_section(main_frame)
        
        # Control buttons
        self.setup_control_buttons(main_frame)
        
        # Portfolio table
        self.setup_portfolio_table(main_frame)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
    def setup_summary_section(self, parent):
        # Summary frame
        summary_frame = ttk.LabelFrame(parent, text="Portfolio Summary", padding="10")
        summary_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        summary_frame.columnconfigure(1, weight=1)
        summary_frame.columnconfigure(3, weight=1)
        summary_frame.columnconfigure(5, weight=1)
        
        # Summary labels
        ttk.Label(summary_frame, text="Total Investment:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.total_investment_var = tk.StringVar()
        ttk.Label(summary_frame, textvariable=self.total_investment_var, font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(summary_frame, text="Current Value:").grid(row=0, column=2, sticky=tk.W, padx=(20, 5))
        self.current_value_var = tk.StringVar()
        ttk.Label(summary_frame, textvariable=self.current_value_var, font=('Arial', 10, 'bold')).grid(row=0, column=3, sticky=tk.W)
        
        ttk.Label(summary_frame, text="Total P&L:").grid(row=0, column=4, sticky=tk.W, padx=(20, 5))
        self.total_pl_var = tk.StringVar()
        self.total_pl_label = ttk.Label(summary_frame, textvariable=self.total_pl_var, font=('Arial', 10, 'bold'))
        self.total_pl_label.grid(row=0, column=5, sticky=tk.W)
        
    def setup_control_buttons(self, parent):
        # Button frame
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(button_frame, text="Add Position", command=self.add_position).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Edit Position", command=self.edit_position).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Delete Position", command=self.delete_position).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Refresh Prices", command=self.refresh_prices).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Export Data", command=self.export_data).pack(side=tk.LEFT, padx=(0, 5))
        
    def setup_portfolio_table(self, parent):
        # Table frame with scrollbars
        table_frame = ttk.Frame(parent)
        table_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Treeview with scrollbars
        self.tree = ttk.Treeview(table_frame, columns=('Description', 'Ticker', 'Quantity', 'Purchase Price', 'Total Cost', 'Fees', 'Current Price', 'Current Value', 'P&L', 'P&L %'), show='headings')
        
        # Configure columns
        columns = {
            'Description': 150,
            'Ticker': 80,
            'Quantity': 80,
            'Purchase Price': 100,
            'Total Cost': 100,
            'Fees': 80,
            'Current Price': 100,
            'Current Value': 100,
            'P&L': 100,
            'P&L %': 80
        }
        
        for col, width in columns.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=tk.CENTER)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Configure tags for colored text
        self.tree.tag_configure('loss', foreground='red')
        self.tree.tag_configure('gain', foreground='green')
        
    def get_current_price(self, ticker):
        """Get current price from Yahoo Finance with caching"""
        now = datetime.now()
        
        # Check cache (refresh every 5 minutes)
        if ticker in self.price_cache and ticker in self.cache_timestamp:
            if now - self.cache_timestamp[ticker] < timedelta(minutes=5):
                return self.price_cache[ticker]
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                self.price_cache[ticker] = current_price
                self.cache_timestamp[ticker] = now
                return current_price
            else:
                return None
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return None
    
    def add_position(self):
        """Add a new position to the portfolio"""
        dialog = PositionDialog(self.root, "Add Position")
        if dialog.result:
            # Validate ticker by trying to get its price
            ticker = dialog.result['ticker'].upper()
            current_price = self.get_current_price(ticker)
            if current_price is None:
                messagebox.showerror("Error", f"Could not fetch data for ticker '{ticker}'. Please verify the ticker symbol.")
                return
            
            position = dialog.result
            position['ticker'] = ticker
            position['date_added'] = datetime.now().isoformat()
            self.portfolio.append(position)
            self.save_data()
            self.update_display()
            self.status_var.set(f"Added position: {ticker}")
    
    def edit_position(self):
        """Edit selected position"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a position to edit.")
            return
        
        item = selected[0]
        index = self.tree.index(item)
        position = self.portfolio[index]
        
        dialog = PositionDialog(self.root, "Edit Position", position)
        if dialog.result:
            # Update the position
            ticker = dialog.result['ticker'].upper()
            current_price = self.get_current_price(ticker)
            if current_price is None:
                messagebox.showerror("Error", f"Could not fetch data for ticker '{ticker}'. Please verify the ticker symbol.")
                return
            
            dialog.result['ticker'] = ticker
            dialog.result['date_added'] = position.get('date_added', datetime.now().isoformat())
            self.portfolio[index] = dialog.result
            self.save_data()
            self.update_display()
            self.status_var.set(f"Updated position: {ticker}")
    
    def delete_position(self):
        """Delete selected position"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a position to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this position?"):
            item = selected[0]
            index = self.tree.index(item)
            ticker = self.portfolio[index]['ticker']
            del self.portfolio[index]
            self.save_data()
            self.update_display()
            self.status_var.set(f"Deleted position: {ticker}")
    
    def refresh_prices(self):
        """Refresh all current prices"""
        def refresh_thread():
            self.status_var.set("Refreshing prices...")
            # Clear cache to force refresh
            self.price_cache.clear()
            self.cache_timestamp.clear()
            
            for position in self.portfolio:
                ticker = position['ticker']
                price = self.get_current_price(ticker)
                if price:
                    self.status_var.set(f"Updated {ticker}: ${price:.2f}")
                    time.sleep(0.5)  # Small delay to avoid rate limiting
            
            self.root.after(0, self.update_display)
            self.root.after(0, lambda: self.status_var.set("Prices refreshed"))
        
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def update_display(self):
        """Update the portfolio display"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        total_investment = 0
        total_current_value = 0
        
        for position in self.portfolio:
            ticker = position['ticker']
            description = position['description']
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
                
                # Format P&L with accounting format (red for losses)
                pl_text = f"${abs(pl):,.2f}" if pl >= 0 else f"(${abs(pl):,.2f})"
                pl_percent_text = f"{pl_percent:+.2f}%"
                
                tag = 'gain' if pl >= 0 else 'loss'
                
                self.tree.insert('', tk.END, values=(
                    description,
                    ticker,
                    f"{quantity:,.0f}",
                    f"${purchase_price:.2f}",
                    f"${total_cost:,.2f}",
                    f"${fees:.2f}",
                    f"${current_price:.2f}",
                    f"${current_value:,.2f}",
                    pl_text,
                    pl_percent_text
                ), tags=(tag,))
            else:
                self.tree.insert('', tk.END, values=(
                    description,
                    ticker,
                    f"{quantity:,.0f}",
                    f"${purchase_price:.2f}",
                    f"${total_cost:,.2f}",
                    f"${fees:.2f}",
                    "N/A",
                    "N/A",
                    "N/A",
                    "N/A"
                ))
        
        # Update summary
        self.total_investment_var.set(f"${total_investment:,.2f}")
        self.current_value_var.set(f"${total_current_value:,.2f}")
        
        total_pl = total_current_value - total_investment
        total_pl_percent = (total_pl / total_investment) * 100 if total_investment > 0 else 0
        
        if total_pl >= 0:
            pl_text = f"${total_pl:,.2f} (+{total_pl_percent:.2f}%)"
            self.total_pl_label.configure(foreground='green')
        else:
            pl_text = f"(${abs(total_pl):,.2f}) ({total_pl_percent:.2f}%)"
            self.total_pl_label.configure(foreground='red')
        
        self.total_pl_var.set(pl_text)
    
    def save_data(self):
        """Save portfolio data to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.portfolio, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save data: {e}")
    
    def load_data(self):
        """Load portfolio data from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.portfolio = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Could not load data: {e}")
                self.portfolio = []
    
    def export_data(self):
        """Export portfolio data to CSV"""
        try:
            import csv
            filename = f"portfolio_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['Description', 'Ticker', 'Quantity', 'Purchase Price', 'Total Cost', 'Fees', 'Current Price', 'Current Value', 'P&L', 'P&L %']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for position in self.portfolio:
                    ticker = position['ticker']
                    current_price = self.get_current_price(ticker)
                    quantity = position['quantity']
                    purchase_price = position['purchase_price']
                    fees = position['fees']
                    total_cost = (quantity * purchase_price) + fees
                    
                    if current_price:
                        current_value = quantity * current_price
                        pl = current_value - total_cost
                        pl_percent = (pl / total_cost) * 100 if total_cost > 0 else 0
                    else:
                        current_price = current_value = pl = pl_percent = "N/A"
                    
                    writer.writerow({
                        'Description': position['description'],
                        'Ticker': ticker,
                        'Quantity': quantity,
                        'Purchase Price': purchase_price,
                        'Total Cost': total_cost,
                        'Fees': fees,
                        'Current Price': current_price,
                        'Current Value': current_value,
                        'P&L': pl,
                        'P&L %': pl_percent
                    })
            
            messagebox.showinfo("Export Successful", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not export data: {e}")


class PositionDialog:
    def __init__(self, parent, title, position=None):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (300 // 2)
        self.dialog.geometry(f"400x300+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Form fields
        self.create_form_fields(main_frame, position)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.RIGHT)
        
        # Set focus and wait
        self.description_entry.focus_set()
        self.dialog.wait_window()
    
    def create_form_fields(self, parent, position):
        # Description
        ttk.Label(parent, text="Description:").pack(anchor=tk.W)
        self.description_var = tk.StringVar(value=position['description'] if position else '')
        self.description_entry = ttk.Entry(parent, textvariable=self.description_var, width=40)
        self.description_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Ticker
        ttk.Label(parent, text="Ticker Symbol:").pack(anchor=tk.W)
        self.ticker_var = tk.StringVar(value=position['ticker'] if position else '')
        self.ticker_entry = ttk.Entry(parent, textvariable=self.ticker_var, width=40)
        self.ticker_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Quantity
        ttk.Label(parent, text="Quantity:").pack(anchor=tk.W)
        self.quantity_var = tk.StringVar(value=str(position['quantity']) if position else '')
        self.quantity_entry = ttk.Entry(parent, textvariable=self.quantity_var, width=40)
        self.quantity_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Purchase Price
        ttk.Label(parent, text="Purchase Price ($):").pack(anchor=tk.W)
        self.price_var = tk.StringVar(value=str(position['purchase_price']) if position else '')
        self.price_entry = ttk.Entry(parent, textvariable=self.price_var, width=40)
        self.price_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Fees
        ttk.Label(parent, text="Fees ($):").pack(anchor=tk.W)
        self.fees_var = tk.StringVar(value=str(position['fees']) if position else '0')
        self.fees_entry = ttk.Entry(parent, textvariable=self.fees_var, width=40)
        self.fees_entry.pack(fill=tk.X, pady=(0, 10))
    
    def ok_clicked(self):
        try:
            # Validate inputs
            description = self.description_var.get().strip()
            ticker = self.ticker_var.get().strip().upper()
            quantity = float(self.quantity_var.get())
            purchase_price = float(self.price_var.get())
            fees = float(self.fees_var.get())
            
            if not description:
                raise ValueError("Description is required")
            if not ticker:
                raise ValueError("Ticker symbol is required")
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            if purchase_price <= 0:
                raise ValueError("Purchase price must be positive")
            if fees < 0:
                raise ValueError("Fees cannot be negative")
            
            self.result = {
                'description': description,
                'ticker': ticker,
                'quantity': quantity,
                'purchase_price': purchase_price,
                'fees': fees
            }
            
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
    
    def cancel_clicked(self):
        self.dialog.destroy()


if __name__ == "__main__":
    # Check if required packages are installed
    try:
        import yfinance
    except ImportError:
        print("Installing required package: yfinance")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
        import yfinance
    
    root = tk.Tk()
    app = PortfolioTracker(root)
    root.mainloop()
    