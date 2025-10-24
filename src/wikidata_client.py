"""
HTTP klient pro komunikaci s Wikidata API
"""

import time
import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode


class WikidataAPIError(Exception):
    """Chyba při komunikaci s Wikidata API"""
    pass


class WikidataClient:
    """HTTP klient pro Wikidata SPARQL endpoint"""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_config = config
        self.endpoint = self.api_config['endpoint']
        self.timeout = self.api_config['timeout']
        self.retry_attempts = self.api_config['retry_attempts']
        self.retry_delay = self.api_config['retry_delay']
        self.user_agent = self.api_config['user_agent']
        
        # Rate limiting
        self.rate_limit = self.api_config['rate_limit']  # requests per minute
        self.last_request_time = 0
        self.request_interval = 60.0 / self.rate_limit  # seconds between requests
        
        # Session pro connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/sparql-results+json'
        })
    
    def execute_query_batch(self, sparql_query: str, batch_size: int = 1000, 
                           max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Vykoná SPARQL dotaz s automatickým dávkovým stahováním
        
        Args:
            sparql_query: SPARQL dotaz jako string (bez LIMIT)
            batch_size: Velikost dávky pro každý požadavek
            max_results: Maximální počet výsledků (None = všechny)
            
        Returns:
            Seznam všech výsledků jako slovníky
            
        Raises:
            WikidataAPIError: Chyba při dotazu
        """
        all_results = []
        offset = 0
        batch_count = 1
        
        # Odstranit existující LIMIT z dotazu
        base_query = self._remove_limit_from_query(sparql_query)
        
        while True:
            # Sestavit dotaz s OFFSET a LIMIT
            batch_query = f"{base_query}\nLIMIT {batch_size} OFFSET {offset}"
            
            print(f"Stahování dávka {batch_count} (offset {offset}, limit {batch_size})...")
            
            try:
                batch_results = self.execute_query(batch_query)
                
                if not batch_results:
                    print("Žádné další výsledky - dokončeno")
                    break
                
                all_results.extend(batch_results)
                print(f"✓ Dávka {batch_count}: získáno {len(batch_results)} záznamů (celkem {len(all_results)})")
                
                # Kontrola maximálního počtu výsledků
                if max_results and len(all_results) >= max_results:
                    all_results = all_results[:max_results]
                    print(f"Dosažen maximální počet výsledků: {max_results}")
                    break
                
                # Příprava na další dávku
                offset += batch_size
                batch_count += 1
                
                # Bezpečnostní pojistka - maximálně 100 dávek
                if batch_count > 100:
                    print("⚠️ Dosažen maximální počet dávek (100) - ukončuji")
                    break
                
            except WikidataAPIError as e:
                print(f"✗ Chyba v dávce {batch_count}: {e}")
                if len(all_results) > 0:
                    print(f"Vracím částečné výsledky: {len(all_results)} záznamů")
                    break
                else:
                    raise e
        
        return all_results
    
    def execute_query(self, sparql_query: str) -> List[Dict[str, Any]]:
        """
        Vykoná SPARQL dotaz na Wikidata endpoint
        
        Args:
            sparql_query: SPARQL dotaz jako string
            
        Returns:
            Seznam výsledků jako slovníky
            
        Raises:
            WikidataAPIError: Chyba při dotazu
        """
        self._enforce_rate_limit()
        
        for attempt in range(self.retry_attempts + 1):
            try:
                response = self._make_request(sparql_query)
                return self._parse_response(response)
                
            except requests.exceptions.Timeout:
                if attempt < self.retry_attempts:
                    print(f"Timeout - pokus {attempt + 1}/{self.retry_attempts + 1}")
                    time.sleep(self.retry_delay)
                    continue
                raise WikidataAPIError("Dotaz vypršel po všech pokusech")
                
            except requests.exceptions.RequestException as e:
                if attempt < self.retry_attempts:
                    print(f"HTTP chyba - pokus {attempt + 1}/{self.retry_attempts + 1}: {e}")
                    time.sleep(self.retry_delay)
                    continue
                raise WikidataAPIError(f"HTTP chyba: {e}")
                
            except Exception as e:
                if attempt < self.retry_attempts:
                    print(f"Obecná chyba - pokus {attempt + 1}/{self.retry_attempts + 1}: {e}")
                    time.sleep(self.retry_delay)
                    continue
                raise WikidataAPIError(f"Neočekávaná chyba: {e}")
        
        raise WikidataAPIError("Dotaz selhal po všech pokusech")
    
    def _make_request(self, sparql_query: str) -> requests.Response:
        """Provede HTTP požadavek"""
        params = {
            'query': sparql_query,
            'format': 'json'
        }
        
        # GET request s query parametrem
        url = f"{self.endpoint}?{urlencode(params)}"
        
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        
        return response
    
    def _parse_response(self, response: requests.Response) -> List[Dict[str, Any]]:
        """
        Parsuje JSON odpověď z Wikidata API
        
        Args:
            response: HTTP response objekt
            
        Returns:
            Seznam výsledků jako slovníky
        """
        try:
            data = response.json()
        except ValueError as e:
            raise WikidataAPIError(f"Neplatná JSON odpověď: {e}")
        
        if 'results' not in data or 'bindings' not in data['results']:
            raise WikidataAPIError("Neočekávaný formát odpovědi")
        
        results = []
        for binding in data['results']['bindings']:
            result = {}
            for var, value_obj in binding.items():
                result[var] = self._extract_value(value_obj)
            results.append(result)
        
        return results
    
    def _extract_value(self, value_obj: Dict[str, str]) -> str:
        """
        Extrahuje hodnotu z SPARQL binding objektu
        
        Args:
            value_obj: SPARQL binding objekt
            
        Returns:
            Extrahovaná hodnota jako string
        """
        if 'value' not in value_obj:
            return ""
        
        value = value_obj['value']
        value_type = value_obj.get('type', 'literal')
        
        # Speciální handling pro různé typy
        if value_type == 'uri':
            # Extrahovat Wikidata ID z URI
            if 'wikidata.org/entity/' in value:
                return value.split('/')[-1]
            return value
        
        return value
    
    def _enforce_rate_limit(self):
        """Vynucuje rate limit mezi požadavky"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_interval:
            sleep_time = self.request_interval - time_since_last
            print(f"Rate limiting: čekám {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def test_connection(self) -> bool:
        """
        Otestuje připojení k Wikidata API
        
        Returns:
            True pokud je API dostupné
        """
        test_query = """
        SELECT ?item WHERE {
          ?item wdt:P31 wd:Q515 .
        } LIMIT 1
        """
        
        try:
            results = self.execute_query(test_query)
            return len(results) > 0
        except WikidataAPIError:
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Vrátí statistiky klienta"""
        return {
            'endpoint': self.endpoint,
            'rate_limit': self.rate_limit,
            'timeout': self.timeout,
            'retry_attempts': self.retry_attempts,
            'last_request_time': self.last_request_time
        }
    
    def _remove_limit_from_query(self, query: str) -> str:
        """
        Odstraní LIMIT klauzuli z SPARQL dotazu
        
        Args:
            query: SPARQL dotaz
            
        Returns:
            Dotaz bez LIMIT klauzule
        """
        lines = query.strip().split('\n')
        filtered_lines = []
        
        for line in lines:
            line_stripped = line.strip().upper()
            if not line_stripped.startswith('LIMIT'):
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def close(self):
        """Uzavře HTTP session"""
        self.session.close()