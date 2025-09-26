import argparse
import csv
import os
from abc import ABC
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class Config:
    """Holds configuration constants (injected for testability)."""

    CSV_FILE = "prices_log.csv"
    LOG_FILE = "prices.log"
    GOLD_API_URL = "https://api.gold-api.com/price/XAU"
    SILVER_API_URL = "https://api.gold-api.com/price/XAG"
    EXCHANGE_API_URL = "https://open.er-api.com/v6/latest/USD"
    OUNCE_TO_GRAM = 31.1034768  # Troy ounce to grams conversion
    PRECISION_OUNCE = 2  # Decimal places for ounce prices
    PRECISION_GRAM = 4  # Decimal places for gram prices


class ApiError(Exception):
    """Custom exception for API-related errors."""

    pass


class ApiFetcher(ABC):
    """Abstract base for API fetchers (SRP: handles HTTP with retries)."""

    def __init__(self, base_url: str, config: Config):
        self.base_url = base_url
        self.config = config
        self.session = self._setup_session()

    def _setup_session(self) -> requests.Session:
        """Shared session setup with retries (DRY)."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session


class MetalPriceFetcher(ApiFetcher):
    """Fetches metal prices (O: extensible for more metals)."""

    def __init__(self, config: Config):
        super().__init__("", config)  # No single base URL; use instance URLs

    def fetch_gold(self) -> float:
        """Fetch gold price in USD per troy ounce."""
        return self._fetch_price(self.config.GOLD_API_URL)

    def fetch_silver(self) -> float:
        """Fetch silver price in USD per troy ounce."""
        return self._fetch_price(self.config.SILVER_API_URL)

    def _fetch_price(self, url: str) -> float:
        """Internal: Fetch and parse price (DRY across metals)."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            if "price" in data:
                return float(data["price"])
            raise ApiError(f"Unexpected format: {data}")
        except requests.RequestException as e:
            raise ApiError(f"HTTP error for {url}: {e}")


class ExchangeRateFetcher(ApiFetcher):
    """Fetches exchange rates (SRP: currency-specific)."""

    def __init__(self, config: Config):
        super().__init__(config.EXCHANGE_API_URL, config)

    def fetch_usd_to_egp(self) -> float:
        """Fetch USD to EGP rate."""
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            data = response.json()
            if data.get("result") == "success" and "rates" in data:
                return data["rates"]["EGP"]
            raise ApiError(f"Unexpected format: {data}")
        except requests.RequestException as e:
            raise ApiError(f"HTTP error: {e}")


class PriceConverter:
    """Converts prices (SRP: pure transformation, no I/O)."""

    def __init__(self, config: Config):
        self.config = config

    def to_gram(self, usd_per_ounce: float) -> float:
        """Convert USD per ounce to per gram."""
        return usd_per_ounce / self.config.OUNCE_TO_GRAM

    def to_egp(self, usd_price: float, rate: float) -> float:
        """Convert USD price to EGP using rate."""
        return usd_price * rate


