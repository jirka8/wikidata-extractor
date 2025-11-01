"""SPARQL dotaz builder pro WikiData extrakci."""

from typing import List, Dict, Any, Set
import logging
from .config_manager import Config, DataField


logger = logging.getLogger('WikiDataExtractor.QueryBuilder')


class SPARQLQueryBuilder:
    """Sestavení SPARQL dotazů podle konfigurace."""

    def __init__(self, config: Config):
        """
        Inicializace query builderu.

        Args:
            config: Konfigurace projektu
        """
        self.config = config
        self.data_fields = config.get_data_fields()

    def build_query(self) -> str:
        """
        Sestaví kompletní SPARQL dotaz podle konfigurace.

        Returns:
            SPARQL dotaz jako string
        """
        logger.info("🔨 Sestavuji SPARQL dotaz...")

        # Části dotazu
        select_clause = self._build_select_clause()
        where_clause = self._build_where_clause()
        filter_clause = self._build_filter_clause()

        # Sestavení finálního dotazu
        query = f"""
{select_clause}
WHERE {{
{where_clause}
{filter_clause}
  SERVICE wikibase:label {{
    bd:serviceParam wikibase:language "{self.config.get('country', 'language')},en" .
  }}
}}
ORDER BY ?settlementLabel
"""

        logger.info(f"✅ SPARQL dotaz sestaven ({len(query)} znaků)")
        return query.strip()

    def _build_select_clause(self) -> str:
        """Sestaví SELECT klauzuli s proměnnými."""
        variables: Set[str] = set()

        # Základní proměnné
        variables.add('?settlement')
        variables.add('?settlementLabel')

        # Proměnné z datových polí
        for field in self.data_fields:
            var_name = self._field_to_variable(field)

            # Koordináty se rozdělují na lat a lon
            if field.field_name == 'coordinates':
                variables.add('?lat')
                variables.add('?lon')
            else:
                variables.add(var_name)

            # Pro P31 (instance of) přidáme i label
            if field.wikidata_property == 'P31':
                variables.add(f'{var_name}Label')

        # Přidání proměnných pro administrativní hierarchii
        hierarchy = self.config.get('administrative_hierarchy', default=[])
        for level_data in hierarchy:
            level = level_data['level']
            variables.add(f'?admin{level}')
            variables.add(f'?admin{level}Label')

        # Sestavení SELECT řádku
        vars_list = sorted(list(variables))
        select_line = f"SELECT DISTINCT {' '.join(vars_list)}"

        return select_line

    def _build_where_clause(self) -> str:
        """Sestaví WHERE klauzuli s triple patterns."""
        patterns = []

        # Základní omezení - země
        country_qid = self.config.get('country', 'wikidata_qid')
        patterns.append(f"  ?settlement wdt:P17 wd:{country_qid} .")

        # Typy sídel
        settlement_types = self.config.get('settlement_types', default=[])
        if settlement_types:
            type_qids = [st['wikidata_qid'] for st in settlement_types]
            values_line = ' '.join([f'wd:{qid}' for qid in type_qids])
            patterns.append(f"  VALUES ?type {{ {values_line} }}")
            patterns.append(f"  ?settlement wdt:P31/wdt:P279* ?type .")

        # Povinná a volitelná pole
        for field in self.data_fields:
            pattern = self._field_to_pattern(field)
            if pattern:
                patterns.append(pattern)

        # Administrativní hierarchie
        hierarchy_pattern = self._build_hierarchy_pattern()
        if hierarchy_pattern:
            patterns.append(hierarchy_pattern)

        return '\n'.join(patterns)

    def _build_filter_clause(self) -> str:
        """Sestaví FILTER klauzuli."""
        filters = []

        # Populace filtry
        min_pop = self.config.get('filters', 'min_population')
        max_pop = self.config.get('filters', 'max_population')

        if min_pop is not None:
            filters.append(f"  FILTER(?population >= {min_pop})")

        if max_pop is not None:
            filters.append(f"  FILTER(?population <= {max_pop})")

        # Bounding box
        bbox = self.config.get('filters', 'bounding_box')
        if bbox and len(bbox) == 4:
            lat_min, lon_min, lat_max, lon_max = bbox
            filters.append(f"  FILTER(?lat >= {lat_min} && ?lat <= {lat_max})")
            filters.append(f"  FILTER(?lon >= {lon_min} && ?lon <= {lon_max})")

        # Vyloučení historických sídel
        if self.config.get('filters', 'exclude_historical'):
            # Přidání filtru pro vyloučení instance of "former municipality" atd.
            filters.append("  # Vyloučení historických sídel")
            filters.append("  FILTER NOT EXISTS { ?settlement wdt:P31 wd:Q19730508 }")  # former municipality

        return '\n'.join(filters) if filters else ''

    def _field_to_variable(self, field: DataField) -> str:
        """Převede pole na SPARQL proměnnou."""
        # Speciální případy
        if field.wikidata_property == 'SUBJECT':
            return '?settlement'
        if field.field_name == 'settlement_type':
            return '?type'

        # Standardní pole
        return f'?{field.field_name}'

    def _field_to_pattern(self, field: DataField) -> str:
        """Vytvoří triple pattern pro datové pole."""
        var = self._field_to_variable(field)
        prop = field.wikidata_property

        # Speciální případy
        if prop == 'SUBJECT':
            return None  # ?settlement už je definováno výše

        if prop == 'rdfs:label':
            # Label se získává přes SERVICE wikibase:label
            return None

        if prop == 'P31':  # Instance of
            return None  # Už definováno v types

        # Coordinates - speciální handling
        if field.field_name == 'coordinates' and prop == 'P625':
            if field.required:
                return f"""  ?settlement wdt:{prop} ?coord .
  BIND(geof:latitude(?coord) AS ?lat)
  BIND(geof:longitude(?coord) AS ?lon)"""
            else:
                return f"""  OPTIONAL {{
    ?settlement wdt:{prop} ?coord .
    BIND(geof:latitude(?coord) AS ?lat)
    BIND(geof:longitude(?coord) AS ?lon)
  }}"""

        # Standardní pole
        if field.required:
            return f"  ?settlement wdt:{prop} {var} ."
        else:
            return f"  OPTIONAL {{ ?settlement wdt:{prop} {var} . }}"

    def _build_hierarchy_pattern(self) -> str:
        """Sestaví pattern pro administrativní hierarchii."""
        hierarchy = self.config.get('administrative_hierarchy', default=[])
        if not hierarchy:
            return ''

        patterns = []
        patterns.append("  # Administrativní hierarchie")
        patterns.append("  OPTIONAL {")

        # Řazení hierarchie podle úrovně
        sorted_hierarchy = sorted(hierarchy, key=lambda x: x['level'])

        # Sestavení vzorů pro každou úroveň
        prev_var = '?settlement'
        for i, level_data in enumerate(sorted_hierarchy):
            level = level_data['level']
            prop = level_data['wikidata_property']
            instance_of = level_data.get('wikidata_instance_of')

            current_var = f'?admin{level}'

            # Propojení s předchozí úrovní
            patterns.append(f"    {prev_var} wdt:{prop} {current_var} .")

            # Instance of constraint
            if instance_of:
                if isinstance(instance_of, list):
                    values = ' '.join([f'wd:{qid}' for qid in instance_of])
                    patterns.append(f"    {current_var} wdt:P31 ?admin{level}Type .")
                    patterns.append(f"    VALUES ?admin{level}Type {{ {values} }}")
                else:
                    patterns.append(f"    {current_var} wdt:P31 wd:{instance_of} .")

            prev_var = current_var

        patterns.append("  }")

        return '\n'.join(patterns)

    def get_query_info(self) -> Dict[str, Any]:
        """
        Vrací informace o dotazu.

        Returns:
            Slovník s metadaty dotazu
        """
        return {
            'country': self.config.get('country', 'name'),
            'country_qid': self.config.get('country', 'wikidata_qid'),
            'fields_count': len(self.data_fields),
            'required_fields': len([f for f in self.data_fields if f.required]),
            'optional_fields': len([f for f in self.data_fields if not f.required]),
            'has_hierarchy': len(self.config.get('administrative_hierarchy', default=[])) > 0,
            'has_filters': bool(self.config.get('filters', 'min_population') or
                              self.config.get('filters', 'max_population') or
                              self.config.get('filters', 'bounding_box'))
        }
