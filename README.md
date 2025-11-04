# WikiData SPARQL Extraktor

Univerzální nástroj pro extrakci strukturovaných dat o městech, obcích a vesnicích z WikiData pomocí SPARQL dotazů.

## 🎯 Hlavní funkce

- ✅ **Flexibilní konfigurace** - YAML konfigurace pro libovolnou zemi
- ✅ **Volitelná datová pole** - Vyberte si pouze pole, která potřebujete
- ✅ **Administrativní hierarchie** - Podpora komplexních správních struktur
- ✅ **Robustní komunikace** - Rate limiting, retry logika, error handling
- ✅ **Export do CSV** - Čistý formát s UTF-8 kódováním
- ✅ **CLI rozhraní** - Snadné použití z příkazové řádky
- ✅ **Validace** - Automatická validace konfigurace a dat

## 📋 Požadavky

- Python 3.9 nebo vyšší
- Závislosti uvedené v `requirements.txt`

## 🚀 Instalace

```bash
# Klonování/stažení projektu
cd wikidata-extractor

# Vytvoření virtuálního prostředí (doporučeno)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# nebo
venv\Scripts\activate  # Windows

# Instalace závislostí
pip install -r requirements.txt
```

## 📖 Základní použití

### Seznam dostupných konfigurací

```bash
# Zobrazit všechny dostupné konfigurace
python wikidata_extractor.py --list-configs
```

### Rychlé použití s předpřipravenými konfiguracemi

Můžete použít buď **zkratky** nebo **plné názvy** konfiguračních souborů:

```bash
# Pomocí zkratek (pro zpětnou kompatibilitu)
python wikidata_extractor.py --country CZ    # Česká republika
python wikidata_extractor.py --country SK    # Slovensko
python wikidata_extractor.py --country PL    # Polsko
python wikidata_extractor.py --country DE    # Německo
python wikidata_extractor.py --country UK    # Spojené království
python wikidata_extractor.py --country GB    # Spojené království (alias)
python wikidata_extractor.py --country ENG   # Pouze Anglie

# Pomocí plných názvů (doporučeno pro nové konfigurace)
python wikidata_extractor.py --country czech_republic
python wikidata_extractor.py --country slovakia
python wikidata_extractor.py --country united_kingdom         # UK - kompletní data
python wikidata_extractor.py --country united_kingdom_cities  # UK - pouze města (rychlejší)
python wikidata_extractor.py --country england

# Case-insensitive
python wikidata_extractor.py --country CZECH_REPUBLIC
python wikidata_extractor.py --country Czech_Republic
```

### Použití s vlastní konfigurací

```bash
# Absolutní cesta
python wikidata_extractor.py --config /cesta/k/moje_konfigurace.yaml

# Relativní cesta
python wikidata_extractor.py --config configs/czech_republic.yaml
```

### Přidání nové země (snadné!)

1. Vytvořte nový YAML soubor v adresáři `configs/`:

```bash
# Například pro Francii
cp configs/germany.yaml configs/france.yaml
```

2. Upravte soubor podle potřeby (QID, jazyk, hierarchie)

3. Použijte ho - **bez úpravy hlavního skriptu!**

```bash
# Pomocí názvu souboru (bez .yaml)
python wikidata_extractor.py --country france

# Nebo přímou cestou
python wikidata_extractor.py --config configs/france.yaml
```

Žádné úpravy kódu nejsou potřeba! 🎉

### Vlastní konfigurace pro specifické potřeby

Můžete vytvořit vlastní konfigurace se specifickými poli pro různé účely:

```bash
# Příklad 1: Základní informace o českých obcích
# configs/czech_municipalities_basic.yaml obsahuje pouze:
# - název obce, souřadnice, okres, kraj, NUTS kód
python wikidata_extractor.py --country czech_municipalities_basic --limit 10

# Příklad 2: Města UK - lightweight konfigurace
# configs/united_kingdom_cities.yaml obsahuje pouze:
# - název, souřadnice, populace (pouze města, bez vesnic)
python wikidata_extractor.py --country united_kingdom_cities --limit 10
```

**Výstupní CSV (czech_municipalities_basic):**
```csv
wikidata_id,nazev_obce,latitude,longitude,nuts_kod,admin_level_1,admin_level_2,export_date
Q1085,Praha,50.0833,14.4167,CZ010,Hlavní město Praha,,2024-11-01
```

