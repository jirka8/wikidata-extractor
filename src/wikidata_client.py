"""WikiData SPARQL klient s rate limiting a retry logikou."""

import time
import logging
from typing import List, Dict, Any, Optional, Callable
from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper.SPARQLExceptions import SPARQLWrapperException, EndPointNotFound, QueryBadFormed
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from tqdm import tqdm

from .config_manager import Config


logger = logging.getLogger('WikiDataExtractor.Client')


class WikiDataClient:
    """Komunikace s WikiData SPARQL endpointem."""

    def __init__(self, config: Config):
        """
        Inicializace WikiData klienta.

        Args:
            config: Konfigurace projektu
        """
        self.config = config
        self.endpoint = config.get('query_settings', 'endpoint')
        self.timeout = config.get('query_settings', 'timeout')
        self.user_agent = config.get('query_settings', 'user_agent')
        self.rate_limit_delay = config.get('query_settings', 'rate_limit_delay')
        self.retry_attempts = config.get('query_settings', 'retry_attempts')
        self.batch_size = config.get('query_settings', 'batch_size')

        # Inicializace SPARQL wrapperu
        self.sparql = SPARQLWrapper(self.endpoint)
        self.sparql.setReturnFormat(JSON)
        self.sparql.setTimeout(self.timeout)

        # Nastavení User-Agent (kompatibilní napříč verzemi)
        self.sparql.addCustomHttpHeader("User-Agent", self.user_agent)

        # Statistiky
        self.total_requests = 0
        self.failed_requests = 0
        self.last_request_time = 0

    def execute_query(self, sparql_query: str) -> Dict[str, Any]:
        """
        Provede SPARQL dotaz s retry logikou.

        Args:
            sparql_query: SPARQL dotaz k provedení

        Returns:
            Výsledky dotazu jako slovník

        Raises:
            Exception: Pokud dotaz selže po všech pokusech
        """
        logger.info("🔍 Provádím SPARQL dotaz...")

        # Nastavení dotazu
        self.sparql.setQuery(sparql_query)

        # Provedení s retry
        result = self._retry_on_failure(
            self._execute_single_query,
            max_attempts=self.retry_attempts
        )

        self.total_requests += 1

        logger.info(f"✅ Dotaz dokončen (celkem požadavků: {self.total_requests})")

        return result

    def _execute_single_query(self) -> Dict[str, Any]:
        """
        Provede jeden SPARQL dotaz.

        Returns:
            Výsledky dotazu

        Raises:
            Různé výjimky při selhání dotazu
        """
        # Rate limiting
        self._apply_rate_limit()

        try:
            # Provedení dotazu
            response = self.sparql.queryAndConvert()

            # Záznam času
            self.last_request_time = time.time()

            return response

        except QueryBadFormed as e:
            logger.error(f"❌ Chybně formovaný dotaz: {e}")
            raise

        except EndPointNotFound as e:
            logger.error(f"❌ Endpoint nenalezen: {e}")
            raise

        except Timeout as e:
            logger.warning(f"⚠️ Timeout dotazu: {e}")
            raise

        except ConnectionError as e:
            logger.warning(f"⚠️ Chyba spojení: {e}")
            raise

        except SPARQLWrapperException as e:
            logger.error(f"❌ SPARQL chyba: {e}")
            raise

        except RequestException as e:
            logger.error(f"❌ HTTP chyba: {e}")
            raise

        except Exception as e:
            logger.error(f"❌ Neočekávaná chyba: {e}")
            raise

    def fetch_all_data(self, sparql_query: str, show_progress: bool = True) -> List[Dict[str, Any]]:
        """
        Stáhne všechna data s podporou stránkování.

        Args:
            sparql_query: SPARQL dotaz
            show_progress: Zobrazit progress bar

        Returns:
            Seznam všech výsledků
        """
        logger.info("📥 Stahuji všechna data z WikiData...")

        # První dotaz pro zjištění celkového počtu
        results = self.execute_query(sparql_query)
        bindings = results.get('results', {}).get('bindings', [])

        total_count = len(bindings)
        logger.info(f"📊 Nalezeno záznamů: {total_count}")

        # Pro WikiData SPARQL endpoint obvykle není potřeba stránkování,
        # protože vrací všechny výsledky najednou (s limitem ~1M)
        # Ale implementujeme podporu pro budoucí rozšíření

        all_results = bindings

        if total_count == 0:
            logger.warning("⚠️ Žádné záznamy nenalezeny")

        return all_results

    def _apply_rate_limit(self) -> None:
        """Aplikuje rate limiting mezi požadavky."""
        if self.last_request_time > 0 and self.rate_limit_delay > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - elapsed
                logger.debug(f"💤 Rate limit: čekám {sleep_time:.2f}s")
                time.sleep(sleep_time)

    def _retry_on_failure(
        self,
        func: Callable,
        max_attempts: int,
        *args,
        **kwargs
    ) -> Any:
        """
        Opakuje funkci při selhání s exponenciálním backoff.

        Args:
            func: Funkce k opakování
            max_attempts: Maximální počet pokusů
            *args: Argumenty pro funkci
            **kwargs: Klíčové argumenty pro funkci

        Returns:
            Výsledek funkce

        Raises:
            Exception: Pokud všechny pokusy selžou
        """
        last_exception = None

        for attempt in range(1, max_attempts + 1):
            try:
                return func(*args, **kwargs)

            except (Timeout, ConnectionError, RequestException) as e:
                last_exception = e
                self.failed_requests += 1

                if attempt < max_attempts:
                    # Exponenciální backoff: 2^attempt sekund
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"⚠️ Pokus {attempt}/{max_attempts} selhal: {e}"
                    )
                    logger.info(f"🔄 Opakuji za {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"❌ Všechny pokusy ({max_attempts}) selhaly"
                    )

            except (QueryBadFormed, EndPointNotFound) as e:
                # Tyto chyby nemá smysl opakovat
                logger.error(f"❌ Neopravitelná chyba: {e}")
                raise

        # Pokud se dostaneme sem, všechny pokusy selhaly
        raise last_exception

    def get_statistics(self) -> Dict[str, Any]:
        """
        Vrací statistiky klienta.

        Returns:
            Slovník se statistikami
        """
        success_rate = 0.0
        if self.total_requests > 0:
            success_rate = (
                (self.total_requests - self.failed_requests) / self.total_requests * 100
            )

        return {
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'success_rate': f"{success_rate:.1f}%",
            'endpoint': self.endpoint,
            'timeout': self.timeout,
            'rate_limit_delay': self.rate_limit_delay
        }

    def test_connection(self) -> bool:
        """
        Testuje spojení s WikiData endpointem.

        Returns:
            True pokud spojení funguje
        """
        logger.info("🔌 Testuji spojení s WikiData...")

        test_query = """
        SELECT ?item WHERE {
          ?item wdt:P31 wd:Q5 .
        } LIMIT 1
        """

        try:
            self.execute_query(test_query)
            logger.info("✅ Spojení funkční")
            return True

        except Exception as e:
            logger.error(f"❌ Test spojení selhal: {e}")
            return False
