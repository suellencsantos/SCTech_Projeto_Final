"""Cálculos analíticos usados pela aplicação e pela documentação."""

from __future__ import annotations

import numpy as np
import pandas as pd


SERIES_META = {
    "juros_credito_pessoal_aa": {
        "codigo": "20748",
        "rotulo": "Juros do crédito pessoal",
        "rotulo_curto": "Juros - crédito pessoal",
        "unidade": "% a.a.",
        "cor": "#2563EB",
        "tipo": "juros",
        "url": "https://dadosabertos.bcb.gov.br/dataset/20748-taxa-media-de-juros-das-operacoes-de-credito-com-recursos-livres---pessoas-fisicas---credito-",
    },
    "inadimplencia_pf_total": {
        "codigo": "21112",
        "rotulo": "Inadimplência das pessoas físicas",
        "rotulo_curto": "Inadimplência - total PF",
        "unidade": "%",
        "cor": "#0F766E",
        "tipo": "inadimplencia",
        "url": "https://dadosabertos.bcb.gov.br/dataset/21112-inadimplencia-da-carteira-de-credito-com-recursos-livres---pessoas-fisicas---total",
    },
    "inadimplencia_cartao": {
        "codigo": "21129",
        "rotulo": "Inadimplência do cartão de crédito",
        "rotulo_curto": "Inadimplência - cartão",
        "unidade": "%",
        "cor": "#EA580C",
        "tipo": "inadimplencia",
        "url": "https://dadosabertos.bcb.gov.br/dataset/21129-inadimplencia-da-carteira-de-credito-com-recursos-livres---pessoas-fisicas---cartao-de-credit",
    },
    "juros_cartao_aa": {
        "codigo": "22024",
        "rotulo": "Juros do cartão de crédito",
        "rotulo_curto": "Juros - cartão",
        "unidade": "% a.a.",
        "cor": "#7C3AED",
        "tipo": "juros",
        "url": "https://dadosabertos.bcb.gov.br/dataset/22024-taxa-media-de-juros-das-operacoes-de-credito-com-recursos-livres---pessoas-fisicas---cartao-d",
    },
}

PAIR_OPTIONS = {
    "Crédito pessoal e inadimplência total": (
        "juros_credito_pessoal_aa",
        "inadimplencia_pf_total",
    ),
    "Cartão de crédito": ("juros_cartao_aa", "inadimplencia_cartao"),
}


def filter_period(data: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    mask = data["data"].between(pd.Timestamp(start), pd.Timestamp(end), inclusive="both")
    return data.loc[mask].copy()


def period_change(data: pd.DataFrame, column: str) -> float:
    if len(data) < 2:
        return float("nan")
    return float(data[column].iloc[-1] - data[column].iloc[0])


def year_over_year_change(data: pd.DataFrame, column: str) -> float:
    if len(data) < 13:
        return float("nan")
    return float(data[column].iloc[-1] - data[column].iloc[-13])


def summary_statistics(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for column, meta in SERIES_META.items():
        maximum_index = data[column].idxmax()
        minimum_index = data[column].idxmin()
        rows.append(
            {
                "Indicador": meta["rotulo"],
                "Média": data[column].mean(),
                "Mediana": data[column].median(),
                "Desvio-padrão": data[column].std(ddof=1),
                "Mínimo": data.loc[minimum_index, column],
                "Data do mínimo": data.loc[minimum_index, "data"],
                "Máximo": data.loc[maximum_index, column],
                "Data do máximo": data.loc[maximum_index, "data"],
                "Último valor": data[column].iloc[-1],
                "Unidade": meta["unidade"],
            }
        )
    return pd.DataFrame(rows)


def correlation(data: pd.DataFrame, x_column: str, y_column: str) -> float:
    paired = data[[x_column, y_column]].dropna()
    if len(paired) < 3 or paired[x_column].nunique() < 2 or paired[y_column].nunique() < 2:
        return float("nan")
    return float(paired[x_column].corr(paired[y_column], method="pearson"))


def lag_correlations(
    data: pd.DataFrame,
    interest_column: str,
    delinquency_column: str,
    max_lag: int = 12,
) -> pd.DataFrame:
    """Correlaciona juros em t com inadimplência em t + defasagem."""
    records: list[dict[str, float | int]] = []
    for lag in range(max_lag + 1):
        future_delinquency = data[delinquency_column].shift(-lag)
        paired = pd.concat([data[interest_column], future_delinquency], axis=1).dropna()
        value = paired.iloc[:, 0].corr(paired.iloc[:, 1]) if len(paired) >= 3 else np.nan
        records.append(
            {
                "defasagem_meses": lag,
                "correlacao": float(value) if pd.notna(value) else np.nan,
                "observacoes": int(len(paired)),
            }
        )
    return pd.DataFrame(records)


def linear_fit(data: pd.DataFrame, x_column: str, y_column: str) -> pd.DataFrame:
    paired = data[[x_column, y_column]].dropna().sort_values(x_column)
    if len(paired) < 3 or paired[x_column].nunique() < 2:
        return pd.DataFrame(columns=[x_column, "estimado"])
    slope, intercept = np.polyfit(paired[x_column], paired[y_column], 1)
    x_values = np.linspace(paired[x_column].min(), paired[x_column].max(), 100)
    return pd.DataFrame({x_column: x_values, "estimado": slope * x_values + intercept})


def annual_summary(data: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = list(SERIES_META)
    annual = data.groupby("ano", as_index=False)[numeric_columns].mean()
    months = data.groupby("ano").size().rename("meses_observados").reset_index()
    annual = annual.merge(months, on="ano", how="left")
    annual["ano_completo"] = annual["meses_observados"].eq(12)
    return annual

