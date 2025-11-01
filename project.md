# Zadání projektu: WikiData SPARQL Extraktor měst a obcí

## Přehled projektu
Vytvoření Python skriptu pro extrakci dat o městech, obcích a vesnicích z WikiData pomocí SPARQL dotazů s možností konfigurace pro různé země a volitelných datových polí.

## Cíl projektu
Vytvořit univerzální nástroj pro stahování strukturovaných dat o sídlech z WikiData, který umožní:
- Flexibilní výběr země
- Konfiguraci hierarchie správních jednotek
- **Volbu konkrétních datových polí pro každé sídlo**
- Export do CSV formátu pro další import

---

## Kroky implementace

### 1. Základní struktura projektu

**Vytvořit následující soubory:**
```
wikidata-extractor/
├── wikidata_extractor.py      # Hlavní skript
├── config.yaml                 # Hlavní konfigurační soubor
├── configs/                    # Složka s předpřipravenými konfiguracemi
│   ├── czech_republic.yaml
│   ├── slovakia.yaml
│   ├── poland.yaml
│   └── germany.yaml
├── requirements.txt            # Python závislosti
├── README.md                   # Dokumentace
└── examples/                   # Příklady použití
    └── example_output.csv
```

---

### 2. Konfigurace

Konfigurační soubor (`config.yaml`) by měl obsahovat:

#### 2.1 Základní nastavení země
```yaml
country:
  name: "Czech Republic"
  wikidata_qid: "Q213"          # QID země ve WikiData
  iso_code: "CZ"                # ISO 3166-1 alpha-2
  language: "cs"                # Jazyk pro názvy
```

#### 2.2 Hierarchie správních jednotek
```yaml
administrative_hierarchy:
  - level: 1
    name: "Kraj"
    wikidata_property: "P131"   # Located in administrative territory
    wikidata_instance_of: "Q38911"  # Instance of region
  - level: 2
    name: "Okres"
    wikidata_property: "P131"
    wikidata_instance_of: "Q548611"
  - level: 3
    name: "ORP"
    wikidata_property: "P131"
    wikidata_instance_of: "Q5153984"
  - level: 4
    name: "Obec"
    wikidata_property: "P131"
    wikidata_instance_of: ["Q5153984", "Q262166"]
```

#### 2.3 Typy sídel
```yaml
settlement_types:
  - type: "city"
    wikidata_qid: "Q515"
    label: "Město"
  - type: "town"
    wikidata_qid: "Q3957"
    label: "Městys"
  - type: "village"
    wikidata_qid: "Q532"
    label: "Vesnice"
  - type: "municipality"
    wikidata_qid: "Q262166"
    label: "Obec"
```

