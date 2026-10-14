import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from detector import detect_duplicates, load_payments, invoice_similarity


class DuplicateDetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = load_payments(ROOT / "data" / "pagamentos_ficticios.csv")

    def test_money_is_integer_cents(self):
        self.assertTrue(pd.api.types.is_integer_dtype(self.df["amount_cents"]))
        self.assertEqual(int(self.df.loc[self.df.payment_id == "P005", "amount_cents"].iloc[0]), 420000)

    def test_hidden_duplicate_is_flagged(self):
        alerts = detect_duplicates(self.df)
        pairs = set(zip(alerts["pagamento_1"].astype(str), alerts["pagamento_2"].astype(str)))
        self.assertTrue(any(
            first in {"P005", "P006"} and second in {"P005", "P006"}
            for first, second in pairs
        ))
        self.assertIn("P005", alerts.to_string())
        self.assertIn("P006", alerts.to_string())

    def test_invoice_similarity(self):
        self.assertGreaterEqual(invoice_similarity("PT-771", "PT-77I"), 0.80)

    def test_risk_score_and_priority_exist(self):
        alerts = detect_duplicates(self.df)
        self.assertIn("score_risco", alerts.columns)
        self.assertIn("prioridade", alerts.columns)
        self.assertTrue(alerts["score_risco"].between(0, 100).all())

    def test_output_has_explanations(self):
        alerts = detect_duplicates(self.df)
        self.assertIn("motivos", alerts.columns)
        self.assertTrue(alerts["motivos"].astype(str).str.len().gt(0).all())


if __name__ == "__main__":
    unittest.main()
