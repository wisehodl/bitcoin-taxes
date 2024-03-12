"""Tests for bitcoin capital gains calculator."""

import csv
import shutil
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from pandas import DataFrame

from main import (
    Buy,
    CapitalGain,
    Duration,
    Sell,
    Transaction,
    extract_sell,
    get_transactions,
    has_sell,
    match_capital_gains,
    next_sell_index,
    read_cashapp_input,
    read_gemini_input,
    read_swan_input,
    split_sell,
    tabulate,
    write_capital_gains,
)

TEST_INPUTS_PATH = Path("tests/input/")


def test_tx_decimal():
    """A transaction should hold amounts as Decimal objects."""

    txn = Transaction(datetime.now(), 1.23, 2.34)
    assert txn.btc == Decimal("1.23")
    assert txn.usd == Decimal("2.34")


def test_split_sell_tx():
    """Should be able to split a sell transaction at a btc amount."""

    timestamp = datetime.now()
    root = Sell(timestamp, -1, 1)
    split, remainder = root.split(Decimal("-0.4"))

    assert split == Sell(timestamp, -0.4, 0.4)
    assert remainder == Sell(timestamp, -0.6, 0.6)


def test_split_buy_tx():
    """Should be able to split a buy transaction at a btc amount."""

    timestamp = datetime.now()
    root = Buy(timestamp, 1, -1)
    split, remainder = root.split(Decimal("0.4"))

    assert split == Buy(timestamp, 0.4, -0.4)
    assert remainder == Buy(timestamp, 0.6, -0.6)


def test_sell_tx():
    """A sell transaction can only have a positive usd and negative btc."""

    with pytest.raises(ValueError, match="USD"):
        Sell(datetime.now(), -1, -1)

    with pytest.raises(ValueError, match="BTC"):
        Sell(datetime.now(), 1, 1)


def test_buy_tx():
    """A buy transaction can only have a positive usd and negative btc."""

    with pytest.raises(ValueError, match="BTC"):
        Buy(datetime.now(), -1, -1)

    with pytest.raises(ValueError, match="USD"):
        Buy(datetime.now(), 1, 1)


@pytest.fixture(scope="function", name="gemini_input")
def gemini_input_fixture(tmp_path: Path) -> Path:
    """Provides a minimal gemini transaction history file path."""

    filename = "gemini.xlsx"
    shutil.copy2(TEST_INPUTS_PATH / filename, tmp_path)

    return tmp_path / filename


@pytest.fixture(scope="function", name="swan_input")
def swan_input_fixture(tmp_path: Path) -> Path:
    """Provides a minimal swan transaction history file path."""

    filename = "swan.csv"
    shutil.copy2(TEST_INPUTS_PATH / filename, tmp_path)

    return tmp_path / filename


@pytest.fixture(scope="function", name="cashapp_input")
def cashapp_input_fixture(tmp_path: Path) -> Path:
    """Provides a minimal cashapp transaction history file path."""

    filename = "cashapp.csv"
    shutil.copy2(TEST_INPUTS_PATH / filename, tmp_path)

    return tmp_path / filename


@pytest.fixture(name="gemini_input_df")
def gemini_input_dataframe_fixture():
    """Returns a sample transaction input dataframe."""

    return DataFrame(
        data={
            "timestamp": [
                datetime(2020, 6, 23, 20, 42, 26, 889000),
                datetime(2020, 6, 23, 20, 45, 3, 979000),
                datetime(2020, 6, 24, 16, 13, 54),
                datetime(2020, 8, 17, 14, 13, 24, 948000),
                datetime(2021, 6, 8, 15, 4, 56, 840000),
            ],
            "type": ["Buy", "Sell", "Buy", "Sell", "Sell"],
            "usd": [-5, 5, -10, 10, 15],
            "btc": [1, -1, 2, -2, -3],
        }
    )