#### 2.4 **Konfigurovatelná datová pole** (KLÍČOVÁ SEKCE)
```yaml
data_fields:
  # Základní identifikátory
  - field_name: "wikidata_id"
    wikidata_property: "SUBJECT"  # Speciální: ID subjektu
    required: true
    output_column: "wikidata_id"
    description: "WikiData QID sídla"
  
  # Názvy
  - field_name: "name_local"
    wikidata_property: "rdfs:label"
    language_filter: "cs"          # Filtr podle jazyka
    required: true
    output_column: "name_cs"
    description: "Název v lokálním jazyce"
  
  - field_name: "name_english"
    wikidata_property: "rdfs:label"
    language_filter: "en"
    required: false
    output_column: "name_en"
    description: "Anglický název"
  
  # Typ sídla
  - field_name: "settlement_type"
    wikidata_property: "P31"       # Instance of
    required: true
    output_column: "type"
    description: "Typ sídla (město/vesnice/obec)"
  
  # Geografické souřadnice
  - field_name: "coordinates"
    wikidata_property: "P625"      # Coordinate location
    required: true
    output_column: ["latitude", "longitude"]  # Rozdělí se do 2 sloupců
    description: "GPS souřadnice"
  
  # Populace
  - field_name: "population"
    wikidata_property: "P1082"     # Population
    required: false
    output_column: "population"
    data_type: "integer"
    description: "Počet obyvatel"
  
  # Nadmořská výška
  - field_name: "elevation"
    wikidata_property: "P2044"     # Elevation above sea level
    required: false
    output_column: "elevation_m"
    data_type: "float"
    description: "Nadmořská výška v metrech"
  
  # Rozloha
  - field_name: "area"
    wikidata_property: "P2046"     # Area
    required: false
    output_column: "area_km2"
    data_type: "float"
    description: "Rozloha v km²"
  
  # Poštovní směrovací číslo
  - field_name: "postal_code"
    wikidata_property: "P281"      # Postal code
    required: false
    output_column: "postal_code"
    description: "PSČ"
  
  # Oficiální webové stránky
  - field_name: "website"
    wikidata_property: "P856"      # Official website
    required: false
    output_column: "website"
    description: "Oficiální web"
  
  # Datum založení
  - field_name: "inception"
    wikidata_property: "P571"      # Inception
    required: false
    output_column: "founded_year"
    data_type: "year"
    description: "Rok založení"
  
  # NUTS kód
  - field_name: "nuts_code"
    wikidata_property: "P605"      # NUTS code
    required: false
    output_column: "nuts_code"
    description: "NUTS statistický kód"
  
  # Časové pásmo
  - field_name: "timezone"
    wikidata_property: "P421"      # Located in time zone
    required: false
    output_column: "timezone"
    description: "Časové pásmo"
  
  # Vlajka (URL obrázku)
  - field_name: "flag_image"
    wikidata_property: "P41"       # Flag image
    required: false
    output_column: "flag_url"
    description: "URL vlajky"
  
  # Znak (URL obrázku)
  - field_name: "coat_of_arms"
    wikidata_property: "P94"       # Coat of arms image
    required: false
    output_column: "coat_of_arms_url"
    description: "URL znaku"
  
  # WikiData položka matky obce (parent municipality)
  - field_name: "parent_municipality"
    wikidata_property: "P131"      # Located in administrative territory
    required: false
    output_column: "parent_qid"
    description: "QID nadřazené správní jednotky"
```

#### 2.5 Filtry a omezení
```yaml
filters:
  min_population: null            # Minimální populace (null = bez omezení)
  max_population: null            # Maximální populace
  settlement_types_include:       # Pouze tyto typy (prázdné = všechny)
    - "Q515"   # city
    - "Q3957"  # town
    - "Q532"   # village
    - "Q262166" # municipality
  exclude_historical: true        # Vyloučit historická sídla
  bounding_box: null              # Geografické ohraničení [lat_min, lon_min, lat_max, lon_max]
```

#### 2.6 Výstupní nastavení
```yaml
output:
  file_path: "output/czech_municipalities.csv"
  encoding: "utf-8-sig"           # UTF-8 s BOM pro Excel
  delimiter: ","
  include_header: true
  date_format: "%Y-%m-%d"
  null_value: ""                  # Jak reprezentovat chybějící hodnoty
```

#### 2.7 Nastavení dotazu
```yaml
query_settings:
  endpoint: "https://query.wikidata.org/sparql"
  timeout: 300                    # Timeout v sekundách
  user_agent: "WikiDataExtractor/1.0 (your@email.com)"
  rate_limit_delay: 1.0          # Pauza mezi dotazy v sekundách
  batch_size: 1000               # Kolik záznamů najednou (pro stránkování)
  retry_attempts: 3              # Počet pokusů při chybě
```

---

### 3. SPARQL dotazy

#### 3.1 Generátor SPARQL dotazu
Implementovat funkci `build_sparql_query(config)`, která:
- Dynamicky sestaví SPARQL dotaz podle konfigurace
- Zahrne pouze vybraná datová pole z `data_fields`
- Aplikuje filtry ze sekce `filters`
- Správně napojí hierarchii správních jednotek

