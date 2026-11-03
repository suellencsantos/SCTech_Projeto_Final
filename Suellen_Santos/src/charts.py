"""Visualizações Plotly do painel."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.analysis import SERIES_META, linear_fit


def _add_source(fig: go.Figure) -> go.Figure:
    """Mantém a fonte no próprio gráfico, inclusive em exportações."""
    fig.update_layout(margin_b=110)
    fig.add_annotation(
        text="Fonte: Banco Central do Brasil (BCB/DSTAT), SGS.<br>Elaboração própria com dados do período selecionado.",
        xref="paper", yref="paper", x=0, y=-0.30,
        xanchor="left", yanchor="top", showarrow=False, align="left",
        font=dict(size=11, color="#475569"),
    )
    return fig


def _base_layout(fig: go.Figure, title: str, y_title: str) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left"},
        template="plotly_white",
        height=420,
        margin=dict(l=20, r=20, t=65, b=25),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        yaxis_title=y_title,
        xaxis_title="",
        font=dict(family="Arial, sans-serif", color="#172033"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E8ECF2", zeroline=False)
    return _add_source(fig)


def time_series_chart(data: pd.DataFrame, columns: list[str], title: str, y_title: str) -> go.Figure:
    fig = go.Figure()
    for column in columns:
        meta = SERIES_META[column]
        fig.add_trace(
            go.Scatter(
                x=data["data"],
                y=data[column],
                mode="lines",
                name=meta["rotulo_curto"],
                line=dict(color=meta["cor"], width=2.6),
                hovertemplate="%{x|%b/%Y}<br>%{y:.2f}<extra>%{fullData.name}</extra>",
            )
        )
    return _base_layout(fig, title, y_title)


def scatter_chart(data: pd.DataFrame, x_column: str, y_column: str) -> go.Figure:
    x_meta = SERIES_META[x_column]
    y_meta = SERIES_META[y_column]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data[x_column],
            y=data[y_column],
            mode="markers",
            name="Meses",
            customdata=data["data"].dt.strftime("%b/%Y"),
            marker=dict(
                color=data["ano"],
                colorscale="Viridis",
                size=8,
                opacity=0.78,
                colorbar=dict(title="Ano"),
            ),
            hovertemplate=(
                "%{customdata}<br>"
                + x_meta["rotulo_curto"]
                + ": %{x:.2f}<br>"
                + y_meta["rotulo_curto"]
                + ": %{y:.2f}<extra></extra>"
            ),
        )
    )
    fit = linear_fit(data, x_column, y_column)
    if not fit.empty:
        fig.add_trace(
            go.Scatter(
                x=fit[x_column],
                y=fit["estimado"],
                mode="lines",
                name="Tendência linear",
                line=dict(color="#111827", width=2, dash="dash"),
                hoverinfo="skip",
            )
        )
    fig.update_layout(
        title={"text": "Associação entre juros e inadimplência", "x": 0.01},
        template="plotly_white",
        height=440,
        margin=dict(l=20, r=20, t=65, b=25),
        xaxis_title=f"{x_meta['rotulo']} ({x_meta['unidade']})",
        yaxis_title=f"{y_meta['rotulo']} ({y_meta['unidade']})",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(family="Arial, sans-serif", color="#172033"),
    )
    fig.update_xaxes(gridcolor="#EEF1F5")
    fig.update_yaxes(gridcolor="#EEF1F5")
    return _add_source(fig)


def lag_chart(lags: pd.DataFrame) -> go.Figure:
    colors = ["#F97316" if lag == 0 else "#2563EB" for lag in lags["defasagem_meses"]]
    fig = go.Figure(
        go.Bar(
            x=lags["defasagem_meses"],
            y=lags["correlacao"],
            marker_color=colors,
            customdata=lags["observacoes"],
            hovertemplate=(
                "Defasagem: %{x} meses<br>Correlação: %{y:.3f}<br>"
                "Pares válidos: %{customdata}<extra></extra>"
            ),
        )
    )
    fig.add_hline(y=0, line_color="#667085", line_width=1)
    fig.update_layout(
        title={"text": "Juros em t versus inadimplência em t + meses", "x": 0.01},
        template="plotly_white",
        height=390,
        margin=dict(l=20, r=20, t=65, b=25),
        xaxis_title="Defasagem da inadimplência (meses)",
        yaxis_title="Correlação de Pearson",
        showlegend=False,
        font=dict(family="Arial, sans-serif", color="#172033"),
    )
    fig.update_xaxes(dtick=1, showgrid=False)
    fig.update_yaxes(range=[-1, 1], gridcolor="#EEF1F5")
    return _add_source(fig)


def annual_chart(data: pd.DataFrame, columns: list[str], title: str, y_title: str) -> go.Figure:
    fig = go.Figure()
    labels = [
        f"{int(row.ano)}" + ("*" if not row.ano_completo else "")
        for row in data.itertuples()
    ]
    for column in columns:
        meta = SERIES_META[column]
        fig.add_trace(
            go.Bar(
                x=labels,
                y=data[column],
                name=meta["rotulo_curto"],
                marker_color=meta["cor"],
                customdata=data["meses_observados"],
                hovertemplate="%{x}<br>Média: %{y:.2f}<br>Meses observados: %{customdata}<extra>%{fullData.name}</extra>",
            )
        )
    fig.update_layout(barmode="group")
    fig = _base_layout(fig, title, y_title)
    fig.update_xaxes(type="category", title_text="Ano (* período incompleto)")
    return fig