**Výhody custom konfigurací:**
- 🎯 Pouze data, která skutečně potřebujete
- ⚡ Rychlejší stahování (méně polí)
- 📊 Přehlednější výstup
- 💾 Menší soubory

### Testování s omezeným počtem výsledků

Pro rychlé testování konfigurace použijte `--limit`:

```bash
# Stáhnout pouze 10 záznamů pro test
python wikidata_extractor.py --country CZ --limit 10

# Test s 100 záznamy
python wikidata_extractor.py --country CZ --limit 100 --verbose

# Kombinace s dry-run pro zobrazení SPARQL s LIMITem
python wikidata_extractor.py --country CZ --limit 50 --dry-run
```

**Výhody použití --limit:**
- ⚡ Rychlé testování (sekundy místo minut)
- 🔍 Kontrola struktury dat
- 🛠️ Ladění SPARQL dotazů
- 💾 Šetření zdrojů při vývoji

### Přizpůsobení výstupu

```bash
# Vlastní výstupní soubor
python wikidata_extractor.py --country CZ --output moje_data.csv

# S detailním výpisem
python wikidata_extractor.py --country CZ --verbose

# S logováním do souboru
python wikidata_extractor.py --country CZ --log-file extractor.log

# Tichý režim (pouze chyby)
python wikidata_extractor.py --country CZ --quiet

# Kombinace parametrů
python wikidata_extractor.py --country CZ --limit 50 --verbose --output test.csv
```

### Speciální režimy

```bash
# Seznam všech dostupných konfigurací
python wikidata_extractor.py --list-configs

# Zobrazení SPARQL dotazu bez spuštění
python wikidata_extractor.py --config config.yaml --dry-run

# Validace konfiguračního souboru
python wikidata_extractor.py --config config.yaml --validate-config

# Test spojení s WikiData
python wikidata_extractor.py --config config.yaml --test-connection

# Vytvoření sumarizačního reportu
python wikidata_extractor.py --country CZ --create-report
```

## ⚙️ Struktura konfiguračního souboru

Konfigurační soubor je ve formátu YAML a obsahuje tyto sekce:

### 1. Základní nastavení země

```yaml
country:
  name: "Czech Republic"
  wikidata_qid: "Q213"       # QID země ve WikiData
  iso_code: "CZ"              # ISO 3166-1 alpha-2
  language: "cs"              # Jazyk pro názvy
```

### 2. Administrativní hierarchie

```yaml
administrative_hierarchy:
  - level: 1
    name: "Kraj"
    wikidata_property: "P131"
    wikidata_instance_of: "Q38911"
  - level: 2
    name: "Okres"
    wikidata_property: "P131"
    wikidata_instance_of: "Q548611"
```

### 3. Typy sídel

```yaml
settlement_types:
  - type: "city"
    wikidata_qid: "Q515"
    label: "Město"
  - type: "village"
    wikidata_qid: "Q532"
    label: "Vesnice"
```

### 4. Datová pole

```yaml
data_fields:
  - field_name: "wikidata_id"
    wikidata_property: "SUBJECT"
    required: true
    output_column: "wikidata_id"
    description: "WikiData QID"

  - field_name: "coordinates"
    wikidata_property: "P625"
    required: true
    output_column: ["latitude", "longitude"]
    description: "GPS souřadnice"

  - field_name: "population"
    wikidata_property: "P1082"
    required: false
    output_column: "population"
    data_type: "integer"
    description: "Počet obyvatel"
```

### 5. Filtry

```yaml
filters:
  min_population: 1000           # Minimální populace
  max_population: null           # Maximální populace
  settlement_types_include:      # Pouze tyto typy
    - "Q515"   # city
    - "Q532"   # village
  exclude_historical: true       # Vyloučit historická sídla
  bounding_box: null             # [lat_min, lon_min, lat_max, lon_max]
```

### 6. Výstupní nastavení

```yaml
output:
  file_path: "output/czech_municipalities.csv"
  encoding: "utf-8-sig"          # UTF-8 s BOM pro Excel
  delimiter: ","
  include_header: true
  date_format: "%Y-%m-%d"
  null_value: ""
```

### 7. Nastavení SPARQL dotazu

