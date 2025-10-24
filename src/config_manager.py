"""
Správa konfigurace pro Wikidata Extractor
"""

import os
import re
import yaml
from typing import Dict, List, Any, Optional


class ConfigValidationError(Exception):
    """Chyba při validaci konfigurace"""
    pass


class ConfigManager:
    """Správce konfigurace - načítání a validace konfiguračních souborů"""
    
    def __init__(self):
        self.config = None
        self._wikidata_id_pattern = re.compile(r'^Q[0-9]+$')
        self._property_id_pattern = re.compile(r'^P[0-9]+$')
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Načte konfiguraci ze souboru
        
        Args:
            config_path: Cesta ke konfiguračnímu souboru
            
        Returns:
            Slovník s konfigurací
            
        Raises:
            ConfigValidationError: Chyba při validaci
            FileNotFoundError: Soubor neexistuje
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Konfigurační soubor nenalezen: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Chyba při parsování YAML: {e}")
        
        self.config = config
        self._validate_config()
        return config
    
    def _validate_config(self):
        """Validuje načtenou konfiguraci"""
        if not self.config:
            raise ConfigValidationError("Prázdná konfigurace")
        
        self._validate_country()
        self._validate_data_fields()
        self._validate_output()
        self._validate_dependencies()
    
    def _validate_country(self):
        """Validuje sekci country"""
        if 'country' not in self.config:
            raise ConfigValidationError("Chybí sekce 'country'")
        
        country = self.config['country']
        if 'wikidata_id' not in country:
            raise ConfigValidationError("Chybí 'country.wikidata_id'")
        
        wikidata_id = country['wikidata_id']
        if not self._wikidata_id_pattern.match(wikidata_id):
            raise ConfigValidationError(
                f"Neplatné Wikidata ID: {wikidata_id}. Očekáván formát Q[číslo]"
            )
    
    def _validate_data_fields(self):
        """Validuje sekci data_fields"""
        if 'data_fields' not in self.config:
            raise ConfigValidationError("Chybí sekce 'data_fields'")
        
        data_fields = self.config['data_fields']
        if not data_fields or len(data_fields) == 0:
            raise ConfigValidationError("Sekce 'data_fields' nesmí být prázdná")
        
        required_fields = []
        for i, field in enumerate(data_fields):
            if 'field' not in field:
                raise ConfigValidationError(f"Pole #{i}: chybí 'field'")
            
            # Validace wikidata_property
            if 'wikidata_property' in field and field['wikidata_property']:
                prop = field['wikidata_property']
                if prop != 'rdfs:label' and not self._property_id_pattern.match(prop):
                    raise ConfigValidationError(
                        f"Pole '{field['field']}': neplatná property {prop}"
                    )
            
            # Sledování povinných polí
            if field.get('required', False):
                required_fields.append(field['field'])
        
        if not required_fields:
            raise ConfigValidationError("Alespoň jedno pole musí být povinné")
    
    def _validate_output(self):
        """Validuje sekci output"""
        if 'output' not in self.config:
            raise ConfigValidationError("Chybí sekce 'output'")
        
        output = self.config['output']
        if 'filename' not in output or not output['filename']:
            raise ConfigValidationError("Chybí nebo prázdný 'output.filename'")
        
        # Kontrola platnosti názvu souboru
        filename = output['filename']
        if any(char in filename for char in ['<', '>', ':', '"', '|', '?', '*']):
            raise ConfigValidationError(f"Neplatný název souboru: {filename}")
    
    def _validate_dependencies(self):
        """Validuje vzájemné závislosti v konfiguraci"""
        # Pokud coordinates_required: true, pak coordinates musí být required
        filters = self.config.get('filters', {})
        if filters.get('coordinates_required', False):
            coord_field = self._find_field_by_property('P625')
            if not coord_field or not coord_field.get('required', False):
                raise ConfigValidationError(
                    "Pokud 'filters.coordinates_required' je true, "
                    "pole 'coordinates' musí být required"
                )
    
    def _find_field_by_property(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Najde pole podle wikidata_property"""
        for field in self.config.get('data_fields', []):
            if field.get('wikidata_property') == property_id:
                return field
        return None
    
    def get_country_id(self) -> str:
        """Vrátí Wikidata ID země"""
        return self.config['country']['wikidata_id']
    
    def get_data_fields(self) -> List[Dict[str, Any]]:
        """Vrátí seznam datových polí"""
        return self.config['data_fields']
    
    def get_output_config(self) -> Dict[str, Any]:
        """Vrátí konfiguraci výstupu"""
        return self.config.get('output', {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """Vrátí konfiguraci API"""
        defaults = {
            'endpoint': 'https://query.wikidata.org/sparql',
            'timeout': 30,
            'retry_attempts': 3,
            'retry_delay': 5,
            'user_agent': 'WikidataExtractor/1.0',
            'rate_limit': 60
        }
        return {**defaults, **self.config.get('api', {})}
    
    def get_settlement_types(self) -> List[str]:
        """Vrátí seznam typů sídel k zahrnutí"""
        settlement_types = self.config.get('settlement_types', {})
        include = settlement_types.get('include', ['Q486972'])  # human settlement
        exclude = settlement_types.get('exclude', [])
        
        # Filtrovat vyloučené typy
        return [t for t in include if t not in exclude]