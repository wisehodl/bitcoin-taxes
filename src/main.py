"""Bitcoin capital gains calculator."""

import argparse
import csv
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path

import pandas
from dateutil import parser
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
        return self.usd / self.btc

    def split(self, split_btc: Decimal) -> tuple["Transaction", "Transaction"]:
        """Splits the transaction at the btc amount and returns two new
        Transaction objects.
        """
        split_usd = split_btc * self.price
        remainder_btc = self.btc - split_btc
        remainder_usd = self.usd - split_usd

        if abs(remainder_usd) <= Decimal("0.0001"):
            remainder_usd = Decimal("0")

        return type(self)(self.timestamp, split_btc, split_usd), type(self)(
            self.timestamp, remainder_btc, remainder_usd
        )

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
            raise ValueError(
                f"BTC value must be positive for a buy. Got: {timestamp}, {btc}"
            )
        if usd > 0:
            raise ValueError(
                f"USD value must be negative for a buy. Got: {timestamp} {usd}"
            )

        super().__init__(timestamp, btc, usd)


class Sell(Transaction):
    """A BTCUSD sell transaction."""

    def __init__(self, timestamp, btc, usd):
        if btc > 0:
            raise ValueError(
                f"BTC value must be negative for a sell. Got: {timestamp} {btc}"
            )
        if usd < 0:
            raise ValueError(
                f"USD value must be positive for a sell. Got: {timestamp} {usd}"
            )

        super().__init__(timestamp, btc, usd)


class Duration(Enum):
    """Duration for a capital gain."""

    SHORT = "Short"
    LONG = "Long"


class CapitalGain:
    """A buy/sell transaction pair for capital gains calculation."""

    def __init__(self, buy: Buy, sell: Sell):
        self._buy = buy
        self._sell = sell

    @property
    def buy(self):
        return self._buy

    @property
    def sell(self):
        return self._sell

    @property
    def duration(self):
        """Returns the duration category of the capital gain."""

        sts = self.sell.timestamp
        adjusted_sell_timestamp = datetime(
            sts.year - 1,
            sts.month,
            sts.day,
            sts.hour,
            sts.minute,
            sts.second,
            sts.microsecond,
            tzinfo=sts.tzinfo,
        )

        if self.buy.timestamp < adjusted_sell_timestamp:
            return Duration.LONG

        return Duration.SHORT

    @property
    def gain(self):
        """Returns the net profit (or loss) of the capital gain."""
        return self.sell.usd + self.buy.usd

    def __eq__(self, other: "CapitalGain"):
        if self is other:
            return True

        return self.buy == other.buy and self.sell == other.sell

    def __repr__(self):
        return f"CapitalGain({self.buy}, {self.sell})"


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
    dataframe["timestamp"] = pandas.to_datetime(
        dataframe["timestamp"]
    ).dt.tz_localize("UTC")
    dataframe = dataframe.sort_values(by=["timestamp"])

    return dataframe


def read_swan_input(path: Path) -> DataFrame:
    """Returns a transaction dataframe from a Swan transaction history."""

    columns = {
        "Date": "timestamp",
        "Event": "type",
        "Total USD": "usd",
        "Unit Count": "btc",
    }

    dataframe = pandas.read_csv(path, usecols=columns.keys(), skiprows=2)
    dataframe = dataframe.rename(columns=columns)
    dataframe = dataframe.loc[dataframe["type"] == "purchase"]
    dataframe["timestamp"] = pandas.to_datetime(dataframe["timestamp"])
    dataframe["type"] = dataframe["type"].str.replace("purchase", "Buy")
    dataframe["usd"] *= -1
    dataframe = dataframe.sort_values(by=["timestamp"])

    return dataframe


def read_cashapp_input(path: Path) -> DataFrame:
    """Returns a transaction dataframe from a Cash App transaction history."""

    columns = {
        "Date": "timestamp",
        "Transaction Type": "type",
        "Amount": "usd",
        "Asset Amount": "btc",
    }

    dataframe = pandas.read_csv(path, usecols=columns.keys())
    dataframe = dataframe.rename(columns=columns)

    dataframe = dataframe.loc[
        dataframe["type"].isin(("Bitcoin Buy", "Bitcoin Sale"))
    ]
    dataframe["timestamp"] = [
        parser.parse(ts) if pandas.notna(ts) else pandas.NaT
        for ts in dataframe["timestamp"]
    ]
    dataframe["timestamp"] = dataframe["timestamp"].dt.tz_convert("UTC")
    dataframe["type"] = dataframe["type"].str.replace("Bitcoin Buy", "Buy")
    dataframe["type"] = dataframe["type"].str.replace("Bitcoin Sale", "Sell")

    dataframe["usd"] = (
        dataframe["usd"].str.replace("$", "").str.replace(",", "").astype(float)
    )
    dataframe.loc[dataframe["type"] == "Sell", "btc"] *= -1
    dataframe = dataframe.sort_values(by=["timestamp"])

    return dataframe


