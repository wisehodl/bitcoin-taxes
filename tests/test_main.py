"""Tests for bitcoin capital gains calculator."""

import shutil
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pandas import DataFrame

from main import (
    Buy,
    Sell,
    Transaction,
    change_strategy,
    get_buys,
    get_sells,
    read_gemini_input,
)

TEST_INPUTS_PATH = Path("tests/input/")


def test_tx_decimal():
    """A transaction should hold amounts as Decimal objects."""

    txn = Transaction(datetime.now(), 1.23, 2.34)
    assert txn.btc == Decimal("1.23")
    assert txn.usd == Decimal("2.34")


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


@pytest.fixture(name="gemini_buys")
def gemini_buys_fixture():
    """Returns the buys from the gemini transaction input."""

    return [
        Buy(datetime(2020, 6, 23, 20, 42, 26, 889000), 1, -5),
        Buy(datetime(2020, 6, 24, 16, 13, 54), 2, -10),
    ]


@pytest.fixture(name="gemini_sells")
def gemini_sells_fixture():
    """Returns the sells from the gemini transaction input."""

    return [
        Sell(datetime(2020, 6, 23, 20, 45, 3, 979000), -1, 5),
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


def test_get_buys(gemini_input_df, gemini_buys):
    """Should extract buy transactions from the input dataframe."""

    buys = get_buys(gemini_input_df)
    assert buys == gemini_buys


def test_get_sells(gemini_input_df, gemini_sells):
    """Should extract sell transactions from the input dataframe."""

    sells = get_sells(gemini_input_df)
    assert sells == gemini_sells


def test_change_strat_first_in_first_out():
    """Should sort the buys for a first-in-first-out strategy."""

    buys = [
        Buy(datetime(2020, 1, 2), 1, -1),
        Buy(datetime(2020, 1, 1), 1, -1),
        Buy(datetime(2020, 1, 3), 1, -1),
    ]

    change_strategy(buys, "first_in_first_out")
    assert buys == [
        Buy(datetime(2020, 1, 3), 1, -1),
        Buy(datetime(2020, 1, 2), 1, -1),
        Buy(datetime(2020, 1, 1), 1, -1),
    ]


def test_change_strat_last_in_first_out():
    """Should sort the buys for a last-in-first-out strategy."""

    buys = [
        Buy(datetime(2020, 1, 2), 1, -1),
        Buy(datetime(2020, 1, 1), 1, -1),
        Buy(datetime(2020, 1, 3), 1, -1),
    ]

    change_strategy(buys, "last_in_first_out")
    assert buys == [
        Buy(datetime(2020, 1, 1), 1, -1),
        Buy(datetime(2020, 1, 2), 1, -1),
        Buy(datetime(2020, 1, 3), 1, -1),
    ]


def test_change_strat_most_expensive_first_out():
    """Should sort the buys for a most-expensive-first-out strategy."""

    buys = [
        Buy(datetime(2020, 1, 2), 1, -10),
        Buy(datetime(2020, 1, 1), 1, -1),
        Buy(datetime(2020, 1, 3), 1, -100),
    ]

    change_strategy(buys, "most_expensive_first_out")
    assert buys == [
        Buy(datetime(2020, 1, 1), 1, -1),
        Buy(datetime(2020, 1, 2), 1, -10),
        Buy(datetime(2020, 1, 3), 1, -100),
    ]


def test_change_strat_least_expensive_first_out():
    """Should sort the buys for a least-expensive-first-out strategy."""

    buys = [
        Buy(datetime(2020, 1, 2), 1, -10),
        Buy(datetime(2020, 1, 1), 1, -1),
        Buy(datetime(2020, 1, 3), 1, -100),
    ]

    change_strategy(buys, "least_expensive_first_out")
    assert buys == [
        Buy(datetime(2020, 1, 3), 1, -100),
        Buy(datetime(2020, 1, 2), 1, -10),
        Buy(datetime(2020, 1, 1), 1, -1),
    ]
