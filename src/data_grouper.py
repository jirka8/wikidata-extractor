"""
Data Grouping funkcionalita pro Wikidata Extractor
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict, OrderedDict


class DataGrouper:
    """Třída pro seskupování dat podle administrativních jednotek"""
    
    def __init__(self, grouping_config: Dict[str, Any]):
        self.grouping_config = grouping_config
        self.enabled = grouping_config.get('enabled', False)
        self.group_by = grouping_config.get('group_by', 'none')
        self.sort_by = grouping_config.get('sort_by', 'name')
        self.include_totals = grouping_config.get('include_totals', False)
    
    def group_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Seskupí data podle konfigurace
        
        Args:
            data: Seznam řádků dat z Wikidata API
            
        Returns:
            Seskupená data (může zahrnovat separátory skupin)
        """
        if not self.enabled or self.group_by == 'none' or not data:
            return self._sort_data(data)
        
        # Seskupit data podle zadaného pole
        groups = self._create_groups(data)
        
        # Seřadit skupiny
        sorted_groups = self._sort_groups(groups)
        
        # Sestavit finální výstup s možnými separátory
        result = []
        for group_name, group_data in sorted_groups.items():
            # Přidat separátor skupiny (prázdný řádek s názvem skupiny)
            if len(sorted_groups) > 1:  # Pouze pokud je více skupin
                separator = self._create_group_separator(group_name, len(group_data))
                result.append(separator)
            
            # Přidat seřazená data skupiny
            sorted_group_data = self._sort_data(group_data)
            result.extend(sorted_group_data)
            
            # Přidat totály pokud je požadováno
            if self.include_totals and len(group_data) > 1:
                total_row = self._create_total_row(group_name, group_data)
                if total_row:
                    result.append(total_row)
        
        return result
    
    def _create_groups(self, data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Vytvoří skupiny podle group_by pole"""
        groups = defaultdict(list)
        
        for row in data:
            group_value = row.get(self.group_by, 'Nezařazeno')
            if not group_value or group_value == '':
                group_value = 'Nezařazeno'
            groups[str(group_value)].append(row)
        
        return dict(groups)
    
    def _sort_groups(self, groups: Dict[str, List[Dict[str, Any]]]) -> OrderedDict:
        """Seřadí skupiny podle názvu"""
        return OrderedDict(sorted(groups.items()))
    
    def _sort_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Seřadí data podle sort_by konfigurace"""
        if not data:
            return data
        
        # Najít správný klíč pro řazení
        sort_key = 'itemLabel'  # default pro name
        if self.sort_by == 'population':
            sort_key = 'population'
        
        # Seřadit s handling prázdných hodnot
        def sort_func(item):
            value = item.get(sort_key, '')
            if self.sort_by == 'population':
                try:
                    return int(value) if value else 0
                except (ValueError, TypeError):
                    return 0
            else:
                return str(value).lower()
        
        return sorted(data, key=sort_func, reverse=(self.sort_by == 'population'))
    
    def _create_group_separator(self, group_name: str, count: int) -> Dict[str, Any]:
        """Vytvoří separátor skupiny (pro rozpoznání v CSV exportu)"""
        return {
            '_group_separator': True,
            '_group_name': group_name,
            '_group_count': count,
            'itemLabel': f"=== {group_name} ({count} položek) ===",
            # Ostatní pole prázdná
            'item': '',
            'coordinates': '',
            'postal_code': '',
            'population': '',
            self.group_by: group_name
        }
    
    def _create_total_row(self, group_name: str, group_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Vytvoří řádek s totály pro skupinu"""
        if not group_data:
            return None
        
        # Spočítat celkovou populaci
        total_population = 0
        valid_population_count = 0
        
        for row in group_data:
            pop_value = row.get('population', '')
            if pop_value:
                try:
                    total_population += int(pop_value)
                    valid_population_count += 1
                except (ValueError, TypeError):
                    pass
        
        if valid_population_count == 0:
            return None  # Žádné validní populační data
        
        return {
            '_total_row': True,
            '_group_name': group_name,
            'itemLabel': f"CELKEM {group_name}",
            'item': '',
            'coordinates': '',
            'postal_code': '',
            'population': str(total_population),
            self.group_by: group_name
        }
    
    def is_enabled(self) -> bool:
        """Vrátí True pokud je seskupování povoleno"""
        return self.enabled and self.group_by != 'none'
    
    def get_grouping_info(self) -> Dict[str, Any]:
        """Vrátí informace o konfiguraci seskupování"""
        return {
            'enabled': self.enabled,
            'group_by': self.group_by,
            'sort_by': self.sort_by,
            'include_totals': self.include_totals
        }