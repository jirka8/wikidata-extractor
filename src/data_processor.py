"""Zpracování a normalizace dat z WikiData."""

import logging
import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from urllib.parse import urlparse

from .config_manager import Config, DataField


logger = logging.getLogger('WikiDataExtractor.DataProcessor')


class DataProcessor:
    """Zpracování a normalizace dat z WikiData."""

    def __init__(self, config: Config):
        """
        Inicializace data processoru.

        Args:
            config: Konfigurace projektu
        """
        self.config = config
        self.data_fields = config.get_data_fields()

    def process_results(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Zpracuje surové výsledky z WikiData.

        Args:
            raw_results: Surové výsledky z SPARQL dotazu

        Returns:
            Zpracované a normalizované záznamy
        """
        logger.info(f"🔄 Zpracovávám {len(raw_results)} záznamů...")

        processed_data = []
        skipped_count = 0

        for i, raw_row in enumerate(raw_results):
            try:
                processed_row = self._process_single_row(raw_row)

                # Validace povinných polí
                if self._validate_required_fields(processed_row):
                    processed_data.append(processed_row)
                else:
                    skipped_count += 1
                    logger.debug(f"Záznam {i+1} přeskočen - chybí povinná pole")

            except Exception as e:
                logger.warning(f"⚠️ Chyba při zpracování záznamu {i+1}: {e}")
                skipped_count += 1

        logger.info(f"✅ Zpracováno: {len(processed_data)} záznamů")
        if skipped_count > 0:
            logger.warning(f"⚠️ Přeskočeno: {skipped_count} záznamů")

        # Odstranění duplikátů
        processed_data = self.deduplicate(processed_data)

        return processed_data

    def _process_single_row(self, raw_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Zpracuje jeden záznam.

        Args:
            raw_row: Surový záznam z SPARQL

        Returns:
            Zpracovaný záznam
        """
        processed_row = {}

        # Zpracování každého pole podle konfigurace
        for field in self.data_fields:
            value = self._extract_field_value(raw_row, field)

            # Aplikace transformací
            value = self._apply_transformations(value, field)

            # Uložení podle output_column
            if isinstance(field.output_column, list):
                # Pole s více výstupními sloupci (např. coordinates → lat, lon)
                if isinstance(value, (list, tuple)) and len(value) == len(field.output_column):
                    for i, col_name in enumerate(field.output_column):
                        processed_row[col_name] = value[i]
            else:
                processed_row[field.output_column] = value

        # Přidání administrativní hierarchie
        hierarchy = self.config.get('administrative_hierarchy', default=[])
        for level_data in hierarchy:
            level = level_data['level']
            col_name = f"admin_level_{level}"

            # Extrakce hodnoty
            var_name = f'admin{level}Label'
            if var_name in raw_row:
                processed_row[col_name] = raw_row[var_name].get('value', '')
            else:
                processed_row[col_name] = ''

        # Přidání metadat
        processed_row['export_date'] = datetime.now().strftime(
            self.config.get('output', 'date_format', default='%Y-%m-%d')
        )

        return processed_row

    def _extract_field_value(self, raw_row: Dict[str, Any], field: DataField) -> Any:
        """
        Extrahuje hodnotu pole ze surového záznamu.

        Args:
            raw_row: Surový záznam
            field: Definice pole

        Returns:
            Hodnota pole nebo None
        """
        # Speciální případy
        if field.wikidata_property == 'SUBJECT':
            # Extrakce QID
            if 'settlement' in raw_row:
                return self.extract_qid(raw_row['settlement']['value'])
            return None

        if field.wikidata_property == 'rdfs:label':
            # Label
            var_name = 'settlementLabel'
            if var_name in raw_row:
                return raw_row[var_name].get('value')
            return None

        # Coordinates
        if field.field_name == 'coordinates':
            if 'lat' in raw_row and 'lon' in raw_row:
                lat = raw_row['lat'].get('value')
                lon = raw_row['lon'].get('value')
                return (
                    self.normalize_coordinates(lat),
                    self.normalize_coordinates(lon)
                )
            return (None, None)

        # Standardní pole
        var_name = field.field_name
        if var_name in raw_row:
            raw_value = raw_row[var_name].get('value')

            # Pro P31 (instance of) extrahovat label
            if field.wikidata_property == 'P31':
                label_var = f'{var_name}Label'
                if label_var in raw_row:
                    return raw_row[label_var].get('value')
                return self.extract_qid(raw_value)

            return raw_value

        return None

    def _apply_transformations(self, value: Any, field: DataField) -> Any:
        """
        Aplikuje transformace na hodnotu podle typu dat.

        Args:
            value: Hodnota k transformaci
            field: Definice pole

        Returns:
            Transformovaná hodnota
        """
        if value is None:
            return self.config.get('output', 'null_value', default='')

        # Koordináty už jsou zpracované jako tuple
        if field.field_name == 'coordinates':
            return value

        data_type = field.data_type

        # Datové typy
        if data_type == 'integer':
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return self.config.get('output', 'null_value', default='')

        if data_type == 'float':
            try:
                return float(value)
            except (ValueError, TypeError):
                return self.config.get('output', 'null_value', default='')

        if data_type == 'year':
            # Extrakce roku z data
            year_match = re.search(r'(\d{4})', str(value))
            if year_match:
                return int(year_match.group(1))
            return self.config.get('output', 'null_value', default='')

        # URL validace
        if field.wikidata_property in ['P856', 'P41', 'P94']:  # Website, flag, coat of arms
            if value and isinstance(value, str):
                # Zkontrolovat, že je to validní URL
                try:
                    result = urlparse(value)
                    if all([result.scheme, result.netloc]):
                        return value
                except:
                    pass
            return self.config.get('output', 'null_value', default='')

        # String (výchozí)
        return str(value)

    def normalize_coordinates(self, coord_string: str) -> Optional[float]:
        """
        Normalizuje souřadnice do float hodnot.

        Args:
            coord_string: Souřadnice jako string

        Returns:
            Normalizovaná souřadnice nebo None
        """
        if not coord_string:
            return None

        try:
            return float(coord_string)
        except ValueError:
            logger.warning(f"⚠️ Nelze převést souřadnici: {coord_string}")
            return None

    def extract_qid(self, uri: str) -> str:
        """
        Extrahuje QID z WikiData URI.

        Args:
            uri: WikiData URI (např. http://www.wikidata.org/entity/Q1085)

        Returns:
            QID (např. Q1085)
        """
        if not uri:
            return ''

        # Regex pro extrakci QID
        match = re.search(r'Q\d+', uri)
        if match:
            return match.group(0)

        return uri

    def _validate_required_fields(self, row: Dict[str, Any]) -> bool:
        """
        Zkontroluje přítomnost povinných polí.

        Args:
            row: Záznam k validaci

        Returns:
            True pokud jsou všechna povinná pole přítomna
        """
        null_value = self.config.get('output', 'null_value', default='')

        for field in self.data_fields:
            if field.required:
                # Kontrola podle output_column
                if isinstance(field.output_column, list):
                    # Více sloupců - všechny musí být vyplněné
                    for col in field.output_column:
                        value = row.get(col)
                        if value is None or value == null_value or value == '':
                            return False
                else:
                    # Jeden sloupec
                    value = row.get(field.output_column)
                    if value is None or value == null_value or value == '':
                        return False

        return True

    def deduplicate(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Odstraní duplicitní záznamy.

        Args:
            data: Seznam záznamů

        Returns:
            Seznam bez duplikátů
        """
        if not data:
            return data

        logger.info("🔍 Odstraňuji duplicity...")

        # Použití wikidata_id jako unikátní klíč
        seen_ids: Set[str] = set()
        unique_data = []

        for row in data:
            wikidata_id = row.get('wikidata_id', '')

            if wikidata_id and wikidata_id not in seen_ids:
                seen_ids.add(wikidata_id)
                unique_data.append(row)

        removed_count = len(data) - len(unique_data)
        if removed_count > 0:
            logger.info(f"✅ Odstraněno {removed_count} duplikátů")

        return unique_data

    def build_hierarchy(self, row: Dict[str, Any]) -> Dict[str, str]:
        """
        Sestaví hierarchii správních jednotek pro záznam.

        Args:
            row: Záznam

        Returns:
            Slovník s hierarchií
        """
        hierarchy = {}

        hierarchy_config = self.config.get('administrative_hierarchy', default=[])
        for level_data in hierarchy_config:
            level = level_data['level']
            name = level_data['name']
            col_name = f"admin_level_{level}"

            hierarchy[name] = row.get(col_name, '')

        return hierarchy

    def get_processing_stats(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Získá statistiky zpracovaných dat.

        Args:
            data: Zpracovaná data

        Returns:
            Slovník se statistikami
        """
        if not data:
            return {
                'total_records': 0,
                'missing_fields': {}
            }

        null_value = self.config.get('output', 'null_value', default='')

        # Počet chybějících hodnot pro každé pole
        missing_counts = {}

        for field in self.data_fields:
            if isinstance(field.output_column, list):
                for col in field.output_column:
                    missing_counts[col] = sum(
                        1 for row in data
                        if row.get(col) in [None, null_value, '']
                    )
            else:
                col = field.output_column
                missing_counts[col] = sum(
                    1 for row in data
                    if row.get(col) in [None, null_value, '']
                )

        return {
            'total_records': len(data),
            'missing_fields': {
                field: count for field, count in missing_counts.items()
                if count > 0
            }
        }
