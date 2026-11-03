"""ETL e validações para as séries mensais do Banco Central do Brasil."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "credito_pf_mensal.csv"
DEFAULT_RAW_COPY_PATH = PROJECT_ROOT / "data" / "raw" / "bcb_series_credito_pf.csv"

SERIES_BY_CODE = {
    "20748": "juros_credito_pessoal_aa",
    "21112": "inadimplencia_pf_total",
    "21129": "inadimplencia_cartao",
    "22024": "juros_cartao_aa",
}

OUTPUT_COLUMNS = [
    "data",
    "ano",
    "mes",
    "periodo",
    "juros_credito_pessoal_aa",
    "inadimplencia_pf_total",
    "inadimplencia_cartao",
    "juros_cartao_aa",
]

MONTHS_PT = {
    "jan": 1,
    "fev": 2,
    "mar": 3,
    "abr": 4,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "set": 9,
    "out": 10,
    "nov": 11,
    "dez": 12,
}


class DataValidationError(ValueError):
    """Erro de qualidade que impede o uso seguro da base."""


def find_source_file(project_root: Path = PROJECT_ROOT) -> Path:
    """Localiza a cópia canônica ou o CSV original fornecido no projeto."""
    candidates = [DEFAULT_RAW_COPY_PATH, *sorted(project_root.glob("STP-*.csv"))]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Nenhum CSV foi encontrado. Mantenha o arquivo STP-*.csv na raiz "
        "ou execute o ETL com --input."
    )


def _read_csv_with_fallback(path: Path) -> pd.DataFrame:
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(path, sep=";", encoding=encoding, dtype="string")
        except UnicodeDecodeError as exc:
            last_error = exc
    raise DataValidationError(f"Não foi possível identificar a codificação de {path.name}.") from last_error


def _column_mapping(columns: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for code, target in SERIES_BY_CODE.items():
        matches = [column for column in columns if str(column).strip().startswith(code)]
        if len(matches) != 1:
            raise DataValidationError(
                f"Era esperada exatamente uma coluna iniciada pelo código SGS {code}; "
                f"foram encontradas {len(matches)}."
            )
        mapping[matches[0]] = target
    return mapping


def _parse_period(value: str) -> pd.Timestamp:
    match = re.fullmatch(r"([a-zç]{3})/(\d{2})", value.strip().lower())
    if not match or match.group(1) not in MONTHS_PT:
        raise DataValidationError(f"Período inválido no CSV: {value!r}.")
    month = MONTHS_PT[match.group(1)]
    year = 2000 + int(match.group(2))
    return pd.Timestamp(year=year, month=month, day=1)


def transform_source(path: str | Path) -> pd.DataFrame:
    """Lê, limpa, tipa e valida o CSV exportado do BCB-DSTAT."""
    source = Path(path)
    raw = _read_csv_with_fallback(source)
    raw.columns = [str(column).strip() for column in raw.columns]

    if "Data" not in raw.columns:
        raise DataValidationError("A coluna 'Data' não foi encontrada.")

    mapping = _column_mapping(raw.columns.tolist())
    data_mask = raw["Data"].fillna("").str.strip().str.match(r"^[A-Za-zçÇ]{3}/\d{2}$")
    unexpected_rows = raw.loc[~data_mask, "Data"].dropna().astype(str).str.strip()
    unexpected_rows = unexpected_rows[~unexpected_rows.str.casefold().isin({"fonte", ""})]
    if not unexpected_rows.empty:
        raise DataValidationError(
            "Foram encontradas linhas não temporais inesperadas: "
            + ", ".join(unexpected_rows.unique().tolist())
        )

    data = raw.loc[data_mask, ["Data", *mapping.keys()]].rename(columns=mapping).copy()
    data["data"] = data.pop("Data").map(_parse_period)

    for column in SERIES_BY_CODE.values():
        normalized = (
            data[column]
            .astype("string")
            .str.strip()
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        data[column] = pd.to_numeric(normalized, errors="coerce")

    if data[list(SERIES_BY_CODE.values())].isna().any().any():
        missing = data[list(SERIES_BY_CODE.values())].isna().sum()
        missing = missing[missing > 0].to_dict()
        raise DataValidationError(f"Há valores ausentes ou não numéricos nas séries: {missing}.")

    data = data.sort_values("data").reset_index(drop=True)
    if data["data"].duplicated().any():
        duplicates = data.loc[data["data"].duplicated(keep=False), "data"].dt.strftime("%Y-%m")
        raise DataValidationError(f"Períodos duplicados: {', '.join(duplicates.tolist())}.")

    expected = pd.date_range(data["data"].min(), data["data"].max(), freq="MS")
    missing_periods = expected.difference(pd.DatetimeIndex(data["data"]))
    if not missing_periods.empty:
        labels = ", ".join(missing_periods.strftime("%Y-%m").tolist())
        raise DataValidationError(f"A série mensal possui lacunas: {labels}.")

    data.insert(1, "ano", data["data"].dt.year.astype("int64"))
    data.insert(2, "mes", data["data"].dt.month.astype("int64"))
    data.insert(3, "periodo", data["data"].dt.strftime("%Y-%m"))
    return data[OUTPUT_COLUMNS]


def quality_report(data: pd.DataFrame) -> dict[str, object]:
    """Produz controles simples de completude, unicidade e cobertura temporal."""
    numeric_columns = list(SERIES_BY_CODE.values())
    return {
        "registros": int(len(data)),
        "inicio": data["data"].min().strftime("%Y-%m-%d"),
        "fim": data["data"].max().strftime("%Y-%m-%d"),
        "periodicidade": "mensal",
        "meses_esperados": int(
            len(pd.date_range(data["data"].min(), data["data"].max(), freq="MS"))
        ),
        "duplicidades_de_data": int(data["data"].duplicated().sum()),
        "valores_ausentes": int(data[numeric_columns].isna().sum().sum()),
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_dataset(
    input_path: str | Path | None = None,
    output_path: str | Path = DEFAULT_PROCESSED_PATH,
    raw_copy_path: str | Path = DEFAULT_RAW_COPY_PATH,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Executa o ETL, preserva uma cópia bruta e grava dados e relatório."""
    source = Path(input_path) if input_path else find_source_file()
    output = Path(output_path)
    raw_copy = Path(raw_copy_path)

    if source.resolve() != raw_copy.resolve():
        raw_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, raw_copy)

    data = transform_source(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(output, index=False, date_format="%Y-%m-%d", encoding="utf-8")

    report = quality_report(data)
    report.update(
        {
            "arquivo_origem": source.name,
            "sha256_origem": file_sha256(source),
            "fonte_declarada_no_csv": "BCB-DSTAT",
            "codigos_sgs": list(SERIES_BY_CODE.keys()),
        }
    )
    report_path = output.with_name("etl_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return data, report


def load_processed(path: str | Path = DEFAULT_PROCESSED_PATH) -> pd.DataFrame:
    data = pd.read_csv(path, parse_dates=["data"])
    return data[OUTPUT_COLUMNS]


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa o ETL das séries de crédito do BCB.")
    parser.add_argument("--input", type=Path, help="CSV exportado do BCB-DSTAT.")
    parser.add_argument("--output", type=Path, default=DEFAULT_PROCESSED_PATH)
    args = parser.parse_args()
    data, report = build_dataset(args.input, args.output)
    print(
        f"ETL concluído: {len(data)} registros, "
        f"de {report['inicio']} a {report['fim']}, sem lacunas ou duplicidades."
    )


if __name__ == "__main__":
    main()

