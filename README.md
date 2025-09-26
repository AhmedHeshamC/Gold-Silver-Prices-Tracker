# Metal Prices Tracker By AHmed Hesham

A robust, object-oriented Python script for fetching live gold (XAU) and silver (XAG) spot prices in USD, converting them to Egyptian Pounds (EGP), and logging historical data with timestamps. Prices are provided both per troy ounce (standard for spot markets) and per gram (common for retail/jewelry). The script uses public APIs for real-time data and appends results to a CSV file for easy analysis in spreadsheets. Designed for periodic runs (e.g., hourly) via cron or similar schedulers.

This project follows SOLID principles, OOP best practices, KISS (Keep It Simple, Stupid), DRY (Don't Repeat Yourself), and clean code standards for maintainability and extensibility. It's lightweight, secure (no API keys required), and fault-tolerant with retries and logging.

## Features

- **Real-Time Data Fetching**: Pulls spot prices from `gold-api.com` (gold/silver in USD per ounce) and exchange rates from `open.er-api.com` (USD to EGP).
- **Dual Units**: Outputs prices per troy ounce and per gram (1 troy ounce = 31.1034768 grams).
- **Currency Conversion**: Automatically converts USD to EGP using live rates.
- **Persistent Logging**:
  - Appends data to `prices_log.csv` (semicolon-delimited for better readability in international locales).
  - Logs summaries and errors to `prices.log`.
- **Console Output**: Formatted table for manual runs (suppressible for background execution).
- **Error Handling**: Retries on API failures (3 attempts), custom exceptions, and graceful degradation.
- **CLI Options**: Supports `--quiet` (for cron/silent runs) and `--test` (mock data for testing).
- **Extensible Architecture**: Modular classes for easy addition of metals, currencies, or storage backends (e.g., database).
- **Scheduling Ready**: Optimized for background runs without console output.

## Requirements

- **Python**: 3.13+ (tested on macOS with zsh; compatible with 3.11+ for timezone features).
- **Dependencies**:
  - `requests` (for HTTP API calls): Install via `pip install requests`.
  - Built-in: `csv`, `argparse`, `datetime`, `abc`, `typing`, `os`.
- **No API Keys**: Uses free, public endpoints (rate-limited; suitable for light use like hourly polling).
- **Environment**: macOS (or Unix-like) for scheduling; works on any OS with Python.

## Setup

1. **Clone/Navigate to Project**:
   ```
   cd /Users/m/Desktop/gt2ndtry  # Or your project root
   ```

2. **Install Dependencies**:
   ```
   pip install requests
   ```

3. **Verify Python**:
   ```
   python3 --version  # Should be 3.13+
   ```

4. **Initial Run** (creates files):
   ```
   python3 metal_prices_tracker.py
   ```
   - This fetches live data, creates `prices_log.csv` and `prices.log`, and prints a table.

5. **Test Mode** (no APIs; uses mock data):
   ```
   python3 metal_prices_tracker.py --test
   ```

## Usage

### Manual Execution
Run the script to fetch current prices and display them:
```
python3 metal_prices_tracker.py
```
After displaying the prices, the script will prompt:
```
Would you like to save these prices? (y/n):
```
- If you enter `y`, the prices are saved to both `prices_log.csv` and `prices.log`.
- If you enter `n`, the script exits without saving and greets you.
- If you run with `--quiet` (e.g., via cron), the script always saves without prompting.
- **Output Example** (console table and prompt):
  ```
  === Latest Prices ===
  Timestamp: 2025-09-26T01:42:15.123456
  Metal      USD (oz)     EGP (oz)    USD (g)      EGP (g)     
  Gold      $   3743.50   180177.16   $  120.35    5789.12
  Silver    $     44.99     2165.30   $    1.45      69.62
  ====================

  Would you like to save these prices? (y/n):
  ```

  Data appended to prices_log.csv. Open in a spreadsheet for full table view.
  ```
- **CSV Structure** (`prices_log.csv`; semicolon-delimited):
  ```
  timestamp (UTC);gold_usd_per_ounce;silver_usd_per_ounce;gold_egp_per_ounce;silver_egp_per_ounce;gold_usd_per_gram;silver_usd_per_gram;gold_egp_per_gram;silver_egp_per_gram
  2025-09-26T01:42:15.123456;3743.50;44.99;180177.16;2165.30;120.35;1.45;5789.12;69.62
  ```
  - Open in Excel/Google Sheets: Import > Separator: Semicolon > Format columns as currency.
- **Log File** (`prices.log`): Appends summaries like:
  ```
  [2025-09-26T01:42:15.123456] Gold (oz/g): $3743.50/$120.35 USD, E£180177.16/5789.12 EGP | Silver (oz/g): $44.99/$1.45 USD, E£2165.30/69.62 EGP
  ```
  - Only saved if you answer `y` to the prompt, or always in `--quiet` mode.

### CLI Options
- `--quiet`: Suppress console output and always save prices (ideal for cron/background; no prompt).
  ```
  python3 metal_prices_tracker.py --quiet
  ```
- `--test`: Run with mock data (no network calls).
  ```
  python3 metal_prices_tracker.py --test --quiet
  ```
- Help: `python3 metal_prices_tracker.py --help`

### Scheduling (Hourly Background Runs)
Use cron (macOS built-in) for automation. Ensures your Mac is on/awake.

1. **Edit Crontab**:
   ```
   crontab -e
   ```

2. **Add Hourly Job** (runs at :00 of every hour):
   ```
   0 * * * * cd /Users/m/Desktop/gt2ndtry && /usr/bin/python3 metal_prices_tracker.py --quiet
   ```
   - **Customization**:
     - Every 30 mins: `*/30 * * * * ...`
     - Log output: Add `>> prices.log 2>&1` (though script logs internally).
     - Full Python path: `/usr/bin/python3` avoids "command not found".
   - Save/exit (vim: `:wq`; nano: Ctrl+O > Enter > Ctrl+X).

3. **Verify**:
   - List jobs: `crontab -l`
   - Test command: Run the full cron line manually in Terminal.
   - Monitor: `tail -f prices.log` (view live appends).

4. **Keep Mac Awake** (if it sleeps):
   - Install `caffeinate` (built-in): Prefix with `caffeinate -t 300` (wakes 5 mins per run).
   ```
   0 * * * * cd /Users/m/Desktop/gt2ndtry && caffeinate -t 300 /usr/bin/python3 metal_prices_tracker.py --quiet
   ```

For always-on (e.g., server), consider Launchd (macOS plist) or cloud (AWS Lambda + EventBridge).

## Architecture

The script is refactored for OOP and SOLID principles:
- **Config**: Centralizes settings (e.g., URLs, precision).
- **ApiFetcher (Base)**: Handles HTTP sessions/retries (DRY).
- **MetalPriceFetcher/ExchangeRateFetcher**: Specific API logic (SRP; extensible).
- **PriceConverter**: Pure functions for unit/currency conversion (testable).
- **DataLogger**: Manages CSV/log output (semicolon-delimited for readability).
- **PriceTracker**: Orchestrates workflow (Dependency Inversion: injects abstractions).
- **Factory (`create_tracker`)**: Builds dependencies (high-level module).

Data Flow: Fetch (APIs) → Convert (math) → Log (CSV/Log). ~200 lines; easy to unit-test (e.g., mock fetchers).

Extensibility: Add metals (subclass `MetalPriceFetcher`), currencies (new fetcher), or storage (e.g., SQLite via new `DataLogger`).

## Troubleshooting

- **"python3: command not found"**: Use `python` or install Python 3.13+. On macOS, install via Homebrew: `brew install python@3.13`.
- **API Errors** (e.g., "Unexpected format"):
  - Check internet; APIs may be down/rate-limited.
  - View `prices.log` for details.
  - Test endpoints: `curl https://api.gold-api.com/price/XAU`.
- **CSV Readability Issues**: Import in spreadsheet with semicolon delimiter. Older runs (pre-ounce) may have blank columns—harmless.
- **Cron Not Running**:
  - Verify path: Use absolute paths.
  - Check logs: `grep CRON /var/log/system.log` (macOS).
  - Permissions: Ensure script is executable (`chmod +x metal_prices_tracker.py`).
- **Deprecation Warnings**: None in 3.13+; uses `timezone.utc`.
- **High Volume**: Free APIs limit ~1,500 req/month—hourly is fine (~720/month). For more, add keys or cache rates.
- **Mock Dates (2025)**: From gold-api demo; switch APIs for production timestamps.

If issues persist, run with `--quiet false` and share console/log output.

## Contributing

Fork the repo, make changes (e.g., add tests with pytest), and submit a PR. Focus on SOLID adherence and docs.

## License

MIT License.

---
