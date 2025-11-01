"""Správa konfigurace pro WikiData Extraktor."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Union
import yaml
import logging
from pathlib import Path
import jsonschema


logger = logging.getLogger('WikiDataExtractor.Config')


@dataclass
class DataField:
    """Reprezentace datového pole pro extrakci."""
    field_name: str
    wikidata_property: str
    required: bool
    output_column: Union[str, List[str]]
    data_type: Optional[str] = None
    language_filter: Optional[str] = None
    description: Optional[str] = None


class ConfigValidator:
    """Validace konfiguračních souborů."""

    # JSON Schema pro validaci konfigurace
    CONFIG_SCHEMA = {
        "type": "object",
        "required": ["country", "data_fields", "output"],
        "properties": {
            "country": {
                "type": "object",
                "required": ["name", "wikidata_qid", "iso_code", "language"],
                "properties": {
                    "name": {"type": "string"},
                    "wikidata_qid": {"type": "string", "pattern": "^Q[0-9]+$"},
                    "iso_code": {"type": "string"},
                    "language": {"type": "string"}
                }
            },
            "administrative_hierarchy": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["level", "name", "wikidata_property"],
                    "properties": {
                        "level": {"type": "integer"},
                        "name": {"type": "string"},
                        "wikidata_property": {"type": "string"},
                        "wikidata_instance_of": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}}
                            ]
                        }
                    }
                }
            },
            "settlement_types": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "wikidata_qid", "label"],
                    "properties": {
                        "type": {"type": "string"},
                        "wikidata_qid": {"type": "string", "pattern": "^Q[0-9]+$"},
                        "label": {"type": "string"}
                    }
                }
            },
            "data_fields": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["field_name", "wikidata_property", "required", "output_column"],
                    "properties": {
                        "field_name": {"type": "string"},
                        "wikidata_property": {"type": "string"},
                        "required": {"type": "boolean"},
                        "output_column": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}}
                            ]
                        },
                        "data_type": {"type": "string"},
                        "language_filter": {"type": "string"},
                        "description": {"type": "string"}
                    }
                }
            },
            "filters": {
                "type": "object",
                "properties": {
                    "min_population": {"oneOf": [{"type": "integer"}, {"type": "null"}]},
                    "max_population": {"oneOf": [{"type": "integer"}, {"type": "null"}]},
                    "settlement_types_include": {"type": "array", "items": {"type": "string"}},
                    "exclude_historical": {"type": "boolean"},
                    "bounding_box": {
                        "oneOf": [
                            {"type": "null"},
                            {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}
                        ]
                    }
                }
            },
            "output": {
                "type": "object",
                "required": ["file_path"],
                "properties": {
                    "file_path": {"type": "string"},
                    "encoding": {"type": "string"},
                    "delimiter": {"type": "string"},
                    "include_header": {"type": "boolean"},
                    "date_format": {"type": "string"},
                    "null_value": {"type": "string"}
                }
            },
            "query_settings": {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string"},
                    "timeout": {"type": "integer"},
                    "user_agent": {"type": "string"},
                    "rate_limit_delay": {"type": "number"},
                    "batch_size": {"type": "integer"},
                    "retry_attempts": {"type": "integer"},
                    "strategy": {
                        "type": "string",
                        "enum": ["single_query", "by_admin_level"]
                    },
                    "batch_by_admin_level": {"type": "integer"}
                }
            }
        }
    }

    def validate(self, config_data: Dict[str, Any]) -> bool:
        """
        Validuje konfigurační data proti JSON schema.

        Args:
            config_data: Konfigurace k validaci

        Returns:
            True pokud je konfigurace validní

        Raises:
            jsonschema.ValidationError: Pokud konfigurace není validní
        """
        try:
            jsonschema.validate(instance=config_data, schema=self.CONFIG_SCHEMA)
            logger.info("✅ Konfigurace je validní")

            # Dodatečné validace
            self._validate_qids(config_data)
            self._validate_properties(config_data)
            self._validate_required_fields(config_data)

            return True

        except jsonschema.ValidationError as e:
            logger.error(f"❌ Chyba validace konfigurace: {e.message}")
            raise

    def _validate_qids(self, config_data: Dict[str, Any]) -> None:
        """Validuje WikiData QID formát."""
        qid_fields = [
            ('country', 'wikidata_qid'),
        ]

        for section, field in qid_fields:
            if section in config_data and field in config_data[section]:
                qid = config_data[section][field]
                if not qid.startswith('Q') or not qid[1:].isdigit():
                    raise ValueError(f"Neplatný QID formát: {qid}")

    def _validate_properties(self, config_data: Dict[str, Any]) -> None:
        """Validuje WikiData property formát (P sufix)."""
        if 'data_fields' in config_data:
            for field in config_data['data_fields']:
                prop = field.get('wikidata_property', '')
                # SUBJECT a rdfs:label jsou speciální případy
                if prop not in ['SUBJECT', 'rdfs:label'] and not prop.startswith('P'):
                    logger.warning(f"⚠️ Nestandardní property: {prop}")

    def _validate_required_fields(self, config_data: Dict[str, Any]) -> None:
        """Kontroluje, zda jsou definována povinná pole."""
        if 'data_fields' not in config_data:
            raise ValueError("Chybí sekce 'data_fields'")

        required_fields = [f for f in config_data['data_fields'] if f.get('required', False)]
        if not required_fields:
            logger.warning("⚠️ Žádné pole není označeno jako povinné")


class Config:
    """Načítání a správa konfigurace projektu."""

    def __init__(self, config_path: Union[str, Path]):
        """
        Inicializace konfigurace.

        Args:
            config_path: Cesta ke konfiguračnímu souboru
        """
        self.config_path = Path(config_path)
        self.data: Dict[str, Any] = {}
        self.validator = ConfigValidator()
        self._load()

    def _load(self) -> None:
        """Načte a validuje konfigurační soubor."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Konfigurační soubor nenalezen: {self.config_path}")

        logger.info(f"📂 Načítám konfiguraci: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.data = yaml.safe_load(f)

        # Validace
        self.validator.validate(self.data)

        # Doplnění výchozích hodnot
        self._apply_defaults()

        logger.info(f"✅ Konfigurace načtena: {self.data['country']['name']}")

    def _apply_defaults(self) -> None:
        """Aplikuje výchozí hodnoty pro chybějící konfigurace."""
        defaults = {
            'query_settings': {
                'endpoint': 'https://query.wikidata.org/sparql',
                'timeout': 300,
                'user_agent': 'WikiDataExtractor/1.0',
                'rate_limit_delay': 1.0,
                'batch_size': 1000,
                'retry_attempts': 3,
                'strategy': 'single_query'
            },
            'output': {
                'encoding': 'utf-8-sig',
                'delimiter': ',',
                'include_header': True,
                'date_format': '%Y-%m-%d',
                'null_value': ''
            },
            'filters': {
                'min_population': None,
                'max_population': None,
                'settlement_types_include': [],
                'exclude_historical': True,
                'bounding_box': None
            }
        }

        for section, values in defaults.items():
            if section not in self.data:
                self.data[section] = values
            else:
                for key, value in values.items():
                    if key not in self.data[section]:
                        self.data[section][key] = value

    def get_data_fields(self) -> List[DataField]:
        """
        Vrací seznam datových polí jako DataField objekty.

        Returns:
            Seznam DataField objektů
        """
        fields = []
        for field_data in self.data.get('data_fields', []):
            fields.append(DataField(
                field_name=field_data['field_name'],
                wikidata_property=field_data['wikidata_property'],
                required=field_data['required'],
                output_column=field_data['output_column'],
                data_type=field_data.get('data_type'),
                language_filter=field_data.get('language_filter'),
                description=field_data.get('description')
            ))
        return fields

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Získá hodnotu z konfigurace pomocí tečkové notace.

        Args:
            *keys: Klíče k hodnotě (např. 'country', 'name')
            default: Výchozí hodnota pokud klíč neexistuje

        Returns:
            Hodnota z konfigurace nebo default
        """
        value = self.data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value
