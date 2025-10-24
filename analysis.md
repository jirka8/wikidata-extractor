# Analýza požadavků a návrh architektury

## Požadavky z zadání

### Funkční požadavky
- Stahování dat měst a sídel z Wikidata API
- Sestavování SPARQL dotazů programaticky
- Vstup: země + požadovaná data
- Základní data: item_id, název, GPS souřadnice, postal code, NUTS code, LAU code
- Výstup: CSV soubor
- Konfigurovatelnost přes konfigurační soubory
- Možnost více konfiguračních souborů

### Technické požadavky
- Python
- Znovupoužitelnost
- Modulární návrh pro budoucí GUI

## Analýza Wikidata API

### SPARQL Endpoint
- URL: https://query.wikidata.org/sparql
- Podpora SPARQL 1.1
- Rate limiting: max 60 req/min pro anonymní uživatele

### Relevantní Wikidata properties pro města/sídla
- P31: instance of (Q515 - city, Q3957 - town, Q532 - village)
- P17: country (pro filtrování podle země)
- P625: coordinate location (GPS souřadnice)
- P281: postal code
- P131: located in administrative territorial entity
- P1937: NUTS code
- P782: LAU code
- rdfs:label: název entity

### Ukázkový SPARQL dotaz
```sparql
SELECT ?item ?itemLabel ?coord ?postal ?nuts ?lau WHERE {
  ?item wdt:P31/wdt:P279* wd:Q486972 . # human settlement
  ?item wdt:P17 wd:Q213 . # Czech Republic
  OPTIONAL { ?item wdt:P625 ?coord }
  OPTIONAL { ?item wdt:P281 ?postal }
  OPTIONAL { ?item wdt:P1937 ?nuts }
  OPTIONAL { ?item wdt:P782 ?lau }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "cs,en" . }
}
```

## Navržená architektura

### Moduly
1. **config_manager.py** - správa konfigurace
2. **query_builder.py** - stavění SPARQL dotazů
3. **wikidata_client.py** - komunikace s API
4. **csv_exporter.py** - export do CSV
5. **main.py** - hlavní skript + CLI

### Struktura projektu
```
wikidata-extractor/
├── src/
│   ├── __init__.py
│   ├── config_manager.py
│   ├── query_builder.py
│   ├── wikidata_client.py
│   └── csv_exporter.py
├── configs/
│   └── example_config.yaml
├── main.py
├── requirements.txt
└── progress.md
```

### Závislosti
- requests (HTTP klient)
- pyyaml (konfigurace)
- csv (built-in)

### Konfigurační formát (YAML)
```yaml
country:
  code: "Q213"  # Wikidata ID pro ČR
  name: "Czech Republic"

data_fields:
  - field: "item_id"
    required: true
  - field: "name"
    property: "rdfs:label"
    required: true
  - field: "coordinates"
    property: "P625"
    required: false
  - field: "postal_code"
    property: "P281"
    required: false

output:
  filename: "czech_cities.csv"
  delimiter: ","
```

## Datové toky
1. Načtení konfigurace → Validace
2. Sestavení SPARQL dotazu podle konfigurace
3. Odeslání dotazu na Wikidata endpoint
4. Zpracování odpovědi (JSON)
5. Export do CSV podle konfigurace

## Pokračování
Doporučuji pokračovat návrhem konfiguračního systému.