# Wikidata Extractor

Professional tool for extracting settlement data from Wikidata API using SPARQL queries. Supports flexible configuration of data fields and filters with CSV export functionality.

## Features

- 🌍 **Settlement data extraction** by country from Wikidata
- 📋 **Flexible configuration** - customizable data fields and filters  
- 🔄 **SPARQL Query Builder** - automatic generation of optimized queries
- 📊 **CSV export** - configurable formatting and output options
- 📦 **Batch processing** - efficient handling of large datasets
- ⚡ **Rate limiting** - respects Wikidata API limits (60 req/min)
- 🛡️ **Error handling** - robust error handling with retry logic
- 🎯 **CLI interface** - easy command-line usage

## Installation

### Requirements
- Python 3.7+
- Internet connection

### Installation Steps
```bash
# 1. Clone the repository
git clone https://github.com/yourusername/wikidata-extractor.git
cd wikidata-extractor

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test connection
python3 main.py configs/czech_cities.yaml --test-connection
```

## Quick Start

### 1. Basic Usage
```bash
# Extract Czech cities to CSV
python3 main.py configs/czech_cities.yaml

# Output: ./output/czech_cities.csv
```

### 2. View Generated SPARQL Query
```bash
python3 main.py configs/czech_cities.yaml --dry-run --verbose
```

### 3. Save SPARQL Query to File
```bash
python3 main.py configs/czech_cities.yaml --save-query my_query.sparql --dry-run
```

### 4. Batch Processing
```bash
# Enable batch processing for large datasets
python3 main.py configs/uk_settlements_complete.yaml --batch --batch-size 500
```

## Configuration

### Basic Configuration File (YAML)

```yaml
# Target country
country:
  wikidata_id: "Q213"           # Czech Republic
  name: "Czech Republic"
  language_codes: ["cs", "en"]

# Settlement types
settlement_types:
  include: ["Q515", "Q3957"]    # cities and towns

# Data fields to extract
data_fields:
  - field: "item_id"
    required: true
    csv_header: "wikidata_id"
    
  - field: "name"
    wikidata_property: "rdfs:label"
    required: true
    csv_header: "name"
    
  - field: "coordinates"
    wikidata_property: "P625"
    csv_header: "latitude,longitude"
    format: "lat_lon_split"

# Output configuration
output:
  filename: "czech_cities.csv"
  directory: "./output"

# Batch processing (optional)
query:
  batch_processing:
    enabled: true
    batch_size: 1000
    max_results: 10000
```

### Wikidata Properties for Settlements

| Property | Description | Example |
|----------|-------------|---------|
| P625 | GPS coordinates | 50.0755,14.4378 |
| P281 | Postal code | 110 00 |
| P1937 | NUTS code | CZ010 |
| P782 | LAU code | CZ0100 |
| P1082 | Population | 1324277 |
| P131 | Administrative territory | Region |

### Wikidata Entity Types for Settlements

| Entity ID | Type | Description |
|-----------|------|-------------|
| Q515 | city | Urban settlement |
| Q3957 | town | Small city/town |
| Q532 | village | Rural settlement |
| Q486972 | human settlement | Generic settlement type |

## Usage Examples

### 1. Czech Cities with Coordinates
```yaml
# configs/czech_cities_coords.yaml
country:
  wikidata_id: "Q213"

settlement_types:
  include: ["Q515"]

data_fields:
  - field: "item_id"
    required: true
  - field: "name"
    wikidata_property: "rdfs:label"
    required: true
  - field: "coordinates"
    wikidata_property: "P625"
    required: true
    format: "lat_lon_split"

filters:
  coordinates_required: true

output:
  filename: "czech_cities_coords.csv"
```

### 2. Slovak Settlements with Population
```yaml
# configs/slovakia_population.yaml
country:
  wikidata_id: "Q214"
  name: "Slovakia"
  language_codes: ["sk", "cs", "en"]

data_fields:
  - field: "item_id"
    required: true
  - field: "name"
    wikidata_property: "rdfs:label"
    required: true
    language: "sk"
  - field: "population"
    wikidata_property: "P1082"
    csv_header: "population"

filters:
  population:
    min: 10000

output:
  filename: "slovakia_large_cities.csv"
  date_suffix: true
```

### 3. German Cities with Complete Data
```yaml
# configs/germany_complete.yaml
country:
  wikidata_id: "Q183"
  name: "Germany" 
  language_codes: ["de", "en"]

settlement_types:
  include: ["Q515", "Q3957"]

data_fields:
  - field: "item_id"
    required: true
  - field: "name"
    wikidata_property: "rdfs:label"
    required: true
  - field: "coordinates"
    wikidata_property: "P625"
    format: "lat_lon_split"
  - field: "postal_code"
    wikidata_property: "P281"
  - field: "nuts_code"
    wikidata_property: "P1937"
  - field: "population"
    wikidata_property: "P1082"

query:
  batch_processing:
    enabled: true
    batch_size: 1000
    max_results: 5000

output:
  filename: "germany_cities.csv"
  encoding: "utf-8"
```

## CLI Parameters

```bash
python3 main.py <config_file> [options]
```

### Available Parameters

