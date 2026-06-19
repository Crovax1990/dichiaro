"""Registry of supported tax years."""

SUPPORTED_YEARS = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]


def supported_years() -> list[int]:
    return sorted(SUPPORTED_YEARS)