@pytest.fixture(name="swan_input_df")
def swan_input_dataframe_fixture():
    """Returns a sample transaction input dataframe."""

    return DataFrame(
        data={
            "timestamp": [
                datetime(2023, 6, 13, 15, 27, 27, tzinfo=timezone.utc),
                datetime(2023, 11, 14, 13, 34, 17, tzinfo=timezone.utc),
            ],
            "type": ["Buy", "Buy"],
            "usd": [-900.0, -500.0],
            "btc": [0.0347969, 0.01362289],
        }
    )


@pytest.fixture(name="cashapp_input_df")
def cashapp_input_dataframe_fixture():
    """Returns a sample transaction input dataframe."""

    return DataFrame(
        data={
            "timestamp": [
                datetime(2023, 10, 31, 18, 27, 3, tzinfo=timezone.utc),
                datetime(2023, 11, 9, 22, 14, 26, tzinfo=timezone.utc),
                datetime(2023, 12, 21, 22, 17, 14, tzinfo=timezone.utc),
                datetime(2023, 12, 25, 14, 53, 19, tzinfo=timezone.utc),
            ],
            "type": ["Sell", "Buy", "Buy", "Sell"],
            "usd": [24.99, -1967.95, -871.84, 5500],
            "btc": [-0.00072675, 0.05365757, 0.01983945, -0.12656005],
        }
    )


@pytest.fixture(name="gemini_transactions")
def gemini_txs_fixture():
    """Returns the transactions from the gemini input."""

    return [
        Buy(datetime(2020, 6, 23, 20, 42, 26, 889000), 1, -5),
        Sell(datetime(2020, 6, 23, 20, 45, 3, 979000), -1, 5),
        Buy(datetime(2020, 6, 24, 16, 13, 54), 2, -10),
        Sell(datetime(2020, 8, 17, 14, 13, 24, 948000), -2, 10),
        Sell(datetime(2021, 6, 8, 15, 4, 56, 840000), -3, 15),
    ]


def test_read_gemini_input(gemini_input, gemini_input_df):
    """Should read Gemini transaction history into buys and sells."""

    dataframe = read_gemini_input(gemini_input)
    expected = gemini_input_df

    assert dataframe["timestamp"].tolist() == expected["timestamp"].tolist()
    assert dataframe["type"].tolist() == expected["type"].tolist()
    assert dataframe["usd"].tolist() == expected["usd"].tolist()
    assert dataframe["btc"].tolist() == expected["btc"].tolist()


def test_read_swan_input(swan_input, swan_input_df):
    """Should read Swan transaction history into buys and sells."""

    dataframe = read_swan_input(swan_input)
    expected = swan_input_df

    assert dataframe["timestamp"].tolist() == expected["timestamp"].tolist()
    assert dataframe["type"].tolist() == expected["type"].tolist()
    assert dataframe["usd"].tolist() == expected["usd"].tolist()
    assert dataframe["btc"].tolist() == expected["btc"].tolist()


def test_read_cashapp_input(cashapp_input, cashapp_input_df):
    """Should read Cash App transaction history into buys and sells."""

    dataframe = read_cashapp_input(cashapp_input)
    expected = cashapp_input_df

    assert dataframe["timestamp"].tolist() == expected["timestamp"].tolist()
    assert dataframe["type"].tolist() == expected["type"].tolist()
    assert dataframe["usd"].tolist() == expected["usd"].tolist()
    assert dataframe["btc"].tolist() == expected["btc"].tolist()


def test_get_transactions(gemini_input_df, gemini_transactions):
    """Should extract  transactions from the input dataframe."""

    transactions = get_transactions(gemini_input_df)
    assert transactions == gemini_transactions


def test_has_sell():
    """Should return whether the transaction list has a Sell in it."""

    transactions = [Buy(datetime.now(), 1, -1)]
    assert has_sell(transactions) is False

    transactions.append(Sell(datetime.now(), -1, 1))
    assert has_sell(transactions) is True


