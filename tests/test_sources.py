"""Source transformation tests."""

import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pandas import DataFrame

from btax import (
    Buy,
    Sell,
    get_transactions,
    transform_cashapp_data,
    transform_gemini_data,
    transform_swan_data,
)

TEST_INPUTS_PATH = Path("tests/input/")


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
                datetime(2020, 6, 23, 20, 42, 26, 889000, tzinfo=timezone.utc),
                datetime(2020, 6, 23, 20, 45, 3, 979000, tzinfo=timezone.utc),
                datetime(2020, 6, 24, 16, 13, 54, tzinfo=timezone.utc),
                datetime(2020, 8, 17, 14, 13, 24, 948000, tzinfo=timezone.utc),
                datetime(2021, 6, 8, 15, 4, 56, 840000, tzinfo=timezone.utc),
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
        Buy(
            datetime(2020, 6, 23, 20, 42, 26, 889000, tzinfo=timezone.utc),
            1,
            -5,
        ),
        Sell(
            datetime(2020, 6, 23, 20, 45, 3, 979000, tzinfo=timezone.utc), -1, 5
        ),
        Buy(datetime(2020, 6, 24, 16, 13, 54, tzinfo=timezone.utc), 2, -10),
        Sell(
            datetime(2020, 8, 17, 14, 13, 24, 948000, tzinfo=timezone.utc),
            -2,
            10,
        ),
        Sell(
            datetime(2021, 6, 8, 15, 4, 56, 840000, tzinfo=timezone.utc), -3, 15
        ),
    ]


def test_transform_gemini_data(gemini_input, gemini_input_df):
    """Should read Gemini transaction history into buys and sells."""

    dataframe = transform_gemini_data(gemini_input)
    expected = gemini_input_df

    assert dataframe["timestamp"].tolist() == expected["timestamp"].tolist()
    assert dataframe["type"].tolist() == expected["type"].tolist()
    assert dataframe["usd"].tolist() == expected["usd"].tolist()
    assert dataframe["btc"].tolist() == expected["btc"].tolist()


def test_transform_swan_data(swan_input, swan_input_df):
    """Should read Swan transaction history into buys and sells."""

    dataframe = transform_swan_data(swan_input)
    expected = swan_input_df

    assert dataframe["timestamp"].tolist() == expected["timestamp"].tolist()
    assert dataframe["type"].tolist() == expected["type"].tolist()
    assert dataframe["usd"].tolist() == expected["usd"].tolist()
    assert dataframe["btc"].tolist() == expected["btc"].tolist()


def test_transform_cashapp_data(cashapp_input, cashapp_input_df):
    """Should read Cash App transaction history into buys and sells."""

    dataframe = transform_cashapp_data(cashapp_input)
    expected = cashapp_input_df

    assert dataframe["timestamp"].tolist() == expected["timestamp"].tolist()
    assert dataframe["type"].tolist() == expected["type"].tolist()
    assert dataframe["usd"].tolist() == expected["usd"].tolist()
    assert dataframe["btc"].tolist() == expected["btc"].tolist()


def test_get_transactions(gemini_input_df, gemini_transactions):
    """Should extract  transactions from the input dataframe."""

    transactions = get_transactions(gemini_input_df)
    assert transactions == gemini_transactions