#### 3.2 Příklad výsledného SPARQL dotazu (pro ČR s vybranými poli)
```sparql
SELECT DISTINCT ?settlement ?settlementLabel ?typeLabel 
       ?lat ?lon ?population ?elevation ?postalCode
       ?admin1Label ?admin2Label ?admin3Label
WHERE {
  ?settlement wdt:P31/wdt:P279* ?type .
  ?settlement wdt:P17 wd:Q213 .  # Czech Republic
  
  # Instance of city, town, village, or municipality
  VALUES ?type { wd:Q515 wd:Q3957 wd:Q532 wd:Q262166 }
  
  # Coordinates (required)
  ?settlement wdt:P625 ?coord .
  BIND(geof:latitude(?coord) AS ?lat)
  BIND(geof:longitude(?coord) AS ?lon)
  
  # Optional fields
  OPTIONAL { ?settlement wdt:P1082 ?population . }
  OPTIONAL { ?settlement wdt:P2044 ?elevation . }
  OPTIONAL { ?settlement wdt:P281 ?postalCode . }
  
  # Administrative hierarchy
  OPTIONAL { 
    ?settlement wdt:P131 ?admin3 .
    ?admin3 wdt:P31 wd:Q5153984 .
    ?admin3 wdt:P131 ?admin2 .
    ?admin2 wdt:P31 wd:Q548611 .
    ?admin2 wdt:P131 ?admin1 .
    ?admin1 wdt:P31 wd:Q38911 .
  }
  
  SERVICE wikibase:label { 
    bd:serviceParam wikibase:language "cs,en" . 
  }
}
ORDER BY ?settlementLabel
```

---

### 4. Komunikace s WikiData

Implementovat třídu `WikiDataClient`:

```python
class WikiDataClient:
    def __init__(self, config):
        """Inicializace klienta s konfigurací"""
        
    def execute_query(self, sparql_query):
        """Provede SPARQL dotaz a vrátí výsledky"""
        
    def fetch_all_data(self):
        """Stáhne všechna data se stránkováním"""
        
    def handle_rate_limiting(self):
        """Implementuje rate limiting"""
        
    def retry_on_failure(self, func, max_attempts):
        """Opakuje dotaz při selhání"""
```

---

### 5. Zpracování dat

Implementovat třídu `DataProcessor`:

```python
class DataProcessor:
    def __init__(self, config):
        """Inicializace procesoru s konfigurací"""
        
    def parse_results(self, raw_results):
        """Parsuje surové výsledky z WikiData"""
        
    def normalize_coordinates(self, coord_string):
        """Normalizuje souřadnice do float hodnot"""
        
    def extract_qid(self, uri):
        """Extrahuje QID z WikiData URI"""
        
    def handle_missing_values(self, data):
        """Ošetří chybějící hodnoty podle konfigurace"""
        
    def validate_required_fields(self, data):
        """Zkontroluje přítomnost povinných polí"""
        
    def build_hierarchy(self, row):
        """Sestaví hierarchii správních jednotek"""
        
    def deduplicate(self, data):
        """Odstraní duplicitní záznamy"""
```

---

### 6. Export do CSV

Implementovat třídu `CSVExporter`:

```python
class CSVExporter:
    def __init__(self, config):
        """Inicializace exportéru"""
        
    def prepare_dataframe(self, processed_data):
        """Připraví pandas DataFrame"""
        
    def generate_columns(self):
        """Vygeneruje sloupce podle konfigurace data_fields"""
        
    def export(self, dataframe, output_path):
        """Exportuje data do CSV"""
        
    def add_metadata(self):
        """Přidá metadata (datum exportu, verze)"""
```

**Struktura výstupního CSV:**
```csv
wikidata_id,name_cs,name_en,type,admin_level_1,admin_level_2,admin_level_3,latitude,longitude,population,elevation_m,area_km2,postal_code,website,founded_year,nuts_code,timezone,flag_url,coat_of_arms_url,export_date
Q1085,Praha,Prague,Q515,Hlavní město Praha,,,50.0833,14.4167,1309000,235,496.21,110 00,https://www.praha.eu,885,CZ010,UTC+01:00,http://commons.wikimedia.org/...,http://commons.wikimedia.org/...,2024-11-01
```

---

### 7. Příklady konfigurace