class DataLogger:
    """Handles data persistence (SRP: CSV and log writing)."""

    def __init__(self, config: Config):
        self.config = config

    def log(
        self,
        timestamp: str,
        gold_usd_oz: float,
        silver_usd_oz: float,
        gold_egp_oz: float,
        silver_egp_oz: float,
        gold_usd_g: float,
        silver_usd_g: float,
        gold_egp_g: float,
        silver_egp_g: float,
        quiet: bool = False,
    ) -> None:
        """Append to CSV and log file (DRY: unified entry point)."""
        self._append_to_csv(
            timestamp,
            gold_usd_oz,
            silver_usd_oz,
            gold_egp_oz,
            silver_egp_oz,
            gold_usd_g,
            silver_usd_g,
            gold_egp_g,
            silver_egp_g,
        )
        self._append_to_log(
            timestamp,
            gold_usd_oz,
            silver_usd_oz,
            gold_egp_oz,
            silver_egp_oz,
            gold_usd_g,
            silver_usd_g,
            gold_egp_g,
            silver_egp_g,
            quiet,
        )

    def _append_to_csv(
        self,
        timestamp: str,
        gold_usd_oz: float,
        silver_usd_oz: float,
        gold_egp_oz: float,
        silver_egp_oz: float,
        gold_usd_g: float,
        silver_usd_g: float,
        gold_egp_g: float,
        silver_egp_g: float,
    ) -> None:
        """Append row to CSV (semicolon-delimited)."""
        file_exists = os.path.isfile(self.config.CSV_FILE)
        with open(self.config.CSV_FILE, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file, delimiter=";")
            if not file_exists:
                writer.writerow(
                    [
                        "timestamp (UTC)",
                        "gold_usd_per_ounce",
                        "silver_usd_per_ounce",
                        "gold_egp_per_ounce",
                        "silver_egp_per_ounce",
                        "gold_usd_per_gram",
                        "silver_usd_per_gram",
                        "gold_egp_per_gram",
                        "silver_egp_per_gram",
                    ]
                )
            writer.writerow(
                [
                    timestamp,
                    f"{gold_usd_oz:.{self.config.PRECISION_OUNCE}f}",
                    f"{silver_usd_oz:.{self.config.PRECISION_OUNCE}f}",
                    f"{gold_egp_oz:.{self.config.PRECISION_OUNCE}f}",
                    f"{silver_egp_oz:.{self.config.PRECISION_OUNCE}f}",
                    f"{gold_usd_g:.{self.config.PRECISION_GRAM}f}",
                    f"{silver_usd_g:.{self.config.PRECISION_GRAM}f}",
                    f"{gold_egp_g:.{self.config.PRECISION_GRAM}f}",
                    f"{silver_egp_g:.{self.config.PRECISION_GRAM}f}",
                ]
            )

    def _append_to_log(
        self,
        timestamp: str,
        gold_usd_oz: float,
        silver_usd_oz: float,
        gold_egp_oz: float,
        silver_egp_oz: float,
        gold_usd_g: float,
        silver_usd_g: float,
        gold_egp_g: float,
        silver_egp_g: float,
        quiet: bool,
    ) -> None:
        """Append summary to log file; print table if not quiet."""
        log_entry = (
            f"[{timestamp}] Gold (oz/g): ${gold_usd_oz:.{self.config.PRECISION_OUNCE}f}/${gold_usd_g:.{self.config.PRECISION_GRAM}f} USD, "
            f"E£{gold_egp_oz:.{self.config.PRECISION_OUNCE}f}/{gold_egp_g:.{self.config.PRECISION_GRAM}f} EGP | "
            f"Silver (oz/g): ${silver_usd_oz:.{self.config.PRECISION_OUNCE}f}/${silver_usd_g:.{self.config.PRECISION_GRAM}f} USD, "
            f"E£{silver_egp_oz:.{self.config.PRECISION_OUNCE}f}/{silver_egp_g:.{self.config.PRECISION_GRAM}f} EGP\n"
        )
        with open(self.config.LOG_FILE, "a", encoding="utf-8") as log:
            log.write(log_entry)

        if not quiet:
            print("\n=== Latest Prices ===")
            print(f"Timestamp: {timestamp}")
            print(
                f"{'Metal':<10} {'USD (oz)':<12} {'EGP (oz)':<12} {'USD (g)':<12} {'EGP (g)':<12}"
            )
            print(
                f"{'Gold':<10} ${gold_usd_oz:>10.{self.config.PRECISION_OUNCE}f}  E£{gold_egp_oz:>10.{self.config.PRECISION_OUNCE}f}  ${gold_usd_g:>10.{self.config.PRECISION_GRAM}f}  E£{gold_egp_g:>10.{self.config.PRECISION_GRAM}f}"
            )
            print(
                f"{'Silver':<10} ${silver_usd_oz:>10.{self.config.PRECISION_OUNCE}f}  E£{silver_egp_oz:>10.{self.config.PRECISION_OUNCE}f}  ${silver_usd_g:>10.{self.config.PRECISION_GRAM}f}  E£{silver_egp_g:>10.{self.config.PRECISION_GRAM}f}"
            )
            print("====================\n")
            print(
                f"Data appended to {self.config.CSV_FILE}. Open in a spreadsheet for full table view."
            )


