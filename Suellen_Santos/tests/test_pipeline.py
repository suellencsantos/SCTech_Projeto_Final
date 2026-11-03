from __future__ import annotations

import unittest

import pandas as pd

from src.analysis import correlation, lag_correlations
from src.data_pipeline import find_source_file, quality_report, transform_source


class PipelineTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = transform_source(find_source_file())

    def test_expected_shape_and_period(self) -> None:
        self.assertEqual(len(self.data), 176)
        self.assertEqual(self.data["data"].min(), pd.Timestamp("2012-01-01"))
        self.assertEqual(self.data["data"].max(), pd.Timestamp("2026-08-01"))

    def test_quality_controls(self) -> None:
        report = quality_report(self.data)
        self.assertEqual(report["registros"], report["meses_esperados"])
        self.assertEqual(report["duplicidades_de_data"], 0)
        self.assertEqual(report["valores_ausentes"], 0)

    def test_all_metrics_are_numeric_and_non_negative(self) -> None:
        columns = [
            "juros_credito_pessoal_aa",
            "inadimplencia_pf_total",
            "inadimplencia_cartao",
            "juros_cartao_aa",
        ]
        self.assertTrue(all(pd.api.types.is_numeric_dtype(self.data[column]) for column in columns))
        self.assertTrue((self.data[columns] >= 0).all().all())

    def test_reference_correlations(self) -> None:
        personal = correlation(
            self.data, "juros_credito_pessoal_aa", "inadimplencia_pf_total"
        )
        card = correlation(self.data, "juros_cartao_aa", "inadimplencia_cartao")
        self.assertAlmostEqual(personal, 0.4876, places=4)
        self.assertAlmostEqual(card, 0.6801, places=4)

    def test_lag_definition(self) -> None:
        lags = lag_correlations(
            self.data,
            "juros_credito_pessoal_aa",
            "inadimplencia_pf_total",
            max_lag=12,
        )
        best = lags.loc[lags["correlacao"].abs().idxmax()]
        self.assertEqual(int(best["defasagem_meses"]), 3)
        self.assertEqual(int(lags.iloc[0]["observacoes"]), 176)
        self.assertEqual(int(lags.iloc[-1]["observacoes"]), 164)


if __name__ == "__main__":
    unittest.main()

