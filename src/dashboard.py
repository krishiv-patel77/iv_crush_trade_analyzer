import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext

from datetime import datetime

import pandas as pd
import numpy as np

from src.exceptions import ConnectionError, NoDataError
from src.ib_client import IBApp
from src.utils import black_scholes_call, black_scholes_put, calculate_delta, calculate_gamma, calculate_theta, calculate_vega

import warnings
warnings.filterwarnings('ignore')


class IVCrushAnalyzer():

    def __init__(self, root):
        
        self.root = root
        self.root.title("Volatility Crush Trade Analyzer")
        self.root.geometry("1200x800")
        self.ib_app = IBApp()
        self.connected = False

        # Market data values
        self.current_spot_price = None
        self.current_iv = None
        self.ticker = None

        # Option Parameters
        self.risk_free_rate = 0.05
        self.vol_annualization = 252

        self.setup_ui()

    def setup_ui(self):
        
        # Configure the mainframe
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))

        # Make everything resizable as window expands
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Title for the app
        title_label = ttk.Label(main_frame, text="Volatility Crush Trade Analyzer", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Left col
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        
        # Right col  
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        right_frame.columnconfigure(0, weight=1)

        # All left col widgets
        self.setup_connection_section(left_frame, row=0)        # Connection widget
        self.setup_market_data_section(left_frame, row=1)       # Market data input widget
        self.setup_current_straddle_section(left_frame, row=2)  # Current straddle widget
        self.setup_current_greeks_section(left_frame, row=3)    # Current greeks widget
        self.setup_status_section(left_frame, row=4)           # Status widget

        # All right col widgets
        self.setup_scenario_section(right_frame, row=0)         # Scenario analysis widget
        self.setup_pnl_section(right_frame, row=1)              # PnL widget
        self.setup_new_greeks_section(right_frame, row=2)       # New greeks widget
        # Add some more functionality here for time decay and term slopes and stuff


    def setup_connection_section(self, parent_frame, row):
        # setup the connection frame and add weights
        conn_frame = ttk.LabelFrame(parent_frame, text="Interactive Brokers Connection", padding="5")
        conn_frame.grid(row=row, column=-0, sticky=(tk.E, tk.W), pady=(0,10))
        conn_frame.columnconfigure(1, weight=1) # Only need to config the text input fields to expand
        conn_frame.columnconfigure(3, weight=1)

        # set the host var field and text box
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, padx=(0,5), sticky=(tk.W))        # Fill all space to the left using sticky tk.W
        self.host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(conn_frame, textvariable=self.host_var, width=15).grid(row=0, column=1, padx=(0,15), sticky=(tk.E, tk.W))

        # set the port var field and text box
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=(0,5), sticky=(tk.W))
        self.port_var = tk.StringVar(value="7497")
        ttk.Entry(conn_frame, textvariable=self.port_var, width=15).grid(row=0, column=3, padx=(0,15), sticky=(tk.E, tk.W))

        # add a frame for the buttons to make it look nice and stuff
        button_frame = ttk.Frame(conn_frame)
        button_frame.grid(row=1, column=0, columnspan=4, pady=(10,0))

        # add the connect button
        self.connect_btn = ttk.Button(button_frame, text="Connect", command=self.connect_ib, state="normal")
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))

        # add the disconnect button
        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", command=self.disconnect_ib, state="disabled")
        self.disconnect_btn.pack(side=tk.LEFT)

        # add a label for connection status
        self.status_label = ttk.Label(conn_frame, text="● Disconnected", foreground="red")
        self.status_label.grid(row=2, column=0, columnspan=4, pady=(5, 0))


    def setup_market_data_section(self, parent_frame, row):
        market_frame = ttk.LabelFrame(parent_frame, text="Market Data & Parameters", padding="10")
        market_frame.grid(row=row, column=0, pady=(0,15), sticky=(tk.E, tk.W))
        market_frame.columnconfigure(1, weight=1)   # Configure the input fields col (1) to expand as window expands

        # ticker row
        ttk.Label(market_frame, text="Ticker:").grid(row=0, column=0, 
                                                     padx=(0,10), pady=(0,8), 
                                                     sticky=(tk.W))
        ticker_frame = ttk.Frame(market_frame)                      # Need a frame for this because we will have a button and input field on same line
        ticker_frame.grid(row=0, column=1, sticky=(tk.E, tk.W))
        ticker_frame.columnconfigure(0, weight=1)

        self.ticker_var = tk.StringVar(value="NVDA")                # Set the ticker var
        ttk.Entry(ticker_frame, textvariable=self.ticker_var, width=12, 
                  font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.fetch_data_btn = ttk.Button(ticker_frame, text="Fetch Data", command=self.fetch_market_data, state="disabled")
        self.fetch_data_btn.pack(side=tk.RIGHT, padx=(10,0))

        # spot price row
        ttk.Label(market_frame, text="Spot Price:").grid(row=1, column=0, 
                                                         padx=(0,10), pady=(0,8), 
                                                         sticky=(tk.W))
        self.spot_price_var = tk.StringVar()
        ttk.Entry(market_frame, textvariable=self.spot_price_var, width=15, font=("Arial", 10, "bold")).grid(
            row=1, column=1, sticky=(tk.E, tk.W), pady=(0,8))

        # strike price row
        ttk.Label(market_frame, text="Strike Price:").grid(row=2, column=0, 
                                                           padx=(0,10), pady=(0,8), 
                                                           sticky=(tk.W))
        self.strike_price_var = tk.StringVar()
        ttk.Entry(market_frame, textvariable=self.strike_price_var, width=15, font=("Arial", 10, "bold")).grid(
            row=2, column=1, sticky=(tk.E, tk.W), pady=(0,8))

        # iv row
        ttk.Label(market_frame, text="IV (%):").grid(row=3, column=0, 
                                                     padx=(0,10), pady=(0,8), 
                                                     sticky=(tk.W))
        self.iv_var = tk.StringVar()
        ttk.Entry(market_frame, textvariable=self.iv_var, width=15, font=("Arial", 10, "bold")).grid(
            row=3, column=1, sticky=(tk.E, tk.W), pady=(0,8))

        # days to expiry row
        ttk.Label(market_frame, text="Days to Expiry:").grid(row=4, column=0, 
                                                             padx=(0,10), pady=(0,8), 
                                                             sticky=(tk.W))
        self.days_to_expiry_var = tk.StringVar()
        ttk.Entry(market_frame, textvariable=self.days_to_expiry_var, width=15, font=("Arial", 10, "bold")).grid(
            row=4, column=1, sticky=(tk.E, tk.W), pady=(0,8))
        
        self.price_straddle_btn = ttk.Button(market_frame, text="Price Straddle", command=self.price_current_straddle, state="disabled")
        self.price_straddle_btn.grid(row=5, column=0, columnspan=2, pady=(10, 0))


    def setup_current_straddle_section(self, parent_frame, row):
        straddle_frame = ttk.LabelFrame(parent_frame, text="Current Straddle Pricing", padding="10")
        straddle_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0,15))
        straddle_frame.columnconfigure(1, weight=1)

        # call price
        ttk.Label(straddle_frame, text="Call Price:").grid(row=0, column=0, pady=(0,5), sticky=tk.W, padx=(0,10))
        self.call_price_label = ttk.Label(straddle_frame, text="$0.00", font=("Arial", 11, "bold"), foreground="green")
        self.call_price_label.grid(row=0, column=1, sticky=tk.W, pady=(0,8))

        # put price
        ttk.Label(straddle_frame, text="Put Price:").grid(row=1, column=0, pady=(0,5), sticky=tk.W, padx=(0,10))
        self.put_price_label = ttk.Label(straddle_frame, text="$0.00", font=("Arial", 11, "bold"), foreground="red")
        self.put_price_label.grid(row=1, column=1, sticky=tk.W, pady=(0,8))

        # horizontal line
        separator = ttk.Separator(straddle_frame, orient='horizontal')
        separator.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8)

        # stradle price
        ttk.Label(straddle_frame, text="Straddle Price:").grid(row=3, column=0, pady=(0,5), sticky=tk.W, padx=(0,10))
        self.straddle_price_label = ttk.Label(straddle_frame, text="$0.00", font=("Arial", 14, "bold"), foreground="deep sky blue")
        self.straddle_price_label.grid(row=3, column=1, sticky=tk.W, pady=(0,8))

    
    def setup_current_greeks_section(self, parent_frame, row):
        greek_frame = ttk.LabelFrame(parent_frame, text="Greeks", padding="10")
        greek_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0,15))
        greek_frame.columnconfigure(1, weight=1)
        greek_frame.columnconfigure(3, weight=1)

        # delta in row 1 to the left
        ttk.Label(greek_frame, text="Delta:").grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky=tk.W)
        self.delta_label = ttk.Label(greek_frame, text="0.000", font=("Arial", 10, "bold"))
        self.delta_label.grid(row=0, column=1, padx=(0, 15), pady=(0, 5), sticky=tk.W)
        
        # gamma in row 1 to the right
        ttk.Label(greek_frame, text="Gamma:").grid(row=0, column=2, padx=(0, 5), pady=(0, 5), sticky=tk.W)
        self.gamma_label = ttk.Label(greek_frame, text="0.000", font=("Arial", 10, "bold"))
        self.gamma_label.grid(row=0, column=3, pady=(0, 5), sticky=tk.W)
        
        # vega in row 2 to the left
        ttk.Label(greek_frame, text="Vega:").grid(row=1, column=0, padx=(0, 5), pady=(0, 5), sticky=tk.W)
        self.vega_label = ttk.Label(greek_frame, text="0.00", font=("Arial", 10, "bold"))
        self.vega_label.grid(row=1, column=1, padx=(0, 15), pady=(0, 5), sticky=tk.W)
        
        # theta in row 2 to the right
        ttk.Label(greek_frame, text="Theta:").grid(row=1, column=2, padx=(0, 5), pady=(0, 5), sticky=tk.W)
        self.theta_label = ttk.Label(greek_frame, text="0.00", font=("Arial", 10, "bold"))
        self.theta_label.grid(row=1, column=3, pady=(0, 5), sticky=tk.W)


    def setup_status_section(self, parent_frame, row):
        status_frame = ttk.LabelFrame(parent_frame, text="Status", padding="5")
        status_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.status_text = scrolledtext.ScrolledText(status_frame, height=6, width=40)
        self.status_text.grid(row=0, column=0, sticky=(tk.E, tk.W))

        # Configure the frame to expand with window 
        status_frame.columnconfigure(0, weight=1)
       

    def setup_scenario_section(self, parent_frame, row):
        scenario_frame = ttk.LabelFrame(parent_frame, text="Scenario Analysis", padding="10")
        scenario_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        scenario_frame.columnconfigure(1, weight=1)
        
        # new spot price (where you think price might be in the future for testing purposes)
        ttk.Label(scenario_frame, text="New Spot Price:").grid(row=0, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.new_spot_var = tk.StringVar()
        ttk.Entry(scenario_frame, textvariable=self.new_spot_var, width=15, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 8))
        
        # new IV in percentage (where you think the change in IV will be)
        ttk.Label(scenario_frame, text="New IV (%):").grid(row=1, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.new_iv_var = tk.StringVar()
        ttk.Entry(scenario_frame, textvariable=self.new_iv_var, width=15, font=("Arial", 10, "bold")).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 8))
        
        # button for analyzing the new scenario
        self.analyze_btn = ttk.Button(scenario_frame, text="Analyze Scenario", command=self.analyze_scenario, state="disabled")
        self.analyze_btn.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        

    def setup_pnl_section(self, parent, row):
        """ This frame is basically for helping you see how much PnL you would have generated for a long or short straddle position. """

        pnl_frame = ttk.LabelFrame(parent, text="P/L Analysis", padding="10")
        pnl_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        pnl_frame.columnconfigure(1, weight=1)
        
        # new straddle price based on the new scenario parameters
        ttk.Label(pnl_frame, text="New Straddle Price:").grid(row=0, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.new_straddle_label = ttk.Label(pnl_frame, text="$0.00", font=("Arial", 12, "bold"), foreground="deep sky blue")
        self.new_straddle_label.grid(row=0, column=1, sticky=tk.W, pady=(0, 8))
        
        separator = ttk.Separator(pnl_frame, orient='horizontal')
        separator.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8)
        
        # pnl for a long straddle
        ttk.Label(pnl_frame, text="Long P/L:").grid(row=2, column=0, padx=(0, 10), pady=(0, 5), sticky=tk.W)
        self.pnl_long_label = ttk.Label(pnl_frame, text="$0.00", font=("Arial", 12, "bold"))
        self.pnl_long_label.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        # pnl for a short straddle
        ttk.Label(pnl_frame, text="Short P/L:").grid(row=3, column=0, padx=(0, 10), sticky=tk.W)
        self.pnl_short_label = ttk.Label(pnl_frame, text="$0.00", font=("Arial", 12, "bold"))
        self.pnl_short_label.grid(row=3, column=1, sticky=tk.W)
        

    def setup_new_greeks_section(self, parent_frame, row):
        new_greek_frame = ttk.LabelFrame(parent_frame, text="New Scenario Greeks", padding="10")
        new_greek_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        new_greek_frame.columnconfigure(1, weight=1)
        new_greek_frame.columnconfigure(3, weight=1)
        
        ttk.Label(new_greek_frame, text="Delta:").grid(row=0, column=0, padx=(0, 5), pady=(0, 5), sticky=tk.W)
        self.new_delta_label = ttk.Label(new_greek_frame, text="0.000", font=("Arial", 10, "bold"))
        self.new_delta_label.grid(row=0, column=1, padx=(0, 15), pady=(0, 5), sticky=tk.W)
        
        ttk.Label(new_greek_frame, text="Gamma:").grid(row=0, column=2, padx=(0, 5), pady=(0, 5), sticky=tk.W)
        self.new_gamma_label = ttk.Label(new_greek_frame, text="0.000", font=("Arial", 10, "bold"))
        self.new_gamma_label.grid(row=0, column=3, pady=(0, 5), sticky=tk.W)
        
        ttk.Label(new_greek_frame, text="Vega:").grid(row=1, column=0, padx=(0, 5), pady=(0, 5), sticky=tk.W)
        self.new_vega_label = ttk.Label(new_greek_frame, text="0.00", font=("Arial", 10, "bold"))
        self.new_vega_label.grid(row=1, column=1, padx=(0, 15), pady=(0, 5), sticky=tk.W)
        
        ttk.Label(new_greek_frame, text="Theta:").grid(row=1, column=2, padx=(0, 5), pady=(0, 5), sticky=tk.W)
        self.new_theta_label = ttk.Label(new_greek_frame, text="0.00", font=("Arial", 10, "bold"))
        self.new_theta_label.grid(row=1, column=3, pady=(0, 5), sticky=tk.W)


    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)

        # Update the UI immediately after a change in the status text area
        self.root.update_idletasks()


    def connect_ib(self):   
        try:
            host = self.host_var.get()
            port = self.port_var.get()

            self.log_message("Connecting to IB...")

            server_version = self.ib_app.connect_ib(host, port)

            if self.ib_app.connected:
                self.connected = True
                self.connect_btn.config(state="disabled")
                self.disconnect_btn.config(state="normal")
                self.status_label.config(text="● Connected", foreground="green")
                self.fetch_data_btn.config(state="normal")
                self.price_straddle_btn.config(state="normal")

                # Log successful connection
                self.log_message(f"Successfully connected to IB (Server: {server_version})")
            else:
                self.log_message("Failed to Connect to IB TWS")

        except ConnectionError as e:
            self.log_message(e.message)

    def disconnect_ib(self):
        
        try:
            # disconnect
            self.ib_app.disconnect_ib()
            self.connected = False

            # reset buttons
            self.disconnect_btn.config(state="disabled")
            self.connect_btn.config(state="normal")
            self.fetch_data_btn.config(state="disabled")
            self.price_straddle_btn.config(state="disabled")
            self.analyze_btn.config(state="disabled")

            # reset labels
            self.status_label.config(text="● Disconnected", foreground="red")

            # reset variables on all screens
            self.clear_data()

            # log message
            self.log_message("Successfully Disconnected from IB TWS")
        except ConnectionError as e:
            self.log_message(e.message)

    def clear_data(self):
        """ Used to clear all variables and labels and stuff because there are too many of them"""
        
        # clear the init params
        self.current_iv = None
        self.current_spot_price = None

        # clear all of the input variables
        self.spot_price_var.set("")
        self.strike_price_var.set("")
        self.iv_var.set("")
        self.new_spot_var.set("")
        self.new_iv_var.set("")

        # reset all of these display labels
        labels_to_reset = [
            self.call_price_label, self.put_price_label, self.straddle_price_label,
            self.delta_label, self.gamma_label, self.vega_label, self.theta_label,
            self.new_straddle_label, self.pnl_long_label, self.pnl_short_label,
            self.new_delta_label, self.new_gamma_label, self.new_vega_label, self.new_theta_label
        ]

        for label in labels_to_reset:
            if "price" in str(label):
                label.config(text="$0.00", foreground="black")
            else:
                if "delta" in str(label) or "gamma" in str(label):
                    label.config(text="0.000", foreground="black")
                else:
                    label.config(text="0.00", foreground="black")


    def fetch_market_data(self):
        if not self.connected:
            messagebox.showerror("Error", "Not Connected to IB TWS")

        ticker = self.ticker_var.get()
        self.log_message(f"Fetching Historical Data for {ticker}")

        # clear any historical data from previous queries
        self.ib_app.historical_data.clear()

        # fetch new historical data
        try:
            # create a contract to query hist data
            contract = self.ib_app.create_equity_contract(symbol=ticker)

            # recieve data
            market_data = self.ib_app.get_historical_data(reqId=99, contract=contract, whatToShow="TRADES")
            self.log_message(f"Historical Data has been recieved for reqID {99}")

            option_data = self.ib_app.get_historical_data(reqId=100, contract=contract, whatToShow="OPTION_IMPLIED_VOLATILITY")
            self.log_message(f"Historical Data has been recieved for reqID {100}")

            # make a df with data and organize it properly
            self.equity_df = pd.DataFrame(market_data)
            self.equity_df['date'] = pd.to_datetime(self.equity_df['date'])
            self.equity_df.set_index('date', inplace=True)

            # fetch the latest bar to get the current spot price of the equity
            latest_bar = self.equity_df.iloc[-1]
            self.current_spot_price = latest_bar['close']
            self.log_message(f"Latest closing price: ${self.current_spot_price:.2f} from {latest_bar.index}")

            # make a df with all options data
            self.option_df = pd.DataFrame(option_data)
            self.option_df['date'] = pd.to_datetime(self.option_df['date'])
            self.option_df.set_index('date', inplace=True)

            # fetch the latest IV
            latest_iv_bar = self.option_df.iloc[-1]
            self.current_iv = latest_iv_bar['close']
            self.current_iv = self.current_iv * np.sqrt(self.vol_annualization)
            self.log_message(f"Latest IV: {self.current_iv: .4f} from {latest_iv_bar.index}")

            # update the input fields
            self.spot_price_var.set(f"{self.current_spot_price: .2f}")
            self.strike_price_var.set(f"{self.current_spot_price: .2f}")        # Will need to manually set this from looking at option chains; for now default to ATM spot price
            self.iv_var.set(f"{self.current_iv*100: .2f}")                      # Convert to percentage

            # calculate the straddle price
            self.price_current_straddle()

        except NoDataError as e:
            self.log_message(e.message)

    def price_current_straddle(self):

        # get all variables needed to calc straddle price; we retrieve them from the input fields incase any have changed at all
        try:
            spot_price = float(self.spot_price_var.get())
            strike_price = float(self.strike_price_var.get())
            iv_percent = float(self.iv_var.get())
            days_to_expiry = int(self.days_to_expiry_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for all parameters")
            return
        
        iv_decimal = iv_percent/100

        T = days_to_expiry/365.0
        r = self.risk_free_rate

        # calculate prices using black scholes
        call_price = black_scholes_call(spot_price, strike_price, T, r, iv_decimal)
        put_price = black_scholes_put(spot_price, strike_price, T, r, iv_decimal)
        straddle_price = call_price + put_price

        # calculate the greeks
        gamma = calculate_gamma(spot_price, strike_price, T, r, iv_decimal)
        vega = calculate_vega(spot_price, strike_price, T, r, iv_decimal) * 2  # call + put vega for straddle

        # delta and theta exposures are the sum of the exposure of the call contract and the put contract for a straddle
        delta = calculate_delta(spot_price, strike_price, T, r, iv_decimal, 'call') + calculate_delta(spot_price, strike_price, T, r, iv_decimal, 'put')        
        theta = calculate_theta(spot_price, strike_price, T, r, iv_decimal, 'call') + calculate_theta(spot_price, strike_price, T, r, iv_decimal, 'put')
        
        # update the pricing displays and the greeks displays
        self.call_price_label.config(text=f"${call_price:.2f}", foreground="green")
        self.put_price_label.config(text=f"${put_price:.2f}", foreground="red")
        self.straddle_price_label.config(text=f"${straddle_price:.2f}", foreground="deep sky blue")
        self.delta_label.config(text=f"{delta:.3f}")
        self.gamma_label.config(text=f"{gamma:.3f}")
        self.vega_label.config(text=f"{vega:.2f}")
        self.theta_label.config(text=f"{theta:.2f}")

        # allow the user to now analyze a scenario
        self.analyze_btn.config(state="normal")

        # for the scenario variables, we are going to defaulty set them to the market data values
        if not self.new_spot_var:
            self.new_spot_var.set(f"{spot_price: .2f}")
        if not self.new_iv_var:
            self.new_iv_var.set(f"{iv_percent: .2f}")

    def analyze_scenario(self):
        
        # get the new scenario vars
        try:
            new_spot = float(self.new_spot_var.get())
            new_iv_dec = float(self.new_iv_var.get())/100.0     # because it is in percent and we need in decimal
        except ValueError:
            messagebox.showerror("Error", "Invalid spot price or IV values")
            return
        
        # get the strike price and days to expiry from market data fields
        try:
            strike_price = float(self.strike_price_var.get())
            days_to_expiry = int(self.days_to_expiry_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid strike price or days to expiry")
            return
        
        T = days_to_expiry / 365.0
        r = self.risk_free_rate

        # calc new option prices
        new_call_price = black_scholes_call(new_spot, strike_price, T, r, new_iv_dec)
        new_put_price = black_scholes_put(new_spot, strike_price, T, r, new_iv_dec)
        new_straddle_price = new_call_price + new_put_price

        # get the og straddle price for pnl calc
        og_straddle_price = float(self.straddle_price_label.cget("text").replace("$", "").strip())

        # calc pnl
        # rmr our position is short straddle so we want new straddle price to be lower than og straddle price which makes pnl long negative and pnl short positive
        pnl_long = new_straddle_price - og_straddle_price
        pnl_short = -pnl_long

        long_color = "green" if pnl_long > 0 else "red"
        short_color = "green" if pnl_short > 0 else "red" 

        # adjust the labels now
        self.new_straddle_label.config(text=f"${new_straddle_price: .2f}", foreground="deep sky blue")
        self.pnl_long_label.config(text=f"${pnl_long:+.2f}", foreground=long_color)
        self.pnl_short_label.config(text=f"${pnl_short:+.2f}", foreground=short_color)

        # calc new greeks 
        new_delta = calculate_delta(new_spot, strike_price, T, r, new_iv_dec, 'call') + calculate_delta(new_spot, strike_price, T, r, new_iv_dec, 'put')
        new_theta = calculate_theta(new_spot, strike_price, T, r, new_iv_dec, 'call') + calculate_theta(new_spot, strike_price, T, r, new_iv_dec, 'put')
        new_vega = calculate_vega(new_spot, strike_price, T, r, new_iv_dec) * 2  # call + put vega
        new_gamma = calculate_gamma(new_spot, strike_price, T, r, new_iv_dec)

        # adjust greek labels
        self.new_delta_label.config(text=f"{new_delta:.3f}")
        self.new_gamma_label.config(text=f"{new_gamma:.3f}")
        self.new_vega_label.config(text=f"{new_vega:.2f}")
        self.new_theta_label.config(text=f"{new_theta:.2f}")

        self.log_message(f"Scenario complete: New price ${new_straddle_price:.2f}, Long P/L ${pnl_long:.2f}, Short P/L ${pnl_short:.2f}")






        