#### 7.1 Česká republika (`configs/czech_republic.yaml`)
```yaml
country:
  name: "Czech Republic"
  wikidata_qid: "Q213"
  iso_code: "CZ"
  language: "cs"

administrative_hierarchy:
  - level: 1
    name: "Kraj"
    wikidata_property: "P131"
    wikidata_instance_of: "Q38911"
  - level: 2
    name: "Okres"
    wikidata_property: "P131"
    wikidata_instance_of: "Q548611"
  - level: 3
    name: "ORP"
    wikidata_property: "P131"
    wikidata_instance_of: "Q5153984"

data_fields:
  # Zahrnout všechna pole z sekce 2.4
  # ...

filters:
  exclude_historical: true

output:
  file_path: "output/czech_municipalities.csv"
```

#### 7.2 Slovensko (`configs/slovakia.yaml`)
```yaml
country:
  name: "Slovakia"
  wikidata_qid: "Q214"
  iso_code: "SK"
  language: "sk"

administrative_hierarchy:
  - level: 1
    name: "Kraj"
    wikidata_property: "P131"
    wikidata_instance_of: "Q192283"
  - level: 2
    name: "Okres"
    wikidata_property: "P131"
    wikidata_instance_of: "Q548611"
```

#### 7.3 Polsko (`configs/poland.yaml`)
```yaml
country:
  name: "Poland"
  wikidata_qid: "Q36"
  iso_code: "PL"
  language: "pl"

administrative_hierarchy:
  - level: 1
    name: "Województwo"
    wikidata_property: "P131"
    wikidata_instance_of: "Q54935504"
  - level: 2
    name: "Powiat"
    wikidata_property: "P131"
    wikidata_instance_of: "Q powiat"
  - level: 3
    name: "Gmina"
    wikidata_property: "P131"
    wikidata_instance_of: "Q13539802"
```

#### 7.4 Německo (`configs/germany.yaml`)
```yaml
country:
  name: "Germany"
  wikidata_qid: "Q183"
  iso_code: "DE"
  language: "de"

administrative_hierarchy:
  - level: 1
    name: "Bundesland"
    wikidata_property: "P131"
    wikidata_instance_of: "Q1221156"
  - level: 2
    name: "Regierungsbezirk"
    wikidata_property: "P131"
    wikidata_instance_of: "Q22865"
  - level: 3
    name: "Landkreis"
    wikidata_property: "P131"
    wikidata_instance_of: "Q106658"
  - level: 4
    name: "Gemeinde"
    wikidata_property: "P131"
    wikidata_instance_of: "Q262166"
```

---

### 8. CLI rozhraní

Implementovat `argparse` pro příkazovou řádku:

```python
python wikidata_extractor.py \
  --config configs/czech_republic.yaml \
  --output output/my_export.csv \
  --verbose \
  --log-file extractor.log
```

**Argumenty:**
- `--config PATH` - Cesta ke konfiguračnímu souboru (povinné)
- `--output PATH` - Cesta k výstupnímu CSV (přepíše config)
- `--country CODE` - Rychlá volba země (CZ/SK/PL/DE) - načte předpřipravený config
- `--fields FIELD1,FIELD2,...` - Přepíše vybraná pole z configu
- `--verbose` / `-v` - Detailní výpis
- `--quiet` / `-q` - Minimální výpis
- `--log-file PATH` - Cesta k log souboru
- `--dry-run` - Pouze zobrazí SPARQL dotaz bez spuštění
- `--validate-config` - Pouze validuje konfigurační soubor
- `--list-fields` - Vypíše všechny dostupné WikiData properties

**Příklady použití:**
```bash
# Základní použití
python wikidata_extractor.py --config configs/czech_republic.yaml

# Rychlá volba země
python wikidata_extractor.py --country CZ --output czechia.csv

# Zobrazení SPARQL dotazu
python wikidata_extractor.py --config configs/slovakia.yaml --dry-run

# Vlastní výběr polí
python wikidata_extractor.py --country PL \
  --fields name_local,coordinates,population,website

# Tichý režim s logováním
python wikidata_extractor.py --config config.yaml --quiet --log-file extract.log
```

