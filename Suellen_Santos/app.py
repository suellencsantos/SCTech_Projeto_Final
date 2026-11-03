"""Aplicação Streamlit para análise de juros e inadimplência no Brasil."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.analysis import (
    PAIR_OPTIONS,
    SERIES_META,
    annual_summary,
    correlation,
    filter_period,
    lag_correlations,
    period_change,
    summary_statistics,
    year_over_year_change,
)
from src.charts import annual_chart, lag_chart, scatter_chart, time_series_chart
from src.data_pipeline import (
    DEFAULT_PROCESSED_PATH,
    find_source_file,
    load_processed,
    quality_report,
    transform_source,
)


PROJECT_ROOT = Path(__file__).resolve().parent
ETL_REPORT_PATH = PROJECT_ROOT / "data" / "processed" / "etl_report.json"

st.set_page_config(
    page_title="Crédito PF: juros e inadimplência",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp { background: #f6f8fb; }
      [data-testid="stHeader"] { background: rgba(246,248,251,.85); }
      .hero {
        padding: 1.8rem 2rem;
        border-radius: 20px;
        color: white;
        background: linear-gradient(120deg, #102a43 0%, #155e75 55%, #0f766e 100%);
        box-shadow: 0 12px 32px rgba(15, 42, 67, .16);
        margin-bottom: 1rem;
      }
      .hero h1 { margin: 0 0 .45rem 0; font-size: 2.15rem; line-height: 1.12; }
      .hero p { margin: 0; max-width: 850px; color: #d8f3f0; font-size: 1.02rem; }
      .insight {
        background: white;
        border: 1px solid #e5eaf0;
        border-left: 5px solid #0f766e;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin: .35rem 0 1rem 0;
      }
      [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5eaf0;
        border-radius: 14px;
        padding: 1rem;
      }
      [data-testid="stSidebar"] { border-right: 1px solid #e3e8ef; }
      .small-muted { color: #667085; font-size: .88rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    if DEFAULT_PROCESSED_PATH.exists():
        return load_processed(DEFAULT_PROCESSED_PATH)
    return transform_source(find_source_file(PROJECT_ROOT))


@st.cache_data(show_spinner=False)
def load_etl_report(data: pd.DataFrame) -> dict[str, object]:
    if ETL_REPORT_PATH.exists():
        return json.loads(ETL_REPORT_PATH.read_text(encoding="utf-8"))
    return quality_report(data)


def br_number(value: float, suffix: str = "") -> str:
    if pd.isna(value):
        return "n.d."
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + suffix


def br_month(value: pd.Timestamp) -> str:
    months = [
        "jan", "fev", "mar", "abr", "mai", "jun",
        "jul", "ago", "set", "out", "nov", "dez",
    ]
    date = pd.Timestamp(value)
    return f"{months[date.month - 1]}/{date.year}"


try:
    data = load_data()
except Exception as exc:
    st.error(f"Não foi possível carregar a base: {exc}")
    st.stop()

report = load_etl_report(data)
min_date = data["data"].min().date()
max_date = data["data"].max().date()

with st.sidebar:
    st.subheader("Filtros da análise")
    selected_dates = st.date_input(
        "Período",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY",
    )
    if len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date, end_date = min_date, max_date

    selected_pair = st.radio(
        "Recorte principal",
        options=list(PAIR_OPTIONS),
        help="Define o par usado nos gráficos de associação e defasagem.",
    )
    max_lag = st.slider(
        "Defasagem máxima",
        min_value=0,
        max_value=12,
        value=12,
        help="Compara juros no mês t com inadimplência até 12 meses depois.",
    )
    st.divider()
    st.caption(
        f"Base: {report.get('registros', len(data))} meses completos, "
        f"de {br_month(data['data'].min())} a {br_month(data['data'].max())}."
    )
    st.caption("Fonte: Banco Central do Brasil - BCB/DSTAT, séries SGS.")

filtered = filter_period(data, pd.Timestamp(start_date), pd.Timestamp(end_date))
if filtered.empty:
    st.warning("O filtro selecionado não contém observações.")
    st.stop()

interest_column, delinquency_column = PAIR_OPTIONS[selected_pair]
interest_meta = SERIES_META[interest_column]
delinquency_meta = SERIES_META[delinquency_column]
latest = filtered.iloc[-1]

st.markdown(
    """
    <section class="hero">
      <h1>Crédito às pessoas físicas: juros e inadimplência</h1>
      <p>Como o custo do crédito e os atrasos acima de 90 dias evoluíram no Brasil,
      e que associação temporal aparece entre esses indicadores?</p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.caption(
    f"Período filtrado: {br_month(filtered['data'].min())} a "
    f"{br_month(filtered['data'].max())} · {len(filtered)} observações mensais"
)

