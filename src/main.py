"""Bitcoin capital gains calculator."""

import argparse
import csv
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from pprint import pprint

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
        return self.usd / self.btc

    def split(self, split_btc: Decimal) -> tuple["Transaction", "Transaction"]:
        """Splits the transaction at the btc amount and returns two new
        Transaction objects.
        """
        split_usd = split_btc * self.price
        remainder_btc = self.btc - split_btc
        remainder_usd = self.usd - split_usd

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
    sells = [
        Sell(r.timestamp, r.btc, r.usd)
        for r in input_df.itertuples()
        if r.type == "Sell"
    ]
    return sorted(sells, key=lambda s: s.timestamp)


def change_strategy(buys: list[Buy], strategy: str):
    """Sorts the buy list according to the desired calculation strategy."""

    if strategy == "first_in_first_out":
        buys.sort(key=lambda b: b.timestamp, reverse=True)

    elif strategy == "last_in_first_out":
        buys.sort(key=lambda b: b.timestamp, reverse=False)

    elif strategy == "most_expensive_first_out":
        buys.sort(key=lambda b: abs(b.price), reverse=False)

    elif strategy == "least_expensive_first_out":
        buys.sort(key=lambda b: abs(b.price), reverse=True)

    else:
        raise ValueError(f"Unknown strategy: '{strategy}'")


def pop_buys(buys: list[Buy], timestamp: datetime, btc: Decimal):
    """Pops buys from the buy list up to the btc amount."""

    popped = []

    while btc:
        pbuy = buys.pop()

        if btc >= pbuy.btc:
            popped.append(pbuy)
            btc -= pbuy.btc

        elif btc < pbuy.btc:
            split, remainder = pbuy.split(btc)
            popped.append(split)
            buys.append(remainder)
            btc -= split.btc

    return popped


def split_sell(sell: Sell, buys: list[Buy]):
    """Splits a sell transaction according to its matched buys."""

    assert sell.btc == -sum(b.btc for b in buys), "BTC amount must match."

    sells = []

    for buy in buys:
        split, sell = sell.split(-buy.btc)
        sells.append(split)

    return sells


def match_capital_gains(sells: list[Sell], buys: list[Buy]):
    """Matches up sell transactions to buy transactions for capital gains."""

    sell_vol = sum(s.btc for s in sells)
    buy_vol = sum(b.btc for b in buys)

    assert sell_vol < buy_vol, "Cannot sell more BTC than what was bought."

    cap_gains = []

    for sell in sells:
        print(sell)
        pbuys = pop_buys(buys, -sell.btc)
        print(pbuys)
        cap_gains += [
            CapitalGain(b, s) for b, s in zip(pbuys, split_sell(sell, pbuys))
        ]

    pprint(buys)

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
    buys = get_buys(gemini_input)
    sells = get_sells(gemini_input)

    change_strategy(buys, "last_in_first_out")

    cap_gains = match_capital_gains(sells, buys)
    short, long = tabulate(cap_gains)

    write_capital_gains(output_path, short, long)