---

### 9. Logování a reportování

Implementovat komplexní logování:

```python
import logging

# Konfigurace loggeru
logger = logging.getLogger('WikiDataExtractor')

# Logovat:
# - Zahájení a ukončení procesu
# - Počet nalezených záznamů
# - Varování při chybějících datech
# - Chyby při komunikaci s WikiData
# - Statistiky exportu
```

**Příklad výstupu:**
```
[2024-11-01 10:23:15] INFO: Starting WikiData extraction
[2024-11-01 10:23:15] INFO: Loading config: configs/czech_republic.yaml
[2024-11-01 10:23:15] INFO: Target country: Czech Republic (Q213)
[2024-11-01 10:23:15] INFO: Selected data fields: 15
[2024-11-01 10:23:16] INFO: Executing SPARQL query...
[2024-11-01 10:23:42] INFO: Query completed: 6258 settlements found
[2024-11-01 10:23:42] WARNING: 142 settlements missing population data
[2024-11-01 10:23:42] WARNING: 89 settlements missing elevation data
[2024-11-01 10:23:43] INFO: Processing data...
[2024-11-01 10:23:44] INFO: Building administrative hierarchy...
[2024-11-01 10:23:45] INFO: Validating required fields...
[2024-11-01 10:23:45] INFO: All records valid
[2024-11-01 10:23:46] INFO: Exporting to CSV: output/czech_municipalities.csv
[2024-11-01 10:23:47] SUCCESS: Export completed
[2024-11-01 10:23:47] INFO: Total records exported: 6258
[2024-11-01 10:23:47] INFO: File size: 2.3 MB
[2024-11-01 10:23:47] INFO: Execution time: 32 seconds
```

---

### 10. Testování a validace

#### 10.1 Validace konfigurace
```python
class ConfigValidator:
    def validate(self, config):
        """Validuje konfigurační soubor"""
        # Kontrola povinných sekcí
        # Validace WikiData QID
        # Kontrola správnosti properties
        # Validace datových typů
```

#### 10.2 Testovací skripty
```bash
# Test na malém vzorku
python wikidata_extractor.py --config configs/test_small.yaml

# Validace výstupu
python validate_output.py output/czech_municipalities.csv

# Unit testy
python -m pytest tests/
```

#### 10.3 Kontrolní body
- ✓ Správnost SPARQL syntaxe
- ✓ Validita WikiData QID a properties
- ✓ Úplnost hierarchie správních jednotek
- ✓ Korektnost datových typů v CSV
- ✓ Kódování UTF-8 bez problémů
- ✓ Konzistence názvů sloupců

---

## Technické požadavky

### Závislosti (`requirements.txt`)
```
SPARQLWrapper>=2.0.0
pyyaml>=6.0.1
pandas>=2.0.0
requests>=2.31.0
numpy>=1.24.0
python-dotenv>=1.0.0
tqdm>=4.66.0              # Progress bar
colorlog>=6.7.0           # Barevné logování
jsonschema>=4.19.0        # Validace konfigurace
```

### Python verze
- Python 3.9 nebo vyšší

### Doporučená struktura kódu
```python
# wikidata_extractor.py
from dataclasses import dataclass
from typing import List, Dict, Optional
import yaml
import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON

@dataclass
class DataField:
    """Reprezentace datového pole"""
    field_name: str
    wikidata_property: str
    required: bool
    output_column: str | List[str]
    data_type: Optional[str] = None
    language_filter: Optional[str] = None

class Config:
    """Načtení a validace konfigurace"""
    pass

class SPARQLQueryBuilder:
    """Sestavení SPARQL dotazů"""
    pass

class WikiDataClient:
    """Komunikace s WikiData"""
    pass

class DataProcessor:
    """Zpracování dat"""
    pass

class CSVExporter:
    """Export do CSV"""
    pass

def main():
    """Hlavní funkce"""
    pass

if __name__ == "__main__":
    main()
```

---

## Příklady dostupných WikiData properties

Pro referenci při konfiguraci `data_fields`:

