#!/usr/bin/env python3
"""
Wikidata Extractor - hlavní skript
Nástroj pro stahování dat o sídlech z Wikidata API
"""

import sys
import os
import argparse
from typing import Optional

# Přidat src do Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config_manager import ConfigManager, ConfigValidationError
from query_builder import SPARQLQueryBuilder
from wikidata_client import WikidataClient, WikidataAPIError
from csv_exporter import CSVExporter, CSVExportError


def parse_arguments():
    """Parsuje argumenty příkazové řádky"""
    parser = argparse.ArgumentParser(
        description='Wikidata Extractor - stahování dat o sídlech z Wikidata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Příklady použití:
  python main.py configs/czech_cities.yaml
  python main.py configs/slovakia_complete.yaml --test-connection
  python main.py configs/minimal.yaml --save-query query.sparql
        """
    )
    
    parser.add_argument(
        'config_file',
        help='Cesta ke konfiguračnímu souboru (YAML)'
    )
    
    parser.add_argument(
        '--test-connection',
        action='store_true',
        help='Pouze otestuje připojení k Wikidata API'
    )
    
    parser.add_argument(
        '--save-query',
        metavar='FILE',
        help='Uloží vygenerovaný SPARQL dotaz do souboru'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Pouze zobrazí dotaz, nespouští jej'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Podrobný výstup'
    )
    
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Zapnout dávkové stahování (přepíše konfiguraci)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        metavar='N',
        help='Velikost dávky pro batch stahování'
    )
    
    parser.add_argument(
        '--max-results',
        type=int,
        metavar='N',
        help='Maximální počet výsledků'
    )
    
    return parser.parse_args()


def main():
    """Hlavní funkce aplikace"""
    args = parse_arguments()
    
    try:
        # 1. Načtení konfigurace
        if args.verbose:
            print(f"Načítám konfiguraci z: {args.config_file}")
        
        config_manager = ConfigManager()
        config = config_manager.load_config(args.config_file)
        
        if args.verbose:
            print(f"✓ Konfigurace načtena")
            print(f"  Země: {config.get('country', {}).get('name', 'N/A')}")
            print(f"  Datová pole: {len(config.get('data_fields', []))}")
        
        # 2. Sestavení SPARQL dotazu
        if args.verbose:
            print("Sestavujem SPARQL dotaz...")
        
        query_builder = SPARQLQueryBuilder(config)
        sparql_query = query_builder.build_query()
        
        if args.verbose:
            query_metadata = query_builder.get_query_metadata()
            print(f"✓ SPARQL dotaz sestaven")
            print(f"  Typy sídel: {len(query_metadata['settlement_types'])}")
            print(f"  Jazyky: {', '.join(query_metadata['languages'])}")
        
        # Uložit dotaz pokud je požadováno
        if args.save_query:
            with open(args.save_query, 'w', encoding='utf-8') as f:
                f.write(sparql_query)
            print(f"✓ SPARQL dotaz uložen do: {args.save_query}")
        
        # Zobrazit dotaz při verbose nebo dry-run
        if args.verbose or args.dry_run:
            print("\\nVygenerovaný SPARQL dotaz:")
            print("-" * 50)
            print(sparql_query)
            print("-" * 50)
        
        if args.dry_run:
            print("\\n✓ Dry-run dokončen - dotaz nebyl vykonán")
            return 0
        
        # 3. Připojení k Wikidata API
        if args.verbose:
            print("\\nPřipojuji se k Wikidata API...")
        
        api_config = config_manager.get_api_config()
        wikidata_client = WikidataClient(api_config)
        
        # Test připojení
        if args.test_connection or args.verbose:
            if wikidata_client.test_connection():
                print("✓ Připojení k Wikidata API funkční")
                if args.test_connection:
                    return 0
            else:
                print("✗ Chyba při připojení k Wikidata API")
                return 1
        
        # 4. Vykonání dotazu
        batch_config = config.get('query', {}).get('batch_processing', {})
        
        # Přepsat konfiguraci parametry z příkazové řádky
        batch_enabled = args.batch or batch_config.get('enabled', False)
        batch_size = args.batch_size or batch_config.get('batch_size', 1000)
        max_results = args.max_results or batch_config.get('max_results')
        
        if batch_enabled:
            if args.verbose:
                print("Vykonávám SPARQL dotaz s dávkovým stahováním...")
                print(f"  Velikost dávky: {batch_size}")
                print(f"  Max výsledků: {max_results or 'neomezeno'}")
            
            results = wikidata_client.execute_query_batch(
                sparql_query, 
                batch_size=batch_size,
                max_results=max_results
            )
        else:
            if args.verbose:
                print("Vykonávám SPARQL dotaz...")
            
            results = wikidata_client.execute_query(sparql_query)
        
        if args.verbose:
            print(f"✓ Dotaz vykonán, získáno {len(results)} záznamů")
        
        # 5. Export do CSV
        if args.verbose:
            print("Exportuji data do CSV...")
        
        output_config = config_manager.get_output_config()
        csv_exporter = CSVExporter(output_config)
        
        # Získat konfiguraci seskupování
        grouping_config = config.get('grouping', {})
        
        output_path = csv_exporter.export_data(results, config_manager.get_data_fields(), grouping_config)
        
        print(f"✓ Data exportována do: {output_path}")
        
        # Statistiky
        if args.verbose:
            stats = csv_exporter.get_export_statistics(output_path)
            print(f"  Řádků dat: {stats.get('data_rows', 'N/A')}")
            print(f"  Velikost souboru: {stats.get('file_size_bytes', 0)} bytů")
        
        # Uzavřít klienta
        wikidata_client.close()
        
        return 0
        
    except ConfigValidationError as e:
        print(f"✗ Chyba v konfiguraci: {e}", file=sys.stderr)
        return 1
        
    except WikidataAPIError as e:
        print(f"✗ Chyba Wikidata API: {e}", file=sys.stderr)
        return 1
        
    except CSVExportError as e:
        print(f"✗ Chyba při exportu CSV: {e}", file=sys.stderr)
        return 1
        
    except FileNotFoundError as e:
        print(f"✗ Soubor nenalezen: {e}", file=sys.stderr)
        return 1
        
    except KeyboardInterrupt:
        print("\\n✗ Přerušeno uživatelem", file=sys.stderr)
        return 130
        
    except Exception as e:
        print(f"✗ Neočekávaná chyba: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())