kpi_columns = st.columns(4)
kpis = [
    ("juros_credito_pessoal_aa", "Juros do crédito pessoal"),
    ("juros_cartao_aa", "Juros do cartão"),
    ("inadimplencia_pf_total", "Inadimplência total PF"),
    ("inadimplencia_cartao", "Inadimplência do cartão"),
]
for container, (column, title) in zip(kpi_columns, kpis):
    meta = SERIES_META[column]
    delta = year_over_year_change(filtered, column)
    container.metric(
        title,
        br_number(latest[column], f" {meta['unidade']}"),
        delta=None if pd.isna(delta) else f"{br_number(delta)} p.p. em 12 meses",
        delta_color="inverse",
        help=f"Último valor disponível no filtro ({br_month(latest['data'])}).",
    )

st.caption(
    "Variação em 12 meses: diferença, em pontos percentuais, entre o último mês "
    "e o mesmo mês do ano anterior dentro do filtro. São necessários pelo menos "
    "13 meses selecionados; caso contrário, a comparação fica indisponível."
)

overview_tab, relation_tab, stats_tab, method_tab = st.tabs(
    ["Visão geral", "Relação e defasagem", "Estatísticas", "Dados e método"]
)

with overview_tab:
    st.subheader("Evolução dos indicadores")
    st.plotly_chart(
        time_series_chart(
            filtered,
            ["juros_credito_pessoal_aa", "juros_cartao_aa"],
            "Taxas médias de juros das novas operações",
            "% ao ano",
        ),
        width="stretch",
        config={"displaylogo": False},
    )
    st.plotly_chart(
        time_series_chart(
            filtered,
            ["inadimplencia_pf_total", "inadimplencia_cartao"],
            "Carteira com atraso superior a 90 dias",
            "% da carteira",
        ),
        width="stretch",
        config={"displaylogo": False},
    )

    annual = annual_summary(filtered)
    if len(annual) >= 2:
        st.plotly_chart(
            annual_chart(
                annual,
                ["inadimplencia_pf_total", "inadimplencia_cartao"],
                "Média anual da inadimplência",
                "% da carteira",
            ),
            width="stretch",
            config={"displaylogo": False},
        )
        incomplete_years = annual.loc[~annual["ano_completo"]]
        if not incomplete_years.empty:
            coverage = "; ".join(
                f"{int(row.ano)}: {int(row.meses_observados)} meses"
                for row in incomplete_years.itertuples()
            )
            st.caption(
                "* Médias de anos incompletos no filtro: " + coverage
                + ". Cada média usa somente os meses selecionados, sem projeção "
                "para o ano inteiro; compare períodos com a mesma cobertura."
            )