class PriceTracker:
    """Orchestrates price tracking (DIP: depends on abstractions)."""

    def __init__(
        self,
        config: Config,
        metal_fetcher: MetalPriceFetcher,
        rate_fetcher: ExchangeRateFetcher,
        converter: PriceConverter,
        logger: DataLogger,
    ):
        self.config = config
        self.metal_fetcher = metal_fetcher
        self.rate_fetcher = rate_fetcher
        self.converter = converter
        self.logger = logger

    def run(self, quiet: bool = False) -> None:
        """Execute the full workflow: fetch, convert, log."""
        try:
            # Fetch
            gold_usd_oz = self.metal_fetcher.fetch_gold()
            silver_usd_oz = self.metal_fetcher.fetch_silver()
            rate = self.rate_fetcher.fetch_usd_to_egp()

            # Convert to EGP per ounce
            gold_egp_oz = gold_usd_oz * rate
            silver_egp_oz = silver_usd_oz * rate

            # Convert to per gram
            gold_usd_g = self.converter.to_gram(gold_usd_oz)
            silver_usd_g = self.converter.to_gram(silver_usd_oz)
            gold_egp_g = self.converter.to_egp(gold_usd_g, rate)
            silver_egp_g = self.converter.to_egp(silver_usd_g, rate)

            # Log
            timestamp = datetime.now(timezone.utc).isoformat()
            self.logger.log(
                timestamp,
                gold_usd_oz,
                silver_usd_oz,
                gold_egp_oz,
                silver_egp_oz,
                gold_usd_g,
                silver_usd_g,
                gold_egp_g,
                silver_egp_g,
                quiet,
            )

        except ApiError as e:
            self._handle_error(e, quiet)
        except Exception as e:
            self._handle_error(e, quiet)

    def _handle_error(self, error: Exception, quiet: bool) -> None:
        """Centralized error handling (clean: one place)."""
        timestamp = datetime.now(timezone.utc).isoformat()
        error_msg = f"[{timestamp}] Error: {error}\n"
        if not quiet:
            print(error_msg, end="")
        with open(self.config.LOG_FILE, "a", encoding="utf-8") as log:
            log.write(error_msg)


def create_tracker(config: Config) -> PriceTracker:
    """Factory: Creates tracker with dependencies (DIP: high-level module)."""
    metal_fetcher = MetalPriceFetcher(config)
    rate_fetcher = ExchangeRateFetcher(config)
    converter = PriceConverter(config)
    logger = DataLogger(config)
    return PriceTracker(config, metal_fetcher, rate_fetcher, converter, logger)


def main():
    """CLI entrypoint (KISS: simple parser)."""
    parser = argparse.ArgumentParser(
        description="Track gold/silver prices per ounce and gram."
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress console output (for cron)."
    )
    parser.add_argument("--test", action="store_true", help="Run test mode.")
    args = parser.parse_args()

    config = Config()
    tracker = create_tracker(config)

    if args.test:
        # Test: Mock data (no APIs) - ounce first, then gram
        timestamp = datetime.now(timezone.utc).isoformat()
        tracker.logger.log(
            timestamp,
            2000.00,
            25.00,
            96260.00,
            1203.25,
            64.28,
            0.80,
            3092.50,
            38.50,
            args.quiet,
        )
        if not args.quiet:
            print("Test log completed. Check prices_log.csv and prices.log")
    else:
        tracker.run(args.quiet)


if __name__ == "__main__":
    main()