def test_next_sell_index():
    """Should return the index of the next sell transaction."""
    transactions = [
        Buy(datetime.now(), 1, -1),
        Sell(datetime.now(), -1, 1),
        Sell(datetime.now(), -1, 1),
    ]
    assert next_sell_index(transactions) == 1


def test_no_next_sell():
    """Should return None if there are no sells in the transactions."""
    transactions = [
        Buy(datetime.now(), 1, -1),
        Buy(datetime.now(), 1, -1),
    ]
    assert next_sell_index(transactions) is None


def test_extract_sell():
    """Should extract the sell and its matching buys."""

    transactions = [
        Buy(datetime(2020, 1, 1), 1, -1),
        Buy(datetime(2020, 1, 2), 1, -1),
        Sell(datetime(2020, 1, 3), -1.5, 15),
        Buy(datetime(2020, 1, 4), 1, -1),
    ]
    index = next_sell_index(transactions)
    sell, buys = extract_sell(transactions, index)

    assert sell == Sell(datetime(2020, 1, 3), -1.5, 15)
    assert buys == [
        Buy(datetime(2020, 1, 2), 1, -1),
        Buy(datetime(2020, 1, 1), 0.5, -0.5),
    ]
    assert transactions == [
        Buy(datetime(2020, 1, 1), 0.5, -0.5),
        Buy(datetime(2020, 1, 4), 1, -1),
    ]


def test_split_sell():
    """Should split a sell transaction according to its matched buys."""

    sell = Sell(datetime(2021, 1, 1), -3, 30)
    buys = [
        Buy(datetime(2020, 1, 1), 1, -1),
        Buy(datetime(2020, 1, 2), 0.5, -0.5),
        Buy(datetime(2020, 1, 3), 1.5, -1.5),
    ]

    sells = split_sell(sell, buys)

    assert sells == [
        Sell(datetime(2021, 1, 1), -1, 10),
        Sell(datetime(2021, 1, 1), -0.5, 5),
        Sell(datetime(2021, 1, 1), -1.5, 15),
    ]


def test_match_capital_gains():
    """Should match up buys to sells as cap gain pairs."""

    transactions = [
        Buy(datetime(2020, 1, 1), 20, -20),
        Sell(datetime(2020, 6, 1), -5, 50),
        Buy(datetime(2021, 1, 1), 10, -10),
        Sell(datetime(2021, 6, 1), -15, 150),
        Buy(datetime(2022, 1, 1), 10, -10),
        Sell(datetime(2023, 6, 1), -10, 100),
    ]

    cap_gains = match_capital_gains(transactions)

    assert cap_gains == [
        CapitalGain(
            Buy(datetime(2020, 1, 1), 5, -5),
            Sell(datetime(2020, 6, 1), -5, 50),
        ),
        CapitalGain(
            Buy(datetime(2021, 1, 1), 10, -10),
            Sell(datetime(2021, 6, 1), -10, 100),
        ),
        CapitalGain(
            Buy(datetime(2020, 1, 1), 5, -5),
            Sell(datetime(2021, 6, 1), -5, 50),
        ),
        CapitalGain(
            Buy(datetime(2022, 1, 1), 10, -10),
            Sell(datetime(2023, 6, 1), -10, 100),
        ),
    ]

    assert transactions == [
        Buy(datetime(2020, 1, 1), 10, -10),
    ]


def test_capital_gain_long_duration():
    """Should detect if a capital gain is long"""

    cap_gain = CapitalGain(
        Buy(datetime(2020, 1, 1), 1, -1), Sell(datetime(2021, 6, 1), -1, 10)
    )
    assert cap_gain.duration == Duration.LONG


def test_capital_gain_short_duration():
    """Should detect if a capital gain is short"""

    cap_gain = CapitalGain(
        Buy(datetime(2020, 1, 1), 1, -1), Sell(datetime(2020, 6, 1), -1, 10)
    )
    assert cap_gain.duration == Duration.SHORT


