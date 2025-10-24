"""
SPARQL Query Builder pro Wikidata dotazy
"""

from typing import List, Dict, Any, Optional


class SPARQLQueryBuilder:
    """Stavitel SPARQL dotazů pro Wikidata API"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.country_id = config['country']['wikidata_id']
        self.data_fields = config['data_fields']
        self.settlement_types = self._get_settlement_types()
        self.language_codes = config.get('country', {}).get('language_codes', ['en'])
    
    def build_query(self) -> str:
        """
        Sestaví kompletní SPARQL dotaz podle konfigurace
        
        Returns:
            SPARQL dotaz jako string
        """
        select_vars = self._build_select_variables()
        where_clauses = self._build_where_clauses()
        optional_clauses = self._build_optional_clauses()
        filters = self._build_filters()
        service_clause = self._build_service_clause()
        
        query_parts = [
            f"SELECT {select_vars} WHERE {{",
            *where_clauses,
            *optional_clauses,
            *filters,
            service_clause,
            "}"
        ]
        
        # Přidat LIMIT pokud je nakonfigurován
        query_config = self.config.get('query', {})
        if query_config.get('limit'):
            query_parts.append(f"LIMIT {query_config['limit']}")
        
        return "\n".join(filter(None, query_parts))
    
    def _build_select_variables(self) -> str:
        """Sestaví SELECT část dotazu"""
        variables = []
        
        for field in self.data_fields:
            field_name = field['field']
            
            if field_name == 'item_id':
                variables.append('?item')
            elif field.get('wikidata_property') == 'rdfs:label':
                variables.append('?itemLabel')
            else:
                variables.append(f'?{field_name}')
        
        return " ".join(variables)
    
    def _build_where_clauses(self) -> List[str]:
        """Sestaví povinné WHERE klauzule"""
        clauses = []
        
        # Typ sídla
        if len(self.settlement_types) == 1:
            clauses.append(f"  ?item wdt:P31 wd:{self.settlement_types[0]} .")
        else:
            # Více typů - použít VALUES
            types_str = " ".join([f"wd:{t}" for t in self.settlement_types])
            clauses.append("  VALUES ?type { " + types_str + " }")
            clauses.append("  ?item wdt:P31 ?type .")
        
        # Země
        clauses.append(f"  ?item wdt:P17 wd:{self.country_id} .")
        
        return clauses
    
    def _build_optional_clauses(self) -> List[str]:
        """Sestaví OPTIONAL klauzule pro volitelná pole"""
        clauses = []
        
        for field in self.data_fields:
            field_name = field['field']
            property_id = field.get('wikidata_property')
            
            # Přeskočit speciální pole
            if field_name == 'item_id' or property_id == 'rdfs:label':
                continue
            
            if not field.get('required', False) and property_id:
                # Speciální handling pro koordináty
                if property_id == 'P625' and field.get('format') == 'lat_lon_split':
                    clauses.append(f"  OPTIONAL {{ ?item wdt:{property_id} ?{field_name} }}")
                    # Přidat binding pro rozdělení lat/lon - zatím základní verze
                # Speciální handling pro administrativní jednotky
                elif field.get('administrative_level'):
                    clauses.append(f"  OPTIONAL {{ ?item wdt:{property_id} ?{field_name}_admin . ?{field_name}_admin rdfs:label ?{field_name} . FILTER(LANG(?{field_name}) = \"en\") }}")
                else:
                    clauses.append(f"  OPTIONAL {{ ?item wdt:{property_id} ?{field_name} }}")
        
        # Povinná pole (kromě speciálních)
        for field in self.data_fields:
            field_name = field['field']
            property_id = field.get('wikidata_property')
            
            if field.get('required', False) and property_id and property_id != 'rdfs:label':
                if field.get('administrative_level'):
                    clauses.append(f"  ?item wdt:{property_id} ?{field_name}_admin . ?{field_name}_admin rdfs:label ?{field_name} . FILTER(LANG(?{field_name}) = \"en\")")
                else:
                    clauses.append(f"  ?item wdt:{property_id} ?{field_name} .")
        
        return clauses
    
    def _build_filters(self) -> List[str]:
        """Sestaví FILTER klauzule"""
        filters = []
        filter_config = self.config.get('filters', {})
        
        # Filtr podle koordinátů
        if filter_config.get('coordinates_required', False):
            coord_field = self._find_field_by_property('P625')
            if coord_field:
                field_name = coord_field['field']
                filters.append(f"  FILTER(BOUND(?{field_name}))")
        
        # Filtr podle populace
        population_filter = filter_config.get('population', {})
        if population_filter.get('min') or population_filter.get('max'):
            pop_field = self._find_field_by_property('P1082')
            if pop_field:
                field_name = pop_field['field']
                if population_filter.get('min'):
                    filters.append(f"  FILTER(?{field_name} >= {population_filter['min']})")
                if population_filter.get('max'):
                    filters.append(f"  FILTER(?{field_name} <= {population_filter['max']})")
        
        return filters
    
    def _build_service_clause(self) -> str:
        """Sestaví SERVICE klauzuli pro labels"""
        query_config = self.config.get('query', {})
        if not query_config.get('enable_service_timeout', True):
            return ""
        
        # Sestavit jazyky
        lang_str = ",".join(self.language_codes)
        return f'  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang_str}" . }}'
    
    def _get_settlement_types(self) -> List[str]:
        """Získá seznam typů sídel z konfigurace"""
        settlement_types = self.config.get('settlement_types', {})
        include = settlement_types.get('include', ['Q486972'])  # human settlement default
        exclude = settlement_types.get('exclude', [])
        
        return [t for t in include if t not in exclude]
    
    def _find_field_by_property(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Najde pole podle wikidata_property"""
        for field in self.data_fields:
            if field.get('wikidata_property') == property_id:
                return field
        return None
    
    def get_query_metadata(self) -> Dict[str, Any]:
        """Vrátí metadata o sestaveném dotazu"""
        return {
            'country': self.country_id,
            'settlement_types': self.settlement_types,
            'field_count': len(self.data_fields),
            'has_filters': bool(self.config.get('filters')),
            'languages': self.language_codes
        }