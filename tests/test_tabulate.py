"""Transaction tabulation tests."""

from datetime import datetime

from btax import Buy, CapitalGain, Sell, tabulate


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
