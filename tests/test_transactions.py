"""Transaction structure tests."""

from datetime import datetime
from decimal import Decimal

import pytest

from btax import Buy, Sell, Transaction


def test_tx_decimal():
    """A transaction should hold amounts as Decimal objects."""

    txn = Transaction(datetime.now(), 1.23, 2.34)
    assert txn.btc == Decimal("1.23")
    assert txn.usd == Decimal("2.34")


def test_split_sell_tx():
    """Should be able to split a sell transaction at a btc amount."""

    timestamp = datetime.now()
    root = Sell(timestamp, -1, 1)
    split, rebtaxder = root.split(Decimal("-0.4"))

    assert split == Sell(timestamp, -0.4, 0.4)
    assert rebtaxder == Sell(timestamp, -0.6, 0.6)


def test_split_buy_tx():
    """Should be able to split a buy transaction at a btc amount."""

    timestamp = datetime.now()
    root = Buy(timestamp, 1, -1)
    split, rebtaxder = root.split(Decimal("0.4"))

    assert split == Buy(timestamp, 0.4, -0.4)
    assert rebtaxder == Buy(timestamp, 0.6, -0.6)


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