def get_transactions(input_df: DataFrame):
    """Returns a list of transactions from the input dataframe"""
    tx_cls = {"Buy": Buy, "Sell": Sell}
    return [
        tx_cls[r.type](r.timestamp, r.btc, r.usd) for r in input_df.itertuples()
    ]


def has_sell(transactions: list[Transaction]):
    """Returns True if there is a Sell in the transaction list."""
    return any(isinstance(t, Sell) for t in transactions)


def next_sell_index(transactions: list[Transaction]):
    """Returns the index of the first Sell in the transaction list."""

    for index, transaction in enumerate(transactions):
        if isinstance(transaction, Sell):
            return index

    return None


def extract_sell(transactions: list[Transaction], sell_index: int):
    """Extracts the sell transaction and its matching buy transactions
    according to a last-in-first-out strategy.
    """

    assert isinstance(
        transactions[sell_index], Sell
    ), "Transaction at `sell_index` must be a Sell."

    sell = transactions.pop(sell_index)
    buy_index = sell_index - 1

    buys = []
    btc = -sell.btc

    while btc:
        pbuy = transactions.pop(buy_index)

        if btc < pbuy.btc:
            split, remainder = pbuy.split(btc)
            buys.append(split)
            transactions.insert(buy_index, remainder)
            btc -= split.btc
        else:
            buys.append(pbuy)
            buy_index -= 1
            btc -= pbuy.btc

    return sell, buys


def split_sell(sell: Sell, buys: list[Buy]):
    """Splits a sell transaction according to its matched buys."""

    assert sell.btc == -sum(b.btc for b in buys), "BTC amount must match."

    sells = []

    for buy in buys:
        split, sell = sell.split(-buy.btc)
        sells.append(split)

    return sells


def match_capital_gains(transactions: list[Transaction]):
    """Matches up sell transactions to buy transactions for capital gains."""

    sell_vol = sum(s.btc for s in transactions if isinstance(s, Sell))
    buy_vol = sum(b.btc for b in transactions if isinstance(b, Buy))

    assert sell_vol < buy_vol, "Cannot sell more BTC than what was bought."

    cap_gains = []

    while has_sell(transactions):
        sell_index = next_sell_index(transactions)
        sell, buys = extract_sell(transactions, sell_index)
        cap_gains += [
            CapitalGain(b, s) for b, s in zip(buys, split_sell(sell, buys))
        ]

    return cap_gains


def tabulate(cap_gains: list[CapitalGain]):
    """Sorts capital gains into long and short durations and by year and
    formats capital gain information into table rows for reporting.
    """

    table = {
        Duration.SHORT: {},
        Duration.LONG: {},
    }

    for gain in cap_gains:
        duration = gain.duration
        year = gain.sell.timestamp.year

        description = f"{gain.buy.btc:.8f} BTC"
        date_acquired = gain.buy.timestamp.strftime("%m/%d/%Y")
        date_sold = gain.sell.timestamp.strftime("%m/%d/%Y")
        proceeds = f"{gain.sell.usd:.2f}"
        cost_basis = f"{abs(gain.buy.usd):.2f}"
        gains = f"{gain.gain:.2f}"

        if not table[duration].get(year):
            table[duration].update({year: []})

        table[duration][year].append(
            (description, date_acquired, date_sold, proceeds, cost_basis, gains)
        )

    return table[Duration.SHORT], table[Duration.LONG]


def write_capital_gains(
    output: Path, short: dict[int, list[tuple]], long: dict[int, list[tuple]]
):
    """Writes the capital gains to csv files in the output directory."""

    header = [
        "Description of Property",
        "Date Acquired",
        "Date Sold or Disposed Of",
        "Proceeds (Sales Price)",
        "Cost or Other Basis",
        "Gain or (loss)",
    ]

    for year, rows in short.items():
        file_path = output / f"{year}_short_gains.csv"
        with open(file_path, "w", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(header)
            for row in rows:
                writer.writerow(row)

    for year, rows in long.items():
        file_path = output / f"{year}_long_gains.csv"
        with open(file_path, "w", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(header)
            for row in rows:
                writer.writerow(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="bcg", description="Bitcoin Capital Gains Calculator"
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Input file directory."
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output file directory."
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    gemini_input = read_gemini_input(input_path / "gemini.xlsx")
    swan_input = read_swan_input(input_path / "swan.csv")
    cashapp_input = read_cashapp_input(input_path / "cashapp.csv")
    transactions_ = (
        get_transactions(gemini_input)
        + get_transactions(swan_input)
        + get_transactions(cashapp_input)
    )
    transactions_.sort(key=lambda tx: tx.timestamp)

    cap_gains_ = match_capital_gains(transactions_)
    short, long = tabulate(cap_gains_)

    write_capital_gains(output_path, short, long)