```yaml
query_settings:
  endpoint: "https://query.wikidata.org/sparql"
  timeout: 300                   # Timeout v sekundách
  user_agent: "WikiDataExtractor/1.0"
  rate_limit_delay: 1.0         # Pauza mezi dotazy (s)
  batch_size: 1000              # Velikost dávky
  retry_attempts: 3             # Počet pokusů při chybě
  strategy: "by_admin_level"    # Volitelná strategie: dávkové zpracování
  batch_by_admin_level: 1       # Úroveň pro dávkové zpracování
```

**Strategie stahování:**
- **Standardní** (bez `strategy`): Stáhne všechna data najednou
- **by_admin_level**: Rozdělí stahování podle administrativních celků (např. kraje, constituent countries)
  - Výhodné pro velké země (UK, USA) - předchází timeout chybám
  - `batch_by_admin_level: 1` znamená rozdělení podle první úrovně hierarchie

## 📊 Dostupné WikiData Properties

Nejčastěji používané properties pro extrakci dat o sídlech:

| Property | Popis | Datový typ |
|----------|-------|------------|
| P31 | Instance of (typ entity) | Item |
| P17 | Country (země) | Item |
| P131 | Located in (správní jednotka) | Item |
| P625 | Coordinates (GPS souřadnice) | Globe coordinate |
| P1082 | Population (počet obyvatel) | Quantity |
| P2044 | Elevation (nadmořská výška) | Quantity |
| P2046 | Area (rozloha) | Quantity |
| P281 | Postal code (PSČ) | String |
| P856 | Website (oficiální web) | URL |
| P571 | Inception (datum založení) | Time |
| P605 | NUTS code | String |
| P421 | Timezone (časové pásmo) | Item |
| P41 | Flag image (vlajka) | Commons media |
| P94 | Coat of arms (znak) | Commons media |

Úplný seznam na: https://www.wikidata.org/wiki/Wikidata:List_of_properties

## 🏗️ Struktura projektu

```
wikidata-extractor/
├── wikidata_extractor.py      # Hlavní skript
├── requirements.txt            # Python závislosti
├── README.md                   # Dokumentace
├── src/                        # Zdrojové moduly
│   ├── __init__.py
│   ├── config_manager.py       # Správa konfigurace
│   ├── query_builder.py        # SPARQL query builder
│   ├── wikidata_client.py      # WikiData klient
│   ├── data_processor.py       # Zpracování dat
│   └── csv_exporter.py         # CSV export
├── configs/                    # Konfigurační soubory
│   ├── czech_republic.yaml             # ČR - kompletní data
│   ├── czech_municipalities_basic.yaml # ČR - pouze základní info
│   ├── slovakia.yaml
│   ├── poland.yaml
│   ├── germany.yaml
│   ├── united_kingdom.yaml             # UK - kompletní data
│   ├── united_kingdom_cities.yaml      # UK - pouze města (lightweight)
│   └── england.yaml
├── output/                     # Výstupní soubory
└── examples/                   # Příklady
```

## 🎓 Příklady použití

### Příklad 1: Základní export českých měst

```bash
python wikidata_extractor.py --country CZ
```

Výstup: `output/czech_municipalities.csv` s kompletními daty o českých sídlech.

### Příklad 2: Export s custom konfigurací

Vytvořte vlastní konfigurační soubor (např. `my_config.yaml`) a upravte dle potřeby.

```bash
python wikidata_extractor.py --config my_config.yaml --verbose
```

### Příklad 3: Rychlý test s limitovaným počtem výsledků

```bash
# Rychlý test na 10 záznamech
python wikidata_extractor.py --country CZ --limit 10 --verbose

# Test konfigurace pro UK na 50 záznamech
python wikidata_extractor.py --country UK --limit 50 --output test_uk.csv
```

**Kdy použít --limit:**
- 🚀 Testování nové konfigurace před plným exportem
- 🔍 Kontrola struktury výstupních dat
- 🛠️ Ladění SPARQL dotazů
- ⏱️ Rychlá iterace při vývoji

### Příklad 4: Použití custom konfigurace s omezenými poli

```bash
# Základní informace o českých obcích (název, GPS, okres, kraj, NUTS)
python wikidata_extractor.py --country czech_municipalities_basic

# S limitem pro rychlý test
python wikidata_extractor.py --country czech_municipalities_basic --limit 100 --verbose
```

**Výhody:**
- Rychlejší stahování (méně SPARQL polí)
- Přehlednější výstup (pouze potřebná data)
- Menší CSV soubory