| Parameter | Description |
|-----------|-------------|
| `--test-connection` | Test connection to Wikidata API only |
| `--dry-run` | Show query without executing it |
| `--save-query FILE` | Save SPARQL query to file |
| `--verbose` | Detailed output with diagnostics |
| `--batch` | Enable batch processing (overrides config) |
| `--batch-size N` | Batch size for batch processing |
| `--max-results N` | Maximum number of results |
| `--help` | Show help message |

### Command Examples

```bash
# Test connection
python3 main.py configs/czech_cities.yaml --test-connection

# Show query without execution
python3 main.py configs/czech_cities.yaml --dry-run --verbose

# Save query and execute
python3 main.py configs/czech_cities.yaml --save-query backup.sparql --verbose

# Batch processing with custom size
python3 main.py configs/uk_settlements_complete.yaml --batch --batch-size 500 --max-results 2000

# Display generated query only
python3 main.py configs/czech_cities.yaml --dry-run
```

## Output Formats

### CSV Output
```csv
wikidata_id,name,latitude,longitude,postal_code
Q8385,Ostrava,49.835555555,18.2925,700 00
Q14960,Brno,49.195277777,16.608333333,602 00
Q1085,Praha,50.0833,14.4667,110 00
```

### Coordinate Formatting Options
- `lat_lon_split`: Split into two columns (latitude, longitude)
- `point`: Keep "Point(lon lat)" format
- `wkt`: Well-Known Text format

## Advanced Configuration

### Filters
```yaml
filters:
  coordinates_required: true    # Only settlements with GPS coordinates
  population:
    min: 50000                 # Minimum population
    max: 1000000               # Maximum population
```

### API Settings
```yaml
api:
  timeout: 60                  # Timeout in seconds
  retry_attempts: 5            # Number of retry attempts
  retry_delay: 10              # Delay between retries
  rate_limit: 30               # Requests per minute
```

### Query Optimization
```yaml
query:
  limit: 5000                  # Result limit
  batch_processing:
    enabled: true              # Enable batch processing
    batch_size: 1000           # Batch size
    max_results: 10000         # Maximum total results
  enable_service_timeout: true # Use SERVICE label optimization
```

## Troubleshooting

### Common Errors

**🔸 "Invalid Wikidata ID"**
```
✗ Configuration error: Invalid Wikidata ID: INVALID_ID
```
- **Solution**: Use Q[number] format, e.g., Q213 for Czech Republic

**🔸 "Query timeout"**
```
✗ Wikidata API error: Query timed out after all attempts
```
- **Solution**: Increase `api.timeout` or enable batch processing with smaller `batch_size`

**🔸 "Rate limit exceeded"**
```
Rate limiting: waiting 1.23s
```
- **Normal**: Automatic throttling to respect API limits

**🔸 "Large dataset issues"**
```
✗ Query too complex or dataset too large
```
- **Solution**: Enable batch processing and set reasonable `max_results`

### Debug Mode
```bash
python3 main.py config.yaml --verbose
```

### SPARQL Query Inspection
```bash
python3 main.py config.yaml --save-query debug.sparql --dry-run
```

## Frequently Used Countries

| Country | Wikidata ID | Code |
|---------|-------------|------|
| Czech Republic | Q213 | CZ |
| Slovakia | Q214 | SK |
| Germany | Q183 | DE |
| Austria | Q40 | AT |
| Poland | Q36 | PL |
| Hungary | Q28 | HU |
| United Kingdom | Q145 | GB |
| Netherlands | Q55 | NL |

## Project Structure

```
wikidata-extractor/
├── src/                       # Source code
│   ├── __init__.py
│   ├── config_manager.py      # Configuration management
│   ├── query_builder.py       # SPARQL query building
│   ├── wikidata_client.py     # Wikidata API client
│   ├── csv_exporter.py        # CSV export functionality
│   └── data_grouper.py        # Data grouping utilities
├── configs/                   # Configuration files
│   ├── czech_cities.yaml     # Czech Republic example
│   ├── slovakia_complete.yaml # Slovakia complete data
│   ├── germany_cities.yaml   # German cities
│   ├── uk_settlements_complete.yaml # UK settlements
│   ├── netherlands_settlements.yaml # Dutch settlements
│   ├── test_minimal.yaml     # Minimal test configuration
│   └── test_advanced.yaml    # Advanced test configuration
├── output/                    # Generated CSV files
│   ├── czech_cities.csv
│   ├── uk_settlements_complete.csv
│   └── ...
├── main.py                    # Main script
├── requirements.txt           # Python dependencies
├── analysis.md               # Project analysis
└── README.md                 # This documentation
```

## Available Configurations

The project includes several pre-configured examples:

- **czech_cities.yaml** - Czech cities and towns
- **slovakia_complete.yaml** - Complete Slovak settlements
- **germany_cities.yaml** - German cities
- **uk_settlements_complete.yaml** - UK settlements with complete data
- **netherlands_settlements.yaml** - Dutch settlements
- **test_minimal.yaml** - Basic testing configuration
- **test_advanced.yaml** - Advanced testing with filters

## Performance Considerations

- **Batch Processing**: For large datasets (>1000 results), enable batch processing
- **Rate Limiting**: Automatic throttling respects Wikidata API limits
- **Memory Efficient**: Streaming processing for large datasets
- **Configurable Timeouts**: Adjustable timeouts for different network conditions

## License and Support

Project created for data extraction and analysis purposes. Open for educational and research use.

For technical support or bug reports, please create an issue in the GitHub repository.