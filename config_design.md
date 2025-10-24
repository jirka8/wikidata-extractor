# Návrh konfiguračního systému

## Struktura konfiguračního souboru (YAML)

### Kompletní konfigurační schéma
```yaml
# Základní metadata konfigurace
metadata:
  name: "Czech Cities Extraction"
  description: "Extract all cities and towns from Czech Republic"
  version: "1.0"
  created: "2024-10-24"

# Definice země pro dotaz
country:
  wikidata_id: "Q213"        # Povinné: Wikidata ID země
  name: "Czech Republic"      # Volitelné: lidsky čitelný název
  language_codes: ["cs", "en"] # Preferované jazyky pro labels

# Typ sídel k extrakci
settlement_types:
  include:
    - "Q515"    # city
    - "Q3957"   # town  
    - "Q532"    # village
    - "Q486972" # human settlement (obecné)
  exclude: []   # Volitelně vyloučit specifické typy

# Definice datových polí k extrakci
data_fields:
  - field: "item_id"
    wikidata_property: null    # Speciální: Wikidata entity ID
    required: true
    csv_header: "wikidata_id"
    
  - field: "name" 
    wikidata_property: "rdfs:label"
    required: true
    csv_header: "name"
    language: "cs"             # Preferovaný jazyk
    
  - field: "coordinates"
    wikidata_property: "P625"  # coordinate location
    required: false
    csv_header: "lat,lon"
    format: "lat_lon_split"    # lat,lon | point | wkt
    
  - field: "postal_code"
    wikidata_property: "P281"
    required: false
    csv_header: "postal_code"
    
  - field: "nuts_code"
    wikidata_property: "P1937"
    required: false  
    csv_header: "nuts"
    
  - field: "lau_code"
    wikidata_property: "P782"
    required: false
    csv_header: "lau"
    
  - field: "population"
    wikidata_property: "P1082"
    required: false
    csv_header: "population"
    qualifier_latest: true     # Vezmi nejnovější hodnotu

# Filtry a omezení
filters:
  population:
    min: null                 # Minimální počet obyvatel
    max: null                 # Maximální počet obyvatel
  
  coordinates_required: false  # Pouze sídla s GPS souřadnicemi
  
  administrative_level:       # Filtr podle administrativní úrovně
    min_level: null
    max_level: null

# Nastavení výstupu
output:
  filename: "czech_settlements.csv"
  directory: "./output"
  delimiter: ","
  encoding: "utf-8"
  include_headers: true
  date_suffix: false          # Přidat datum do názvu souboru

# API nastavení
api:
  endpoint: "https://query.wikidata.org/sparql"
  timeout: 30                 # sekundy
  retry_attempts: 3
  retry_delay: 5              # sekundy mezi pokusy
  user_agent: "WikidataExtractor/1.0"
  rate_limit: 60              # požadavků za minutu

# Nastavení dotazu
query:
  limit: null                 # Omezení počtu výsledků (null = bez limitu)
  batch_size: 1000           # Velikost dávky pro velké dotazy
  enable_service_timeout: true # Použít SERVICE wikibase:label
  custom_sparql_suffix: null  # Vlastní SPARQL kód na konec dotazu

# Pokročilé možnosti
advanced:
  validate_wikidata_ids: true  # Ověřit existenci Wikidata ID
  skip_redirects: true         # Přeskočit přesměrování
  include_aliases: false       # Zahrnout alternativní názvy
  debug_mode: false           # Podrobné logování
  save_sparql_query: false    # Uložit vygenerovaný SPARQL dotaz
```

## Validační pravidla

### Povinná pole
- `country.wikidata_id`: Musí být validní Wikidata entity ID (Q[0-9]+)
- `data_fields`: Minimálně jedno pole musí být definováno
- `output.filename`: Nesmí být prázdný

### Datové typy
- Wikidata ID: regex `^Q[0-9]+$`
- Property ID: regex `^P[0-9]+$` nebo speciální hodnoty
- Jazykové kódy: ISO 639-1 (cs, en, de, fr, ...)
- Koordináty: formát `lat_lon_split|point|wkt`

### Vzájemné závislosti
- Pokud `coordinates_required: true`, pak pole "coordinates" musí být `required: true`
- `language_codes` určuje fallback pro `rdfs:label`
- `batch_size` nesmí být větší než API limit

## Příklady konfiguračních souborů

### 1. configs/czech_cities.yaml - Základní česká města
```yaml
metadata:
  name: "Czech Major Cities"
  
country:
  wikidata_id: "Q213"
  name: "Czech Republic"
  
settlement_types:
  include: ["Q515", "Q3957"]  # pouze města a městyse
  
data_fields:
  - field: "item_id"
    required: true
    csv_header: "id"
  - field: "name"
    wikidata_property: "rdfs:label" 
    required: true
    csv_header: "name"
  - field: "coordinates"
    wikidata_property: "P625"
    required: true
    csv_header: "lat,lon"
    
output:
  filename: "czech_cities.csv"
```

### 2. configs/slovakia_complete.yaml - Kompletní slovenská data
```yaml
metadata:
  name: "Slovakia Complete Settlements"
  
country:
  wikidata_id: "Q214"
  name: "Slovakia"
  language_codes: ["sk", "cs", "en"]
  
data_fields:
  - field: "item_id"
    required: true
    csv_header: "wikidata_id"
  - field: "name"
    wikidata_property: "rdfs:label"
    required: true 
    csv_header: "name"
    language: "sk"
  - field: "coordinates"
    wikidata_property: "P625"
    csv_header: "latitude,longitude"
  - field: "postal_code"
    wikidata_property: "P281"
    csv_header: "psc"
  - field: "nuts_code" 
    wikidata_property: "P1937"
    csv_header: "nuts"
    
filters:
  coordinates_required: true
  
output:
  filename: "slovakia_settlements.csv"
  date_suffix: true
```

### 3. configs/minimal.yaml - Minimální konfigurace
```yaml
country:
  wikidata_id: "Q213"
  
data_fields:
  - field: "item_id"
    required: true
  - field: "name"
    wikidata_property: "rdfs:label"
    required: true
    
output:
  filename: "output.csv"
```

## Struktura validátoru

### ConfigValidator třída
- `validate_structure()` - YAML struktura
- `validate_wikidata_ids()` - Kontrola existence entity 
- `validate_properties()` - Kontrola Wikidata properties
- `validate_dependencies()` - Vzájemné závislosti
- `validate_output_path()` - Přístupnost výstupního adresáře

### Error handling
- `ConfigValidationError` - Vlastní exception
- Detailní error messages s číslem řádku
- Warnings pro doporučení (např. chybějící coordinates)

## Pokračování
Doporučuji pokračovat implementací základní struktury projektu.