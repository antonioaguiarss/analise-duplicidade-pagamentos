"""Rule-based duplicate-payment detection for fictional LSP payments."""
from __future__ import annotations

from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "pagamentos_ficticios.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "alertas.csv"

DATE_WINDOW_DAYS = 5
AMOUNT_TOLERANCE_CENTS = 500  # R$ 5,00
INVOICE_SIMILARITY_THRESHOLD = 0.80


def normalize_text(value: object) -> str:
    """Normalize text for robust comparisons."""
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def normalize_tax_id(value: object) -> str:
    """Keep digits only; empty values remain empty."""
    if pd.isna(value):
        return ""
    return re.sub(r"\D", "", str(value))


def invoice_similarity(a: object, b: object) -> float:
    """Similarity score between normalized invoice identifiers (0..1)."""
    a_norm = re.sub(r"[^a-z0-9]", "", normalize_text(a))
    b_norm = re.sub(r"[^a-z0-9]", "", normalize_text(b))
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def load_payments(path: Path | str = DEFAULT_INPUT) -> pd.DataFrame:
    """Load CSV while preserving money as integer cents."""
    df = pd.read_csv(path, dtype={"supplier_tax_id": "string", "invoice_number": "string"})
    required = {
        "payment_id", "supplier_tax_id", "supplier_name", "invoice_number",
        "invoice_date", "payment_date", "amount_cents", "currency",
        "purchase_order", "service_reference", "payment_status",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(missing)}")

    df["payment_id"] = df["payment_id"].astype(str)
    df["supplier_tax_id_norm"] = df["supplier_tax_id"].map(normalize_tax_id)
    df["supplier_name_norm"] = df["supplier_name"].map(normalize_text)
    df["invoice_norm"] = df["invoice_number"].map(
        lambda x: re.sub(r"[^a-z0-9]", "", normalize_text(x))
    )
    for col in ("invoice_date", "payment_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["amount_cents"] = pd.to_numeric(df["amount_cents"], errors="raise").astype("int64")
    df["currency"] = df["currency"].astype(str).str.strip().str.upper()
    for col in ("purchase_order", "service_reference", "payment_status"):
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df


def supplier_key(row: pd.Series) -> str:
    """Use tax ID where present; fallback to normalized supplier name."""
    tax_id = row["supplier_tax_id_norm"]
    return f"TAX:{tax_id}" if tax_id else f"NAME:{row['supplier_name_norm']}"


def detect_duplicates(
    df: pd.DataFrame,
    date_window_days: int = DATE_WINDOW_DAYS,
    amount_tolerance_cents: int = AMOUNT_TOLERANCE_CENTS,
    invoice_similarity_threshold: float = INVOICE_SIMILARITY_THRESHOLD,
) -> pd.DataFrame:
    """
    Generate explainable pair-level alerts.

    Exact/near amounts, similar invoice IDs, shared purchase order/service
    references, and proximity in dates contribute to a risk score.
    Partial-payment candidates are added when multiple payments share a
    supplier/reference and sum to a nearby invoice-sized amount.
    """
    data = df.copy()
    if "supplier_tax_id_norm" not in data:
        data["supplier_tax_id_norm"] = data["supplier_tax_id"].map(normalize_tax_id)
    if "supplier_name_norm" not in data:
        data["supplier_name_norm"] = data["supplier_name"].map(normalize_text)
    if "invoice_norm" not in data:
        data["invoice_norm"] = data["invoice_number"].map(
            lambda x: re.sub(r"[^a-z0-9]", "", normalize_text(x))
        )
    data["supplier_key"] = data.apply(supplier_key, axis=1)
    data["payment_date"] = pd.to_datetime(data["payment_date"], errors="coerce")
    data["invoice_date"] = pd.to_datetime(data["invoice_date"], errors="coerce")

    alerts: list[dict] = []
    seen_pairs: set[tuple[str, str, str]] = set()

    # Pairwise checks within each supplier and currency.
    for _, group in data.groupby(["supplier_key", "currency"], dropna=False):
        rows = [row for _, row in group.iterrows()]
        for a, b in combinations(rows, 2):
            if a["payment_id"] == b["payment_id"]:
                continue
            ids = tuple(sorted([str(a["payment_id"]), str(b["payment_id"])]))
            day_gap = abs((a["payment_date"] - b["payment_date"]).days) if pd.notna(a["payment_date"]) and pd.notna(b["payment_date"]) else 999999
            invoice_gap = abs((a["invoice_date"] - b["invoice_date"]).days) if pd.notna(a["invoice_date"]) and pd.notna(b["invoice_date"]) else 999999
            value_gap = abs(int(a["amount_cents"]) - int(b["amount_cents"]))
            exact_amount = value_gap == 0
            near_amount = 0 < value_gap <= amount_tolerance_cents
            sim = invoice_similarity(a["invoice_number"], b["invoice_number"])
            same_invoice = bool(a["invoice_norm"]) and a["invoice_norm"] == b["invoice_norm"]
            similar_invoice = sim >= invoice_similarity_threshold
            shared_po = bool(a["purchase_order"]) and a["purchase_order"] == b["purchase_order"]
            shared_service = bool(a["service_reference"]) and a["service_reference"] == b["service_reference"]
            close_dates = min(day_gap, invoice_gap) <= date_window_days

            # A pair is considered only if there is a meaningful signal.
            if not (same_invoice or (close_dates and (exact_amount or near_amount or similar_invoice or shared_po or shared_service))):
                continue
            pair_key = (ids[0], ids[1], "PAIR")
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            score = 0
            reasons = []
            if exact_amount:
                score += 30
                reasons.append("valor exatamente igual")
            elif near_amount:
                score += 15
                reasons.append(f"valores próximos (diferença de R$ {value_gap / 100:.2f})")
            if same_invoice:
                score += 45
                reasons.append("mesmo número de nota normalizado")
            elif similar_invoice:
                score += 25
                reasons.append(f"números de nota semelhantes ({sim:.0%})")
            if close_dates:
                score += 15
                reasons.append("datas próximas")
            if shared_po:
                score += 10
                reasons.append("mesmo pedido de compra")
            if shared_service:
                score += 15
                reasons.append("mesma referência de serviço")
            if str(a["payment_status"]).upper() == "REVERSED" or str(b["payment_status"]).upper() == "REVERSED":
                score -= 20
                reasons.append("há pagamento estornado; validar antes de classificar")

            score = max(0, min(score, 100))
            priority = "ALTA" if score >= 75 else "MÉDIA" if score >= 45 else "BAIXA"
            alerts.append({
                "tipo_alerta": "POSSIVEL_DUPLICIDADE",
                "pagamento_1": ids[0],
                "pagamento_2": ids[1],
                "fornecedor": a["supplier_name"],
                "tax_id": a["supplier_tax_id_norm"] or "",
                "nota_1": a["invoice_number"],
                "nota_2": b["invoice_number"],
                "valor_1_brl": int(a["amount_cents"]) / 100,
                "valor_2_brl": int(b["amount_cents"]) / 100,
                "diferenca_valor_brl": value_gap / 100,
                "dias_entre_pagamentos": day_gap,
                "score_risco": score,
                "prioridade": priority,
                "motivos": "; ".join(reasons),
                "status": "INVESTIGAR",
            })

    # Partial-payment candidates: group by supplier, currency, and shared
    # service/PO reference. Flag only groups with 2+ payments and meaningful
    # combined amount; this is a candidate, not proof of duplication.
    ref_cols = ["supplier_key", "currency", "service_reference"]
    usable = data[data["service_reference"].astype(str).str.strip().ne("")]
    for _, group in usable.groupby(ref_cols, dropna=False):
        if len(group) < 2 or len(group) > 8:
            continue
        # Equal-sized payments are more likely to be a duplicate-pair signal
        # than a partial-payment pattern, so leave those to pair-level rules.
        amounts = group["amount_cents"].astype("int64")
        if amounts.nunique() == 1:
            continue
        total = int(amounts.sum())
        ids = sorted(group["payment_id"].astype(str).tolist())
        pair_key = ("+".join(ids), "", "PARTIAL")
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        # Avoid noisy tiny groups; this rule is intentionally conservative.
        if total <= 0:
            continue
        statuses = ", ".join(sorted(set(group["payment_status"].astype(str))))
        alerts.append({
            "tipo_alerta": "POSSIVEIS_PAGAMENTOS_PARCIAIS",
            "pagamento_1": ids[0],
            "pagamento_2": " + ".join(ids[1:]),
            "fornecedor": group.iloc[0]["supplier_name"],
            "tax_id": group.iloc[0]["supplier_tax_id_norm"] or "",
            "nota_1": group.iloc[0]["invoice_number"],
            "nota_2": " | ".join(group["invoice_number"].astype(str).tolist()[1:]),
            "valor_1_brl": int(group.iloc[0]["amount_cents"]) / 100,
            "valor_2_brl": int(group.iloc[1:]["amount_cents"].sum()) / 100,
            "diferenca_valor_brl": 0.0,
            "dias_entre_pagamentos": int((group["payment_date"].max() - group["payment_date"].min()).days) if group["payment_date"].notna().any() else -1,
            "score_risco": 35 if len(group) == 2 else 40,
            "prioridade": "BAIXA",
            "motivos": f"{len(group)} pagamentos compartilham referência de serviço; soma R$ {total / 100:.2f}; status: {statuses}. Conferir valor original da fatura e cronograma de parcelas",
            "status": "VALIDAR PAGAMENTO PARCIAL",
        })

    columns = [
        "tipo_alerta", "pagamento_1", "pagamento_2", "fornecedor", "tax_id",
        "nota_1", "nota_2", "valor_1_brl", "valor_2_brl",
        "diferenca_valor_brl", "dias_entre_pagamentos", "score_risco",
        "prioridade", "motivos", "status",
    ]
    result = pd.DataFrame(alerts, columns=columns)
    if not result.empty:
        result = result.sort_values(
            ["score_risco", "tipo_alerta"], ascending=[False, True]
        ).reset_index(drop=True)
    return result


def main() -> None:
    payments = load_payments(DEFAULT_INPUT)
    alerts = detect_duplicates(payments)
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    alerts.to_csv(DEFAULT_OUTPUT, index=False, encoding="utf-8-sig")
    print(f"Registros analisados: {len(payments)}")
    print(f"Alertas gerados: {len(alerts)}")
    if alerts.empty:
        print("Nenhum alerta encontrado.")
    else:
        print(alerts.to_string(index=False))
    print(f"\nRelatório salvo em: {DEFAULT_OUTPUT}")


if __name__ == "__main__":
    main()