with relation_tab:
    corr = correlation(filtered, interest_column, delinquency_column)
    lags = lag_correlations(filtered, interest_column, delinquency_column, max_lag=max_lag)
    valid_lags = lags.dropna(subset=["correlacao"])
    best_lag = None if valid_lags.empty else valid_lags.loc[valid_lags["correlacao"].abs().idxmax()]

    left, right = st.columns([1.65, 1])
    with left:
        st.plotly_chart(
            scatter_chart(filtered, interest_column, delinquency_column),
            width="stretch",
            config={"displaylogo": False},
        )
    with right:
        st.metric("Correlação contemporânea", br_number(corr))
        st.markdown(
            f"""
            <div class="insight">
              <strong>Como ler</strong><br>
              O coeficiente de Pearson varia de -1 a +1. Neste filtro, a associação entre
              <em>{interest_meta['rotulo'].lower()}</em> e
              <em>{delinquency_meta['rotulo'].lower()}</em> é {br_number(corr)}.
              A linha pontilhada resume a tendência linear, sem demonstrar causalidade.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "As séries têm tendência e autocorrelação. Portanto, a correlação bruta pode "
            "refletir movimentos comuns no tempo e não um efeito direto."
        )

    if len(filtered) < max(24, max_lag + 12):
        st.warning(
            "O período selecionado é curto para comparar defasagens com estabilidade. "
            "Amplie o intervalo para interpretar este gráfico."
        )
    st.plotly_chart(
        lag_chart(lags),
        width="stretch",
        config={"displaylogo": False},
    )
    if best_lag is not None:
        st.info(
            f"A maior correlação absoluta no intervalo testado ocorre com "
            f"{int(best_lag['defasagem_meses'])} mês(es) de defasagem: "
            f"r = {br_number(best_lag['correlacao'])}. Esse resultado é exploratório."
        )

with stats_tab:
    st.subheader("Medidas descritivas do período filtrado")
    stats = summary_statistics(filtered).copy()
    for column in ["Média", "Mediana", "Desvio-padrão", "Mínimo", "Máximo", "Último valor"]:
        stats[column] = stats[column].map(lambda value: round(float(value), 2))
    stats["Data do mínimo"] = stats["Data do mínimo"].map(br_month)
    stats["Data do máximo"] = stats["Data do máximo"].map(br_month)
    st.dataframe(stats, hide_index=True, width="stretch")

    changes = []
    for column, meta in SERIES_META.items():
        changes.append(
            {
                "Indicador": meta["rotulo"],
                "Primeiro valor": filtered[column].iloc[0],
                "Último valor": filtered[column].iloc[-1],
                "Variação no período (p.p.)": period_change(filtered, column),
                "Variação em 12 meses (p.p.)": year_over_year_change(filtered, column),
            }
        )
    changes_frame = pd.DataFrame(changes).round(2)
    st.subheader("Variações em pontos percentuais")
    st.dataframe(changes_frame, hide_index=True, width="stretch")

with method_tab:
    st.subheader("Fonte, qualidade e transformação")
    quality_left, quality_right = st.columns(2)
    quality_left.markdown(
        f"""
        **Fonte pública**  
        Banco Central do Brasil (BCB/DSTAT), Sistema Gerenciador de Séries Temporais (SGS).

        **Recorte disponível**  
        {br_month(data['data'].min())} a {br_month(data['data'].max())}, frequência mensal.

        **Licença informada no catálogo**  
        Open Data Commons Open Database License (ODbL).
        """
    )
    quality_right.markdown(
        f"""
        **Controles executados**  
        {report.get('registros', len(data))} registros; {report.get('duplicidades_de_data', 0)}
        duplicidades de data; {report.get('valores_ausentes', 0)} valores ausentes; continuidade
        mensal validada.

        **Transformações**  
        Remoção da linha de fonte, conversão de mês/ano em data, conversão da vírgula decimal,
        nomes padronizados e ordenação cronológica.
        """
    )

    st.subheader("Dicionário das séries")
    dictionary = pd.DataFrame(
        [
            {
                "Código SGS": meta["codigo"],
                "Indicador": meta["rotulo"],
                "Unidade": meta["unidade"],
                "Catálogo": meta["url"],
            }
            for meta in SERIES_META.values()
        ]
    )
    st.dataframe(
        dictionary,
        hide_index=True,
        width="stretch",
        column_config={"Catálogo": st.column_config.LinkColumn("Catálogo BCB")},
    )

    st.warning(
        "Limitação: juros medem novas concessões, enquanto inadimplência mede o estoque da "
        "carteira com atraso superior a 90 dias. A análise é agregada, descritiva e não "
        "controla renda, inflação, emprego, composição da carteira ou mudanças regulatórias."
    )

    download = filtered.to_csv(index=False, sep=";", decimal=",", date_format="%Y-%m-%d")
    st.download_button(
        "Baixar recorte filtrado (CSV)",
        data=download.encode("utf-8-sig"),
        file_name="credito_pf_recorte.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "Painel educacional com dados públicos do Banco Central do Brasil. "
    "Resultados descritivos não constituem recomendação financeira e não demonstram causalidade."
)
