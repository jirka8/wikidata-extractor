"""Export zpracovaných dat do CSV formátu."""

import logging
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
from datetime import datetime

from .config_manager import Config


logger = logging.getLogger('WikiDataExtractor.CSVExporter')


class CSVExporter:
    """Export dat do CSV formátu."""

    def __init__(self, config: Config):
        """
        Inicializace CSV exportéru.

        Args:
            config: Konfigurace projektu
        """
        self.config = config

    def export(self, data: List[Dict[str, Any]], output_path: str = None) -> Path:
        """
        Exportuje data do CSV souboru.

        Args:
            data: Zpracovaná data k exportu
            output_path: Volitelná cesta k výstupnímu souboru (přepíše config)

        Returns:
            Cesta k exportovanému souboru

        Raises:
            ValueError: Pokud nejsou žádná data k exportu
        """
        if not data:
            raise ValueError("Žádná data k exportu")

        # Určení výstupní cesty
        if output_path is None:
            output_path = self.config.get('output', 'file_path')

        output_path = Path(output_path)

        # Zajistit, že existuje výstupní adresář
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"📤 Exportuji data do: {output_path}")

        # Vytvoření DataFrame
        df = self._prepare_dataframe(data)

        # Generování sloupců podle konfigurace
        df = self._order_columns(df)

        # Export do CSV
        self._write_csv(df, output_path)

        # Statistiky
        file_size = output_path.stat().st_size / 1024 / 1024  # MB
        logger.info(f"✅ Export dokončen")
        logger.info(f"📊 Exportováno záznamů: {len(df)}")
        logger.info(f"📂 Velikost souboru: {file_size:.2f} MB")
        logger.info(f"📋 Počet sloupců: {len(df.columns)}")

        return output_path

    def _prepare_dataframe(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Připraví pandas DataFrame z dat.

        Args:
            data: Data k exportu

        Returns:
            pandas DataFrame
        """
        logger.info("🔄 Připravuji DataFrame...")

        df = pd.DataFrame(data)

        # Kontrola prázdných sloupců
        empty_cols = df.columns[df.isna().all()].tolist()
        if empty_cols:
            logger.warning(f"⚠️ Prázdné sloupce: {', '.join(empty_cols)}")

        return df

    def _order_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Seřadí sloupce podle konfigurace data_fields.

        Args:
            df: DataFrame k seřazení

        Returns:
            DataFrame se seřazenými sloupci
        """
        # Generování požadovaného pořadí sloupců
        ordered_columns = []

        # Nejdříve pole z konfigurace
        for field in self.config.get_data_fields():
            if isinstance(field.output_column, list):
                ordered_columns.extend(field.output_column)
            else:
                ordered_columns.append(field.output_column)

        # Pak administrativní hierarchie
        hierarchy = self.config.get('administrative_hierarchy', default=[])
        for level_data in hierarchy:
            level = level_data['level']
            col_name = f"admin_level_{level}"
            if col_name not in ordered_columns:
                ordered_columns.append(col_name)

        # Nakonec metadata
        metadata_cols = ['export_date']
        for col in metadata_cols:
            if col not in ordered_columns and col in df.columns:
                ordered_columns.append(col)

        # Ověřit, že všechny sloupce existují
        existing_columns = [col for col in ordered_columns if col in df.columns]

        # Přidat jakékoli extra sloupce, které nejsou v konfiguraci
        extra_columns = [col for col in df.columns if col not in existing_columns]
        if extra_columns:
            logger.debug(f"Extra sloupce: {', '.join(extra_columns)}")
            existing_columns.extend(extra_columns)

        return df[existing_columns]

    def _write_csv(self, df: pd.DataFrame, output_path: Path) -> None:
        """
        Zapíše DataFrame do CSV souboru.

        Args:
            df: DataFrame k exportu
            output_path: Cesta k výstupnímu souboru
        """
        # Nastavení z konfigurace
        encoding = self.config.get('output', 'encoding', default='utf-8-sig')
        delimiter = self.config.get('output', 'delimiter', default=',')
        include_header = self.config.get('output', 'include_header', default=True)

        # Zápis do CSV
        df.to_csv(
            output_path,
            sep=delimiter,
            encoding=encoding,
            index=False,
            header=include_header
        )

        logger.debug(f"CSV zapsáno: {output_path}")

    def add_metadata_comment(self, output_path: Path) -> None:
        """
        Přidá komentář s metadaty na začátek CSV souboru.

        Args:
            output_path: Cesta k CSV souboru
        """
        metadata = [
            f"# WikiData Extractor Export",
            f"# Země: {self.config.get('country', 'name')}",
            f"# Datum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Konfigurace: {self.config.config_path}",
            ""
        ]

        # Přečíst existující obsah
        with open(output_path, 'r', encoding=self.config.get('output', 'encoding')) as f:
            content = f.read()

        # Zapsat s metadaty
        with open(output_path, 'w', encoding=self.config.get('output', 'encoding')) as f:
            f.write('\n'.join(metadata))
            f.write(content)

        logger.debug("Metadata přidána do CSV")

    def create_summary_report(self, data: List[Dict[str, Any]], output_path: Path) -> str:
        """
        Vytvoří sumarizační report o exportovaných datech.

        Args:
            data: Exportovaná data
            output_path: Cesta k exportovanému CSV

        Returns:
            Report jako string
        """
        df = pd.DataFrame(data)

        report_lines = [
            "=" * 60,
            "WikiData Extractor - Export Report",
            "=" * 60,
            "",
            f"Země: {self.config.get('country', 'name')} ({self.config.get('country', 'iso_code')})",
            f"Datum exportu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Výstupní soubor: {output_path}",
            "",
            "Statistiky:",
            f"  Celkem záznamů: {len(df)}",
            f"  Počet sloupců: {len(df.columns)}",
            f"  Velikost souboru: {output_path.stat().st_size / 1024:.1f} KB",
            "",
            "Sloupce:",
        ]

        # Informace o každém sloupci
        for col in df.columns:
            non_null = df[col].notna().sum()
            null_count = len(df) - non_null
            coverage = (non_null / len(df) * 100) if len(df) > 0 else 0

            report_lines.append(
                f"  {col:30s} - {non_null:6d} hodnot ({coverage:5.1f}% pokrytí)"
            )

        # Statistiky pro numerická pole
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            report_lines.extend([
                "",
                "Numerické statistiky:",
            ])

            for col in numeric_cols:
                if df[col].notna().any():
                    report_lines.append(
                        f"  {col:30s} - "
                        f"min: {df[col].min():.2f}, "
                        f"max: {df[col].max():.2f}, "
                        f"průměr: {df[col].mean():.2f}"
                    )

        report_lines.append("=" * 60)

        report = '\n'.join(report_lines)

        # Uložit report do souboru
        report_path = output_path.with_suffix('.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"📋 Report uložen: {report_path}")

        return report

    def export_formats(
        self,
        data: List[Dict[str, Any]],
        output_dir: Path,
        formats: List[str] = None
    ) -> Dict[str, Path]:
        """
        Exportuje data do více formátů.

        Args:
            data: Data k exportu
            output_dir: Výstupní adresář
            formats: Seznam formátů ('csv', 'json', 'excel')

        Returns:
            Slovník s cestami k exportovaným souborům
        """
        if formats is None:
            formats = ['csv']

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(data)
        outputs = {}

        base_name = self.config.get('country', 'iso_code', default='export').lower()

        if 'csv' in formats:
            csv_path = output_dir / f"{base_name}.csv"
            self.export(data, str(csv_path))
            outputs['csv'] = csv_path

        if 'json' in formats:
            json_path = output_dir / f"{base_name}.json"
            df.to_json(json_path, orient='records', indent=2, force_ascii=False)
            logger.info(f"📤 JSON export: {json_path}")
            outputs['json'] = json_path

        if 'excel' in formats:
            excel_path = output_dir / f"{base_name}.xlsx"
            df.to_excel(excel_path, index=False, engine='openpyxl')
            logger.info(f"📤 Excel export: {excel_path}")
            outputs['excel'] = excel_path

        return outputs