### Příklad 5: Export pouze velkých měst

V konfiguraci nastavte:

```yaml
filters:
  min_population: 10000
  settlement_types_include:
    - "Q515"  # pouze města
```

### Příklad 6: Dry run - zobrazení dotazu

```bash
python wikidata_extractor.py --country CZ --dry-run

# S LIMITem
python wikidata_extractor.py --country CZ --limit 100 --dry-run
```

Zobrazí SPARQL dotaz bez jeho provedení.

## 🔧 Řešení problémů

### Chyba při spojení s WikiData

```
❌ Chyba spojení: Connection timeout
```

**Řešení:** Zkuste zvýšit timeout v konfiguraci:

```yaml
query_settings:
  timeout: 600  # 10 minut
```

### Žádné výsledky

```
⚠️ Žádná data nebyla nalezena
```

**Možné příčiny:**
- Špatné QID v konfiguraci
- Příliš restriktivní filtry
- Nesprávná instance_of hodnota

**Řešení:** Použijte `--dry-run` pro kontrolu SPARQL dotazu.

### Chybějící hodnoty v CSV

```
⚠️ 142 settlements missing population data
```

To je normální - ne všechna sídla ve WikiData mají kompletní data.

## 🤝 Přispívání

Pokud chcete přispět k projektu:

1. Vytvořte fork projektu
2. Vytvořte feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit změny (`git commit -m 'Add some AmazingFeature'`)
4. Push do branch (`git push origin feature/AmazingFeature`)
5. Otevřete Pull Request

## 📝 Licence

Tento projekt je licencován pod MIT licencí.

WikiData data jsou dostupná pod CC0 Public Domain licencí.

## 🔗 Užitečné odkazy

- [WikiData Query Service](https://query.wikidata.org/)
- [WikiData Properties List](https://www.wikidata.org/wiki/Wikidata:List_of_properties)
- [SPARQL Tutorial](https://www.wikidata.org/wiki/Wikidata:SPARQL_tutorial)
- [WikiData Data Model](https://www.mediawiki.org/wiki/Wikibase/DataModel)

## 📞 Podpora

Pokud narazíte na problém nebo máte dotaz:

1. Zkontrolujte dokumentaci výše
2. Podívejte se na [Issues](https://github.com/your-repo/issues)
3. Vytvořte nový issue s detailním popisem problému

## 🎉 Příklady výstupů

### Ukázkový CSV výstup

```csv
wikidata_id,name_cs,name_en,type,latitude,longitude,population,elevation_m,area_km2,postal_code,website,admin_level_1,admin_level_2,export_date
Q1085,Praha,Prague,Q515,50.0833,14.4167,1309000,235.0,496.21,110 00,https://www.praha.eu,Hlavní město Praha,,2024-11-01
Q14960,Brno,Brno,Q515,49.1952,16.6079,380681,237.0,230.19,602 00,https://www.brno.cz,Jihomoravský kraj,Brno-město,2024-11-01
```

## ⚠️ Poznámky

- WikiData se neustále aktualizuje, data se mohou lišit
- Rate limiting je důležitý pro ochranu WikiData serveru
- Některá sídla mohou mít neúplná data
- Pro velké extrakce může trvat delší dobu (minutes až desítky minut)

### Poznámky k UK/England konfiguracím

**Spojené království (UK)** má specifickou administrativní strukturu:
- `--country united_kingdom` - extrahuje všechna sídla z celého UK (England, Scotland, Wales, Northern Ireland) s kompletními daty
- `--country united_kingdom_cities` - **lightweight verze** pouze s městy a základními poli (rychlejší stahování)
- `--country england` - extrahuje pouze sídla z Anglie
- UK zahrnuje speciální pole jako OS Grid Reference (P613) pro Ordnance Survey souřadnicový systém
- Administrativní hierarchie je komplexnější kvůli různým systémům v jednotlivých zemích UK

**Dávkové zpracování (batch processing):**
- UK konfigurace používají strategii `by_admin_level` pro rozdělení stahování podle constituent countries (England, Scotland, Wales, Northern Ireland)
- Tento přístup zrychluje stahování a předchází timeout chybám
- Můžete monitorovat průběh zpracování jednotlivých regionů pomocí `--verbose` parametru

---

**Verze:** 1.0.0
**Autor:** WikiData Extractor Project
**Datum:** 2024-11-01