def test_capital_gain_short_duration_exact_year():
    """Should detect that a capital gain is short if the duration is exactly
    one year.
    """

    cap_gain = CapitalGain(
        Buy(datetime(2020, 1, 1), 1, -1), Sell(datetime(2021, 1, 1), -1, 10)
    )
    assert cap_gain.duration == Duration.SHORT


def test_capital_gain_gain():
    """Should calculate the gain of the capital gain."""

    cap_gain = CapitalGain(
        Buy(datetime(2020, 1, 1), 1, -1), Sell(datetime(2020, 1, 2), -1, 10)
    )

    assert cap_gain.gain == 9


def test_tabulate():
    """Should tabulate the capital gains for tax reporting by year."""

    cap_gains = [
        CapitalGain(
            Buy(datetime(2020, 1, 1), 1, -1),
            Sell(datetime(2020, 6, 1), -1, 10),
        ),
        CapitalGain(
            Buy(datetime(2020, 1, 2), 10, -10),
            Sell(datetime(2021, 6, 1), -10, 200),
        ),
        CapitalGain(
            Buy(datetime(2021, 1, 1), 1.5, -50),
            Sell(datetime(2021, 6, 1), -1.5, 10),
        ),
        CapitalGain(
            Buy(datetime(2021, 1, 2), 1.12345678, -50),
            Sell(datetime(2022, 6, 1), -1.12345678, 25),
        ),
    ]

    short, long = tabulate(cap_gains)

    assert short == {
        2020: [
            (
                "1.00000000 BTC",
                "01/01/2020",
                "06/01/2020",
                "10.00",
                "1.00",
                "9.00",
            ),
        ],
        2021: [
            (
                "1.50000000 BTC",
                "01/01/2021",
                "06/01/2021",
                "10.00",
                "50.00",
                "-40.00",
            ),
        ],
    }

    assert long == {
        2021: [
            (
                "10.00000000 BTC",
                "01/02/2020",
                "06/01/2021",
                "200.00",
                "10.00",
                "190.00",
            ),
        ],
        2022: [
            (
                "1.12345678 BTC",
                "01/02/2021",
                "06/01/2022",
                "25.00",
                "50.00",
                "-25.00",
            ),
        ],
    }


def test_write_capital_gains(tmp_path):
    """Should write capital gains to csv files."""

    short = {
        2020: [
            (
                "1.00000000 BTC",
                "01/01/2020",
                "06/01/2020",
                "10.00",
                "1.00",
                "9.00",
            ),
        ],
        2021: [
            (
                "1.50000000 BTC",
                "01/01/2021",
                "06/01/2021",
                "10.00",
                "50.00",
                "-40.00",
            ),
        ],
    }

    long = {
        2021: [
            (
                "10.00000000 BTC",
                "01/02/2020",
                "06/01/2021",
                "200.00",
                "10.00",
                "190.00",
            ),
        ],
        2022: [
            (
                "1.12345678 BTC",
                "01/02/2021",
                "06/01/2022",
                "25.00",
                "50.00",
                "-25.00",
            ),
        ],
    }

    write_capital_gains(tmp_path, short, long)

    files = [
        tmp_path / "2020_short_gains.csv",
        tmp_path / "2021_short_gains.csv",
        tmp_path / "2021_long_gains.csv",
        tmp_path / "2022_long_gains.csv",
    ]

    for file in files:
        assert file.exists()

    with open(files[0], "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        assert "Proceeds (Sales Price)" in next(reader)
        assert "1.00000000 BTC" in next(reader)

    with open(files[1], "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        assert "Proceeds (Sales Price)" in next(reader)
        assert "1.50000000 BTC" in next(reader)

    with open(files[2], "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        assert "Proceeds (Sales Price)" in next(reader)
        assert "10.00000000 BTC" in next(reader)

    with open(files[3], "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        assert "Proceeds (Sales Price)" in next(reader)
        assert "1.12345678 BTC" in next(reader)
