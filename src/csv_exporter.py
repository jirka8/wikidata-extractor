"""
CSV export funkcionalita pro Wikidata Extractor
"""

import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from data_grouper import DataGrouper


class CSVExportError(Exception):
    """Chyba při exportu do CSV"""
    pass


class CSVExporter:
    """Exportér dat do CSV formátu"""
    
    def __init__(self, config: Dict[str, Any]):
        self.output_config = config
        self.data_fields_config = []  # Bude nastaveno při exportu
        self.grouper = None  # Bude nastaveno při exportu
    
    def export_data(self, data: List[Dict[str, Any]], 
                   data_fields_config: List[Dict[str, Any]],
                   grouping_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Exportuje data do CSV souboru
        
        Args:
            data: Seznam výsledků z Wikidata API
            data_fields_config: Konfigurace datových polí
            grouping_config: Konfigurace seskupování (volitelné)
            
        Returns:
            Cesta k vytvořenému CSV souboru
            
        Raises:
            CSVExportError: Chyba při exportu
        """
        self.data_fields_config = data_fields_config
        
        # Inicializovat grouper pokud je konfigurace poskytnutá
        if grouping_config:
            self.grouper = DataGrouper(grouping_config)
            if self.grouper.is_enabled():
                data = self.grouper.group_data(data)
        
        # Sestavit cestu k výstupnímu souboru
        output_path = self._get_output_path()
        
        # Vytvořit výstupní adresář pokud neexistuje
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            with open(output_path, 'w', newline='', 
                     encoding=self.output_config.get('encoding', 'utf-8')) as csvfile:
                
                self._write_csv_data(csvfile, data)
                
        except Exception as e:
            raise CSVExportError(f"Chyba při zápisu CSV: {e}")
        
        return output_path
    
    def _get_output_path(self) -> str:
        """Sestaví kompletní cestu k výstupnímu souboru"""
        directory = self.output_config.get('directory', './output')
        filename = self.output_config['filename']
        
        # Přidat datum k názvu souboru pokud je požadováno
        if self.output_config.get('date_suffix', False):
            name, ext = os.path.splitext(filename)
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{name}_{date_str}{ext}"
        
        return os.path.join(directory, filename)
    
    def _write_csv_data(self, csvfile, data: List[Dict[str, Any]]):
        """Zapíše data do CSV souboru"""
        if not data:
            # Prázdný soubor s header
            if self.output_config.get('include_headers', True):
                headers = self._get_csv_headers()
                writer = csv.writer(csvfile, delimiter=self.output_config.get('delimiter', ','))
                writer.writerow(headers)
            return
        
        # Získat hlavičky
        headers = self._get_csv_headers()
        field_mapping = self._get_field_mapping()
        
        writer = csv.writer(csvfile, delimiter=self.output_config.get('delimiter', ','))
        
        # Zapsat hlavičky
        if self.output_config.get('include_headers', True):
            writer.writerow(headers)
        
        # Zapsat data s deduplikací a agregací TOID kódů
        aggregated_data = self._aggregate_duplicate_rows(data)
        
        for row_data in aggregated_data:
            csv_row = self._process_row(row_data, field_mapping, headers)
            writer.writerow(csv_row)
    
    def _get_csv_headers(self) -> List[str]:
        """Vrátí seznam CSV hlaviček"""
        headers = []
        
        for field_config in self.data_fields_config:
            field_name = field_config['field']
            csv_header = field_config.get('csv_header', field_name)
            
            # Speciální handling pro koordináty
            if (field_config.get('wikidata_property') == 'P625' and 
                field_config.get('format') == 'lat_lon_split'):
                if ',' in csv_header:
                    # Rozdělené hlavičky: "lat,lon"
                    headers.extend(csv_header.split(','))
                else:
                    # Fallback
                    headers.extend([f"{csv_header}_lat", f"{csv_header}_lon"])
            else:
                headers.append(csv_header)
        
        return headers
    
    def _get_field_mapping(self) -> Dict[str, str]:
        """Vytvoří mapování mezi API poli a konfiguračními poli"""
        mapping = {}
        
        for field_config in self.data_fields_config:
            field_name = field_config['field']
            
            if field_name == 'item_id':
                mapping['item'] = field_name
            elif field_config.get('wikidata_property') == 'rdfs:label':
                mapping['itemLabel'] = field_name
            else:
                mapping[field_name] = field_name
        
        return mapping
    
    def _process_row(self, row_data: Dict[str, Any], 
                    field_mapping: Dict[str, str], 
                    headers: List[str]) -> List[str]:
        """Zpracuje jeden řádek dat pro CSV"""
        csv_row = []
        header_index = 0
        
        for field_config in self.data_fields_config:
            field_name = field_config['field']
            
            # Najít odpovídající hodnotu v datech
            api_field = None
            for api_key, config_field in field_mapping.items():
                if config_field == field_name:
                    api_field = api_key
                    break
            
            value = row_data.get(api_field, '') if api_field else ''
            
            # Speciální zpracování podle typu pole
            processed_values = self._process_field_value(value, field_config)
            
            # Přidat hodnoty do řádku
            if isinstance(processed_values, list):
                csv_row.extend(processed_values)
                header_index += len(processed_values)
            else:
                csv_row.append(processed_values)
                header_index += 1
        
        return csv_row
    
    def _process_field_value(self, value: str, field_config: Dict[str, Any]) -> List[str]:
        """
        Zpracuje hodnotu pole podle konfigurace
        
        Args:
            value: Surová hodnota z API
            field_config: Konfigurace pole
            
        Returns:
            Zpracovaná hodnota nebo seznam hodnot
        """
        if not value:
            # Prázdná hodnota
            if (field_config.get('wikidata_property') == 'P625' and 
                field_config.get('format') == 'lat_lon_split'):
                return ['', '']  # Dva prázdné sloupce pro lat,lon
            return ['']
        
        # Speciální zpracování koordinátů
        if (field_config.get('wikidata_property') == 'P625' and 
            field_config.get('format') == 'lat_lon_split'):
            return self._process_coordinates(value)
        
        # Standardní hodnota
        return [str(value)]
    
    def _process_coordinates(self, coord_value: str) -> List[str]:
        """
        Zpracuje koordináty z Wikidata formátu
        
        Args:
            coord_value: Koordináty ve formátu "Point(lon lat)"
            
        Returns:
            [latitude, longitude] jako stringy
        """
        try:
            # Očekávaný formát: "Point(longitude latitude)"
            if coord_value.startswith('Point(') and coord_value.endswith(')'):
                coords = coord_value[6:-1]  # Odstranit "Point(" a ")"
                parts = coords.split()
                if len(parts) == 2:
                    longitude, latitude = parts
                    return [latitude, longitude]  # CSV: lat, lon
            
            # Fallback - vrátit původní hodnotu do obou sloupců
            return [coord_value, '']
            
        except Exception:
            return ['', '']
    
    def get_export_statistics(self, output_path: str) -> Dict[str, Any]:
        """Vrátí statistiky o exportovaném souboru"""
        if not os.path.exists(output_path):
            return {'error': 'Soubor neexistuje'}
        
        try:
            file_size = os.path.getsize(output_path)
            
            # Spočítat řádky
            with open(output_path, 'r', encoding=self.output_config.get('encoding', 'utf-8')) as f:
                line_count = sum(1 for line in f)
            
            # Odečíst hlavičku pokud existuje
            data_rows = line_count - (1 if self.output_config.get('include_headers', True) else 0)
            
            return {
                'file_path': output_path,
                'file_size_bytes': file_size,
                'total_lines': line_count,
                'data_rows': data_rows,
                'headers_included': self.output_config.get('include_headers', True),
                'encoding': self.output_config.get('encoding', 'utf-8'),
                'delimiter': self.output_config.get('delimiter', ',')
            }
            
        except Exception as e:
            return {'error': f'Chyba při analýze souboru: {e}'}
    
    def _create_dedup_key(self, row_data: Dict[str, Any], field_mapping: Dict[str, str]) -> str:
        """
        Vytvoří klíč pro deduplikaci řádků
        
        Args:
            row_data: Data řádku
            field_mapping: Mapování polí
            
        Returns:
            Deduplikační klíč jako string
        """
        # Klíčová pole pro deduplikaci (bez TOID a podobných variabilních polí)
        key_fields = ['item', 'itemLabel', 'coords', 'adminLabel', 'nutsCode']
        key_parts = []
        
        for field in key_fields:
            value = row_data.get(field, '')
            # Normalizovat hodnotu
            if isinstance(value, str):
                value = value.strip()
            key_parts.append(str(value))
        
        return '|'.join(key_parts)
    
    def _aggregate_duplicate_rows(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Agreguje duplicitní řádky a spojí TOID kódy
        
        Args:
            data: Seznam dat
            
        Returns:
            Seznam dat bez duplikátů s agregovanými TOID kódy
        """
        # Mapa pro agregaci: dedup_key -> aggregated_row
        aggregated = {}
        
        for row_data in data:
            # Speciální řádky (separátory, totály) nezpracovávat
            if row_data.get('_group_separator') or row_data.get('_total_row'):
                # Pro speciální řádky použít unikátní klíč
                unique_key = f"_special_{len(aggregated)}"
                aggregated[unique_key] = row_data
                continue
            
            # Vytvořit deduplikační klíč
            field_mapping = self._get_field_mapping()
            dedup_key = self._create_dedup_key(row_data, field_mapping)
            
            if dedup_key in aggregated:
                # Sloučit TOID kódy
                existing_toid = aggregated[dedup_key].get('toid', '')
                new_toid = row_data.get('toid', '')
                
                if new_toid and new_toid not in existing_toid:
                    if existing_toid:
                        aggregated[dedup_key]['toid'] = f"{existing_toid}; {new_toid}"
                    else:
                        aggregated[dedup_key]['toid'] = new_toid
            else:
                # Nový záznam
                aggregated[dedup_key] = row_data.copy()
        
        return list(aggregated.values())