#!/usr/bin/env python3
"""
WikiData SPARQL Extraktor - Hlavní skript

Extrakce dat o městech, obcích a vesnicích z WikiData pomocí SPARQL dotazů.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional
import time

# Import modulů
from src.config_manager import Config, ConfigValidator
from src.query_builder import SPARQLQueryBuilder
from src.wikidata_client import WikiDataClient
from src.data_processor import DataProcessor
from src.csv_exporter import CSVExporter


# Verze
__version__ = "1.0.0"


def setup_logging(verbose: bool = False, quiet: bool = False, log_file: Optional[str] = None) -> None:
    """
    Nastavení logování.

    Args:
        verbose: Detailní výpis
        quiet: Minimální výpis
        log_file: Cesta k log souboru
    """
    # Úroveň logování
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # Formát zpráv
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    handlers.append(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Vždy DEBUG do souboru
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(file_handler)

    # Konfigurace root loggeru
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )


def parse_arguments() -> argparse.Namespace:
    """
    Parsování argumentů příkazové řádky.

    Returns:
        Namespace s argumenty
    """
    parser = argparse.ArgumentParser(
        description='WikiData SPARQL Extraktor - Extrakce dat o městech a obcích',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Příklady použití:
  %(prog)s --config configs/czech_republic.yaml
  %(prog)s --country CZ --output czechia.csv
  %(prog)s --config configs/slovakia.yaml --dry-run
  %(prog)s --config config.yaml --verbose --log-file extractor.log
        """
    )

    # Verze
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    # Konfigurace
    config_group = parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument(
        '--config',
        type=str,
        help='Cesta ke konfiguračnímu souboru'
    )
    config_group.add_argument(
        '--country',
        type=str,
        choices=['CZ', 'SK', 'PL', 'DE', 'UK', 'GB', 'ENG'],
        help='Rychlá volba země (CZ/SK/PL/DE/UK/GB/ENG)'
    )

    # Výstup
    parser.add_argument(
        '--output',
        type=str,
        help='Cesta k výstupnímu CSV (přepíše config)'
    )

    # Pole
    parser.add_argument(
        '--fields',
        type=str,
        help='Seznam polí oddělený čárkami (přepíše config)'
    )

    # Logování
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Detailní výpis'
    )
    log_group.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Minimální výpis'
    )

    parser.add_argument(
        '--log-file',
        type=str,
        help='Cesta k log souboru'
    )

    # Speciální režimy
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Pouze zobrazí SPARQL dotaz bez spuštění'
    )

    parser.add_argument(
        '--validate-config',
        action='store_true',
        help='Pouze validuje konfigurační soubor'
    )

    parser.add_argument(
        '--test-connection',
        action='store_true',
        help='Testuje spojení s WikiData'
    )

    parser.add_argument(
        '--create-report',
        action='store_true',
        help='Vytvoří sumarizační report'
    )

    return parser.parse_args()


def get_config_path(country_code: str) -> Path:
    """
    Získá cestu ke konfiguračnímu souboru pro zemi.

    Args:
        country_code: Kód země (CZ/SK/PL/DE/UK/GB/ENG)

    Returns:
        Cesta ke konfiguračnímu souboru
    """
    country_map = {
        'CZ': 'configs/czech_republic.yaml',
        'SK': 'configs/slovakia.yaml',
        'PL': 'configs/poland.yaml',
        'DE': 'configs/germany.yaml',
        'UK': 'configs/united_kingdom.yaml',
        'GB': 'configs/united_kingdom.yaml',  # Alias pro UK
        'ENG': 'configs/england.yaml'
    }

    return Path(country_map.get(country_code, 'config.yaml'))


def main() -> int:
    """
    Hlavní funkce aplikace.

    Returns:
        Exit kód (0 = úspěch, 1 = chyba)
    """
    # Parsování argumentů
    args = parse_arguments()

    # Nastavení logování
    setup_logging(args.verbose, args.quiet, args.log_file)

    logger = logging.getLogger('WikiDataExtractor')

    try:
        # Banner
        logger.info("=" * 70)
        logger.info("WikiData SPARQL Extraktor v{}".format(__version__))
        logger.info("=" * 70)

        # Určení konfiguračního souboru
        if args.config:
            config_path = Path(args.config)
        else:
            config_path = get_config_path(args.country)

        logger.info(f"📂 Konfigurační soubor: {config_path}")

        # Načtení konfigurace
        config = Config(config_path)

        # Validace konfigurace
        if args.validate_config:
            logger.info("✅ Konfigurace je validní")
            return 0

        # Vytvoření komponent
        query_builder = SPARQLQueryBuilder(config)
        client = WikiDataClient(config)
        processor = DataProcessor(config)
        exporter = CSVExporter(config)

        # Sestavení SPARQL dotazu
        sparql_query = query_builder.build_query()

        # Informace o dotazu
        query_info = query_builder.get_query_info()
        logger.info(f"🎯 Cíl: {query_info['country']} ({query_info['country_qid']})")
        logger.info(f"📊 Datová pole: {query_info['fields_count']} "
                   f"(povinných: {query_info['required_fields']}, "
                   f"volitelných: {query_info['optional_fields']})")

        # Dry run - zobrazení dotazu
        if args.dry_run:
            logger.info("\n" + "=" * 70)
            logger.info("SPARQL Dotaz:")
            logger.info("=" * 70)
            print(sparql_query)
            logger.info("=" * 70)
            return 0

        # Test spojení
        if args.test_connection:
            success = client.test_connection()
            return 0 if success else 1

        # Měření času
        start_time = time.time()

        # Stažení dat
        logger.info("🚀 Zahajuji stahování dat z WikiData...")
        raw_results = client.fetch_all_data(sparql_query)

        if not raw_results:
            logger.warning("⚠️ Žádná data nebyla nalezena")
            return 1

        # Zpracování dat
        processed_data = processor.process_results(raw_results)

        if not processed_data:
            logger.error("❌ Žádná validní data po zpracování")
            return 1

        # Statistiky zpracování
        stats = processor.get_processing_stats(processed_data)
        if stats.get('missing_fields'):
            logger.warning("⚠️ Některé záznamy mají chybějící hodnoty:")
            for field, count in stats['missing_fields'].items():
                logger.warning(f"  - {field}: {count} záznamů")

        # Export do CSV
        output_path = args.output or config.get('output', 'file_path')
        exported_file = exporter.export(processed_data, output_path)

        # Vytvoření reportu
        if args.create_report:
            report = exporter.create_summary_report(processed_data, exported_file)
            print("\n" + report)

        # Statistiky klienta
        client_stats = client.get_statistics()
        logger.info("📡 Statistiky komunikace:")
        logger.info(f"  - Celkem požadavků: {client_stats['total_requests']}")
        logger.info(f"  - Neúspěšné: {client_stats['failed_requests']}")
        logger.info(f"  - Úspěšnost: {client_stats['success_rate']}")

        # Celkový čas
        elapsed_time = time.time() - start_time
        logger.info(f"⏱️  Celkový čas: {elapsed_time:.1f}s")

        # Finální souhrn
        logger.info("=" * 70)
        logger.info("✅ Export úspěšně dokončen!")
        logger.info(f"📂 Výstupní soubor: {exported_file}")
        logger.info(f"📊 Exportováno záznamů: {len(processed_data)}")
        logger.info("=" * 70)

        return 0

    except FileNotFoundError as e:
        logger.error(f"❌ Soubor nenalezen: {e}")
        return 1

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Přerušeno uživatelem")
        return 1

    except Exception as e:
        logger.error(f"❌ Kritická chyba: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
