from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import BarData
from typing import Dict, List
import time
import threading
from datetime import datetime

from src.exceptions import NoDataError, ConnectionError

class IBApp(EClient, EWrapper):
    def __init__(self):
        # We want to initialize the EClient with the self meaning current instance of IBApp because we need to give it access to our instance of EWrapper
        # This is because EClient is responsible for sending requests to the IB Server over the TCP Socket and the IB Server needs to know where to send the response to (ie EWrapper)
        EClient.__init__(self, self)

        self.connected = False
        self.historical_data: Dict[int, List]= {}

    def nextValidId(self, orderId):
        self.connected = True
        print(f"Connected to IB TWS")

    def error(self, reqId, errorCode, errorString, *args):
        # Filter out irrelevant warnings
        if errorCode == 2176 and "fractional share" in errorString.lower():
            return
        print(f"Error reqId: {reqId} | {errorCode}: {errorString}")

    def create_equity_contract(self, symbol: str):
        """ Function for creating a contract for a given equity symbol with all required params """

        contract = Contract()
        contract.symbol = symbol.upper()
        contract.secType = "STK"    # Stock
        contract.exchange = "SMART" 
        contract.currency = "USD"

        return contract

    def get_historical_data(self, reqId: int, contract: Contract, whatToShow:str):
        """ This is our request function for historical data """
        
        if reqId not in self.historical_data:
            self.historical_data[reqId] = []

        end_date = datetime.now()

        self.reqHistoricalData(
            reqId=reqId,
            contract=contract,
            endDateTime=end_date.strftime("%Y%m%d %H:%M:%S"),
            durationStr="3 D",
            barSizeSetting="1 min",
            whatToShow=whatToShow,
            useRTH=1,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )

        # Wait for the data | 15 seconds
        timeout = 15
        start_time = time.time()

        while self.historical_data[reqId] == [] and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if len(self.historical_data[reqId]) > 0:
            # Note that if the server responds, the only way this reqId key will be populated is if historicalData overriden method is called by the server
            return self.historical_data[reqId]
        else:
            raise NoDataError(f"No Historical Data Recieved for reqId {reqId}")
        

    def historicalData(self, reqId: int, bar: BarData):
        """ 
        This function overrides an EWrapper callback for handling the server response to our historical data request 
        
        Here, we can define how to organize the data we recieve from the server

        This function will not be directly called ever; if you want historical data, you call the get_historical_data function
        """

        self.historical_data[reqId].append({
            "date": bar.date ,
            "open": bar.open,
            "close": bar.close,
            "high": bar.high,
            "low": bar.low,
            "volume": bar.volume
        })

    def historicalDataEnd(self, reqId, start, end):
        print(f"Historical Data has been recieved for reqID {reqId}")

        
    def connect_ib(self, host: str, port: str):
        
        try:
            port = int(port)

            def connect_thread():
                try:
                    self.connect(host, port, clientId=1)
                    self.run()
                except Exception as e:
                    raise ConnectionError(_func="connect_ib", _file="ib_client")
                
            thread = threading.Thread(target=connect_thread, daemon=True)
            thread.start()

            # Wait for connection
            timeout = 15
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if self.connected:
                try:
                    server_version = self.serverVersion()
                    return server_version
                except Exception as e:
                    raise ConnectionError(_func="connect_ib", _file="ib_client",
                                          message=f"Connection established but couldn't get server version | {e}")
            else:
                return None

        except Exception as e:
            raise ConnectionError(_func="connect_ib", _file="ib_client", message=f"{e}")

    def disconnect_ib(self):
        try:
            self.disconnect()
        except Exception as e:
            raise ConnectionError(_func="disconnect_ib", _file="ib_client", message=f"{e}")