| Property | QID | Popis | Datový typ |
|----------|-----|-------|------------|
| P31 | Instance of | Typ entity | Item |
| P17 | Country | Země | Item |
| P131 | Located in | Správní jednotka | Item |
| P625 | Coordinates | GPS souřadnice | Globe coordinate |
| P1082 | Population | Počet obyvatel | Quantity |
| P2044 | Elevation | Nadmořská výška | Quantity |
| P2046 | Area | Rozloha | Quantity |
| P281 | Postal code | PSČ | String |
| P856 | Website | Oficiální web | URL |
| P571 | Inception | Datum založení | Time |
| P605 | NUTS code | NUTS kód | String |
| P421 | Timezone | Časové pásmo | Item |
| P41 | Flag image | Vlajka | Commons media |
| P94 | Coat of arms | Znak | Commons media |
| P6 | Head of government | Starosta | Item |
| P1540 | Male population | Mužů | Quantity |
| P1539 | Female population | Žen | Quantity |
| P473 | Local dialing code | Telefonní předvolba | String |
| P395 | License plate code | SPZ | String |
| P1566 | GeoNames ID | GeoNames ID | External identifier |

Úplný seznam na: https://www.wikidata.org/wiki/Wikidata:List_of_properties

---

## Očekávaný výstup projektu

### 1. Funkční Python aplikace
- ✓ Spustitelná z příkazové řádky
- ✓ Plně konfigurovatelná přes YAML
- ✓ Robustní error handling
- ✓ Detailní logování

### 2. Dokumentace
- ✓ README.md s návody na použití
- ✓ Příklady konfiguračních souborů
- ✓ Seznam dostupných WikiData properties
- ✓ Troubleshooting guide

### 3. Kvalitní výstupní data
- ✓ Čistý CSV formát
- ✓ Konzistentní struktura
- ✓ Správné kódování (UTF-8)
- ✓ Validovaná data
- ✓ Úplná hierarchie správních jednotek

### 4. Flexibilita
- ✓ Podpora libovolné země
- ✓ Volitelná datová pole
- ✓ Konfigurovatelné filtry
- ✓ Rozšiřitelná architektura

---

## Poznámky k implementaci

### Důležité WikiData koncepty

1. **QID** - Jedinečný identifikátor entity (např. Q213 = Česká republika)
2. **Property (P)** - Vlastnost entity (např. P625 = souřadnice)
3. **Instance of (P31)** - Typ entity
4. **Subclass of (P279)** - Podtřída entity

### Tipy pro SPARQL dotazy

- Používat `OPTIONAL` pro nepovinná pole
- Implementovat timeout pro velké dotazy
- Využít `SERVICE wikibase:label` pro automatické názvy
- Filtrovat podle jazyka při získávání labelů
- Použít `DISTINCT` pro odstranění duplicit

### Optimalizace výkonu

- Cachování výsledků dotazů
- Paralelní zpracování batch požadavků
- Komprese výstupních CSV souborů
- Inkrementální aktualizace (ukládání rozdílů)

---

## Rozšíření do budoucna

Možné budoucí funkce:
- 🔄 Podpora aktualizace existujících CSV (diff update)
- 🗺️ Export do GeoJSON formátu
- 📊 Statistické reporty a grafy
- 🌐 GUI webové rozhraní
- 🔍 Fulltextové vyhledávání v datech
- 📱 REST API pro dotazování
- 🐳 Docker kontejner
- ⚡ Async/paralelní stahování

---

## Kontaktní informace a podpora

Po dokončení projektu vytvořit:
- GitHub repository s otevřeným zdrojovým kódem
- Issues tracker pro hlášení chyb
- Wiki s podrobnou dokumentací
- Příklady use-case scénářů

---

## Licencování

Doporučená licence: MIT License (umožňuje volné použití i pro komerční účely)

WikiData data jsou dostupná pod CC0 Public Domain licencí.

---

**Verze zadání:** 1.0  
**Datum vytvoření:** 2024-11-01  
**Autor specifikace:** Pro Claude Code implementaci
