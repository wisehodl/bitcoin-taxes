"""Tests for bitcoin capital gains calculator."""

from datetime import datetime

from btax import (
    Buy,
    CapitalGain,
    Duration,
    Sell,
    Strategy,
    extract_sell,
    has_sell,
    match_capital_gains,
    next_sell_index,
    split_sell,
)


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
    sell, buys = extract_sell(transactions, index, Strategy.LIFO)

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
