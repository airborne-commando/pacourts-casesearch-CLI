# PA Court Case Search Tool

A Python script for searching Pennsylvania court cases by participant name, with optional filtering by docket type. Built with Selenium for web automation and Pandas for data export.

## Features

- Search by participant name (first and last)
- Filter by county (automatically determined from ZIP code)
- Optional docket type filtering (Civil, Criminal, Traffic, etc.)
- CSV export of search results
- Logging of all activities
- Both file-based and manual input modes

## Installation

### Prerequisites

- Python 3.7+
- Google Chrome installed

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/airborne-commando/pacourts-casesearch-CLI.git
   cd pacourts-casesearch-CLI
   ```

2. Install dependencies:
   ```
   pip install selenium pandas webdriver-manager
   ```

3. Prepare your input file (optional):
   ```
   # Format: ZIP,LastName,FirstName[,DocketType]
   19107,Smith,John,Traffic
   19104,Doe,Jane,Criminal
   ```

## Usage

### File Mode
```
python casesearch.py
# Select option 1 and provide file path
```

### Manual Mode
```
python casesearch.py
# Select option 2 and enter searches in format: ZIP,LastName,FirstName[,DocketTypeOrNumber]
# Example: 19107,Smith,John,2 (where 2 = Criminal)
```

### Available Docket Types
1. Civil
2. Criminal 
3. Landlord/Tenant
4. Miscellaneous
5. Non-Traffic
6. Summary Appeal
7. Traffic

## Output

Results are saved in CSV format to the `case_results/` directory with timestamps. Example filename:
```
Smith_John_PHILADELPHIA_Traffic_20230815_142356.csv
```

## Configuration

Edit the script to:
- Enable headless mode (uncomment `--headless`)
- Change default wait times
- Modify logging behavior

## Troubleshooting

**Common issues:**
- ChromeDriver version mismatch: Update Chrome or use `webdriver-manager`
- No results: Verify county mapping for your ZIP codes

---

*Note: Use this tool in compliance with the [PA Judiciary's terms of service](https://ujsportal.pacourts.us).*
