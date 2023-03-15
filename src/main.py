"""Bitcoin capital gains calculator."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas
from pandas import DataFrame


class Transaction:
    """A BTCUSD transaction."""

    def __init__(self, timestamp: datetime, btc: float, usd: float):
        self._timestamp = timestamp
        self._btc = Decimal(str(btc))
        self._usd = Decimal(str(usd))

    @property
    def timestamp(self):
        """Returns the transaction timestamp."""
        return self._timestamp

    @property
    def btc(self):
        """Returns the transactions BTC amount."""
        return self._btc

    @property
    def usd(self):
        """Returns the transactions USD amount."""
        return self._usd

    @property
    def price(self) -> Decimal:
        """Returns the BTCUSD price of the transaction."""
        return abs(self.usd / self.btc)

    def __eq__(self, other: "Transaction"):
        if self is other:
            return True

        return (
            self.timestamp == other.timestamp
            and self.btc == other.btc
            and self.usd == other.usd
        )

    def __repr__(self):
        classname = type(self).__name__
        timestamp = f"timestamp='{self.timestamp.isoformat()}'"
        btc = f"btc={self.btc}"
        usd = f"usd={self.usd}"

        return f"{classname}({timestamp}, {btc}, {usd})"


class Buy(Transaction):
    """A BTCUSD buy transaction."""

    def __init__(self, timestamp, btc, usd):
        if btc < 0:
            raise ValueError("BTC value must be positive for a buy.")
        if usd > 0:
            raise ValueError("USD value must be negative for a buy.")

        super().__init__(timestamp, btc, usd)


class Sell(Transaction):
    """A BTCUSD sell transaction."""

    def __init__(self, timestamp, btc, usd):
        if btc > 0:
            raise ValueError("BTC value must be negative for a sell.")
        if usd < 0:
            raise ValueError("USD value must be positive for a sell.")

        super().__init__(timestamp, btc, usd)


def read_gemini_input(path: Path) -> DataFrame:
    """Returns a transaction dataframe from a Gemini transaction history."""

    columns = {
        "Date": "timestamp",
        "Type": "type",
        "USD Amount USD": "usd",
        "BTC Amount BTC": "btc",
    }
    tx_types = ("Buy", "Sell")

    dataframe = pandas.read_excel(path, usecols=columns.keys())
    dataframe = dataframe.rename(columns=columns)
    dataframe = dataframe.loc[dataframe["type"].isin(tx_types)]
    dataframe = dataframe.sort_values(by=["timestamp"])

    return dataframe


def get_buys(input_df: DataFrame):
    """Returns a list of buy transactions from the input dataframe."""
    return [
        Buy(r.timestamp, r.btc, r.usd)
        for r in input_df.itertuples()
        if r.type == "Buy"
    ]


def get_sells(input_df: DataFrame):
    """Returns a list of sell transactions from the input dataframe."""
    return [
        Sell(r.timestamp, r.btc, r.usd)
        for r in input_df.itertuples()
        if r.type == "Sell"
    ]


def change_strategy(buys: list[Buy], strategy: str):
    """Sorts the buy list according to the desired calculation strategy."""

    if strategy == "first_in_first_out":
        buys.sort(key=lambda b: b.timestamp, reverse=True)

    elif strategy == "last_in_first_out":
        buys.sort(key=lambda b: b.timestamp, reverse=False)

    elif strategy == "most_expensive_first_out":
        buys.sort(key=lambda b: b.price, reverse=False)

    elif strategy == "least_expensive_first_out":
        buys.sort(key=lambda b: b.price, reverse=True)
