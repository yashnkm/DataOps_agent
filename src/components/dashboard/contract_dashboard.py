"""
Contract Dashboard — reads from the POC Postgres schema
(contracts, fee_schedules, transactions) and shows billing details,
live transactions, and real discrepancies computed on-the-fly.
"""

import os
from decimal import Decimal
from typing import Any, Dict, List, Tuple

import gradio as gr
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine


def _connect():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "financial_services_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


_ENGINE = None

def _engine():
    """SQLAlchemy engine for pandas.read_sql_query (pandas warns on raw psycopg2)."""
    global _ENGINE
    if _ENGINE is None:
        url = (
            f"postgresql+psycopg2://{os.getenv('DB_USER', 'postgres')}:"
            f"{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}:"
            f"{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'financial_services_db')}"
        )
        _ENGINE = create_engine(url)
    return _ENGINE


class ContractDashboard:
    def __init__(self):
        self.contracts_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "contracts"
        )
        self.left_components: Dict[str, Any] = {}
        self.center_components: Dict[str, Any] = {}
        self.right_components: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get_contract_list(self) -> List[str]:
        """Return dropdown labels of the form 'PARTICIPANT — PROVIDER (contract_id)'."""
        try:
            with _connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT contract_id, participant, service_provider "
                        "FROM contracts ORDER BY participant, service_provider"
                    )
                    rows = cur.fetchall()
            return [f"{p} — {s} ({cid})" for (cid, p, s) in rows]
        except Exception as e:
            print(f"⚠️ Dashboard: could not load contract list: {e}")
            return []

    @staticmethod
    def _contract_id_from_label(label: str) -> str:
        """Extract contract_id from dropdown label 'PART — PROV (CID)'."""
        if not label:
            return ""
        if "(" in label and label.endswith(")"):
            return label.rsplit("(", 1)[-1].rstrip(")")
        return label

    def load_contract_content(self, label: str) -> str:
        contract_id = self._contract_id_from_label(label)
        if not contract_id:
            return "Please select a contract"
        try:
            with _connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT source_file FROM contracts WHERE contract_id = %s", (contract_id,))
                    row = cur.fetchone()
            if not row or not row[0]:
                return f"No source file associated with {contract_id}"
            path = os.path.join(self.contracts_dir, row[0])
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error loading contract: {e}"

    def get_contract_billing_info(self, label: str) -> str:
        contract_id = self._contract_id_from_label(label)
        if not contract_id:
            return "Please select a contract"

        try:
            with _connect() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """SELECT contract_id, participant, service_provider, contract_type,
                                  effective_date, term_months
                           FROM contracts WHERE contract_id = %s""",
                        (contract_id,),
                    )
                    contract = cur.fetchone()
                    if not contract:
                        return f"❌ No contract found for {contract_id}"

                    cur.execute(
                        """SELECT fee_category, fee_amount, fee_percentage, fee_unit, notes
                           FROM fee_schedules WHERE contract_id = %s
                           ORDER BY fee_unit, fee_category""",
                        (contract_id,),
                    )
                    fees = cur.fetchall()
        except Exception as e:
            return f"❌ Error loading billing info: {e}"

        lines = [
            f"## 📋 **{contract['participant']} — {contract['service_provider']}**",
            "",
            f"**Contract ID:** `{contract['contract_id']}`  ",
            f"**Type:** {contract['contract_type']}  ",
            f"**Effective:** {contract['effective_date']}  ",
            f"**Term:** {contract['term_months']} months" if contract["term_months"] else "**Term:** open-ended",
            "",
            "### 💰 Fee Schedule",
            "",
            "| Category | Fixed | Percentage | Unit |",
            "|---|---|---|---|",
        ]
        for f in fees:
            amt = f"${f['fee_amount']}" if f["fee_amount"] is not None else "—"
            pct = f"{float(f['fee_percentage']) * 100:.2f}%" if f["fee_percentage"] is not None else "—"
            lines.append(f"| {f['fee_category']} | {amt} | {pct} | {f['fee_unit']} |")

        lines.append("")
        lines.append(f"_Total fee rules: {len(fees)}_")
        return "\n".join(lines)

    def get_transaction_data(self, label: str) -> pd.DataFrame:
        """Transactions + computed expected_fee + discrepancy."""
        contract_id = self._contract_id_from_label(label)
        if not contract_id:
            return pd.DataFrame()

        sql = """
            SELECT
                t.transaction_date,
                t.transaction_type,
                t.transaction_amount,
                t.fee_charged,
                (COALESCE(f.fee_amount, 0) + COALESCE(f.fee_percentage, 0) * t.transaction_amount)
                    AS expected_fee,
                (t.fee_charged -
                    (COALESCE(f.fee_amount, 0) + COALESCE(f.fee_percentage, 0) * t.transaction_amount))
                    AS discrepancy,
                t.merchant_name
            FROM transactions t
            LEFT JOIN fee_schedules f
                ON f.contract_id = t.contract_id
                AND f.fee_category = t.transaction_type
            WHERE t.contract_id = %s
            ORDER BY t.transaction_date DESC
        """
        try:
            df = pd.read_sql_query(sql, _engine(), params=(contract_id,))
        except Exception as e:
            print(f"⚠️ Dashboard: transaction query failed: {e}")
            return pd.DataFrame()

        if df.empty:
            return df

        df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.strftime("%Y-%m-%d %H:%M")
        df["transaction_amount"] = df["transaction_amount"].apply(lambda x: f"${float(x):.2f}")
        df["fee_charged"] = df["fee_charged"].apply(lambda x: f"${float(x):.4f}")
        df["expected_fee"] = df["expected_fee"].apply(lambda x: f"${float(x):.4f}")
        df["discrepancy"] = df["discrepancy"].apply(
            lambda x: f"⚠️ +${float(x):.4f}" if float(x) > 0.0001 else f"${float(x):.4f}"
        )
        df = df[[
            "transaction_date", "transaction_type", "transaction_amount",
            "fee_charged", "expected_fee", "discrepancy", "merchant_name",
        ]]
        df.columns = ["Date", "Type", "Amount", "Fee Charged", "Expected Fee", "Discrepancy", "Merchant"]
        return df

    def get_transaction_summary(self, label: str) -> str:
        contract_id = self._contract_id_from_label(label)
        if not contract_id:
            return "Please select a contract"
        return f"## 🗄️ Transactions for `{contract_id}`"

    def compute_discrepancy_analysis(self, label: str) -> Tuple[str, pd.DataFrame]:
        """Real AI-ready analysis — compares each transaction fee to contract fee schedule."""
        contract_id = self._contract_id_from_label(label)
        if not contract_id:
            return "Please select a contract", pd.DataFrame()

        sql = """
            WITH joined AS (
                SELECT t.*,
                       (COALESCE(f.fee_amount, 0) + COALESCE(f.fee_percentage, 0) * t.transaction_amount)
                           AS expected_fee
                FROM transactions t
                LEFT JOIN fee_schedules f
                    ON f.contract_id = t.contract_id
                    AND f.fee_category = t.transaction_type
                WHERE t.contract_id = %s
            )
            SELECT
                COUNT(*) FILTER (WHERE fee_charged > expected_fee + 0.0001) AS overcharged,
                COUNT(*) AS total,
                COALESCE(SUM(fee_charged - expected_fee)
                         FILTER (WHERE fee_charged > expected_fee + 0.0001), 0)
                    AS total_overcharge
            FROM joined
        """
        details_sql = """
            SELECT transaction_date, transaction_type, transaction_amount,
                   fee_charged, expected_fee, fee_charged - expected_fee AS variance
            FROM (
                SELECT t.*,
                       (COALESCE(f.fee_amount, 0) + COALESCE(f.fee_percentage, 0) * t.transaction_amount)
                           AS expected_fee
                FROM transactions t
                LEFT JOIN fee_schedules f
                    ON f.contract_id = t.contract_id
                    AND f.fee_category = t.transaction_type
                WHERE t.contract_id = %s
            ) j
            WHERE fee_charged > expected_fee + 0.0001
            ORDER BY (fee_charged - expected_fee) DESC
            LIMIT 20
        """
        try:
            with _connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (contract_id,))
                    overcharged, total, total_overcharge = cur.fetchone()
                details_df = pd.read_sql_query(details_sql, _engine(), params=(contract_id,))
        except Exception as e:
            return f"❌ Error computing analysis: {e}", pd.DataFrame()

        if total == 0:
            return "No transactions found for this contract.", pd.DataFrame()

        pct = (overcharged / total * 100) if total else 0.0
        summary = f"""## 🤖 Discrepancy Analysis — `{contract_id}`

**Findings**
- 🚨 **{overcharged}** of **{total}** transactions are overcharged vs contract ({pct:.1f}%)
- 💸 Total overcharge: **${float(total_overcharge):.4f}**

**Method**
- Each transaction's `fee_charged` is compared to the contract's fee rule
  (`fee_amount + fee_percentage * transaction_amount` from `fee_schedules`)
- Any excess > $0.0001 is flagged as a discrepancy

**Top offenders shown in the table below**
"""
        if not details_df.empty:
            details_df["transaction_date"] = pd.to_datetime(details_df["transaction_date"]).dt.strftime("%Y-%m-%d")
            details_df["transaction_amount"] = details_df["transaction_amount"].apply(lambda x: f"${float(x):.2f}")
            details_df["fee_charged"] = details_df["fee_charged"].apply(lambda x: f"${float(x):.4f}")
            details_df["expected_fee"] = details_df["expected_fee"].apply(lambda x: f"${float(x):.4f}")
            details_df["variance"] = details_df["variance"].apply(lambda x: f"+${float(x):.4f}")
            details_df.columns = ["Date", "Type", "Amount", "Fee Charged", "Expected", "Variance"]

        return summary, details_df

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def create_left_section_interface(self):
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Contract Information")
            self.left_components["contract_dropdown"] = gr.Dropdown(
                label="Select Contract",
                choices=self.get_contract_list(),
                value=None,
                interactive=True,
            )
            self.left_components["billing_info"] = gr.Markdown(
                value="_Select a contract to view billing information._"
            )
            with gr.Row():
                self.left_components["refresh_btn"] = gr.Button("🔄 Refresh", variant="secondary", scale=1)
                self.left_components["view_contract_btn"] = gr.Button("📄 View Full Contract", variant="primary", scale=2)
            self.left_components["contract_content"] = gr.Textbox(
                label="Full Contract Content", lines=8, interactive=False, visible=False,
            )

        self.left_components["contract_dropdown"].change(
            fn=self._on_contract_selection_change,
            inputs=[self.left_components["contract_dropdown"]],
            outputs=[
                self.left_components["billing_info"],
                self.left_components["contract_content"],
            ],
        )
        self.left_components["view_contract_btn"].click(
            fn=lambda label: gr.update(value=self.load_contract_content(label), visible=True),
            inputs=[self.left_components["contract_dropdown"]],
            outputs=[self.left_components["contract_content"]],
        )
        self.left_components["refresh_btn"].click(
            fn=self.get_contract_billing_info,
            inputs=[self.left_components["contract_dropdown"]],
            outputs=[self.left_components["billing_info"]],
        )

    def create_center_section_interface(self):
        with gr.Column(scale=1):
            gr.Markdown("### 🗄️ Transaction Records")
            self.center_components["transaction_summary"] = gr.Markdown(
                value="_Select a contract to view transactions._"
            )
            self.center_components["transaction_table"] = gr.Dataframe(interactive=False, wrap=True)

    def create_right_section_interface(self):
        with gr.Column(scale=1):
            gr.Markdown("### 🤖 Discrepancy Analysis")
            self.right_components["ai_analysis"] = gr.Markdown(
                value="_Select a contract to view discrepancy analysis._"
            )
            self.right_components["ai_details_table"] = gr.Dataframe(
                label="Overcharged Transactions (top 20)", interactive=False, wrap=True,
            )

    def create_full_dashboard_interface(self):
        with gr.Row():
            self.create_left_section_interface()
            self.create_center_section_interface()
            self.create_right_section_interface()

        self.left_components["contract_dropdown"].change(
            fn=self._update_all_sections,
            inputs=[self.left_components["contract_dropdown"]],
            outputs=[
                self.center_components["transaction_summary"],
                self.center_components["transaction_table"],
                self.right_components["ai_analysis"],
                self.right_components["ai_details_table"],
            ],
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_contract_selection_change(self, label: str) -> Tuple[str, str]:
        return self.get_contract_billing_info(label), ""

    def _update_all_sections(self, label: str) -> Tuple[str, pd.DataFrame, str, pd.DataFrame]:
        summary = self.get_transaction_summary(label)
        df = self.get_transaction_data(label)
        analysis, details = self.compute_discrepancy_analysis(label)
        return summary, df, analysis, details
