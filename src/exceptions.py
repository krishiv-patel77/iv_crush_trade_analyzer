class NoDataError(Exception):
    """ Raised when there is either no data or not enough data to do a given operation """
    def __init__(self, message="Not Enough Data"):
        self.message = f"No Data Error: {message}"
        super().__init__(self.message)

class ConnectionError(Exception):
    """ Raised when there is an error connecting with IB TWS"""

    def __init__(self, _func: str, _file: str, message="Could not connect to IB TWS"):
        self.message = f"Connection Error | loc: ({_func}, {_file}) | {message}"
        super().__init__(self.message)