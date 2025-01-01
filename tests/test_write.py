"""Output write tests."""

import csv

from btax import write_capital_gains


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
