---
name: contract-onboarding
description: Ingest a new contract PDF into the FBE system. Parse it, extract structured metadata and fee schedule rows, seed the Postgres tables, and update the RAG index. Use when onboarding a new bank or network contract.
---

<oneliner>
Every new contract ends up in three places: `data/contracts/*.txt` (source), `contracts` + `fee_schedules` rows in Postgres (structured), and the FAISS index (RAG). Miss any one and the analysis agent gives incomplete answers.
</oneliner>

<workflow>
## The 6-step onboarding workflow

1. **Drop the source file** into `data/contracts/`. Use a descriptive filename: `<Participant>_<Provider>_<Year>.txt`.
2. **Extract contract header** — contract_id, participant, service_provider, contract_type, effective_date, term_months.
3. **Extract the fee schedule** — every numeric fee line gets one row in `fee_schedules`.
4. **Insert into Postgres** — `contracts` first (parent), then `fee_schedules` (child, FK).
5. **Reindex RAG** — upload the new PDF via the Gradio Documents tab or call the ingest pipeline programmatically.
6. **Verify** — run `check_fee_compliance(new_contract_id)` and confirm it returns sensible results (should be 0 overcharged since no transactions yet).
</workflow>

<extraction-rules>
## What to extract from the PDF

### Header fields
| Field | Find it via… |
|---|---|
| `contract_id` | Usually in the first few lines. Pattern: `<BANK>-<NETWORK>-<YEAR>-<SEQ>`, e.g. `DBS-MC-2021-001`. If absent, generate one following the pattern. |
| `participant` | The bank name. Uppercase. |
| `service_provider` | 'VISA', 'MASTERCARD', 'PULSE', 'AMERICAN_EXPRESS' — keep consistent. |
| `contract_type` | "Participation Agreement", "Addendum", "Service Agreement", etc. |
| `effective_date` | ISO date from the first page. |
| `term_months` | If the contract says "extended by 2 years" → 24. If "10-year term" → 120. Null for open-ended. |
| `source_file` | The filename placed in data/contracts/. |

### Fee schedule rows
Every bullet or table row mentioning a dollar amount, percentage, or "waived" gets one `fee_schedules` row.

**Fee categories** — use these canonical values (they need to match `transactions.transaction_type`):
- `atm_withdrawal`, `pos`, `online_cnp`, `contactless`
- `debit_interchange_fixed`, `credit_interchange_fixed`, `premium_credit_interchange`, `corporate_interchange`
- `cross_border_processing`, `international_atm_access`, `international_atm`, `international_processing`
- `currency_conversion`, `interchange`, `transaction_processing`
- `balance_inquiry`, `switch_processing`, `network_access`, `domestic_settlement`, `international_settlement`
- `*_monthly` suffix for per-month: `processing_fee_monthly`, `account_maintenance_monthly`, `fraud_monitoring_monthly`, etc.
- `*_annual` suffix for per-year
- `chargeback_admin`, `failed_transaction`

If an existing category fits → use it. If not → add a new one but document the match rule.

### Fee unit mapping
- "$X.XX per transaction" → `per_transaction`
- "$X.XX per month" → `per_month`
- "X%" or "X% of amount" → `percentage`
- "$X annually" → `per_year`
- "$X per case" / "per chargeback" → `per_case`
- "waived" → insert row with `fee_amount=0, fee_unit='per_transaction'` and `notes='waived per contract'`

### Discount wording
Contracts often phrase fees as *discounts*: "Standard transactions shall be discounted by $0.005". The base rate may be implicit. POC convention: store the discount as a negative `fee_amount` (so `expected_fee` calculation still works if base rate is zero), and document in `notes`.
</extraction-rules>

<ex-insertion>
## Example — insertion SQL

After parsing a new contract `ABC_VISA_2026.txt`:

```sql
INSERT INTO contracts (contract_id, participant, service_provider, contract_type,
                       effective_date, term_months, source_file)
VALUES ('ABC-VISA-2026-001', 'ABC BANK', 'VISA', 'Participation Agreement',
        '2026-01-10', 36, 'ABC_VISA_2026.txt');

INSERT INTO fee_schedules (contract_id, fee_category, fee_amount, fee_percentage, fee_unit, notes)
VALUES
    ('ABC-VISA-2026-001', 'pos',                  0.14, NULL,   'per_transaction', 'POS processing'),
    ('ABC-VISA-2026-001', 'atm_withdrawal',       0.01, NULL,   'per_transaction', 'ATM withdrawal'),
    ('ABC-VISA-2026-001', 'credit_interchange_fixed', 0.20, 0.022, 'per_transaction', 'Credit: 2.2% + $0.20'),
    ('ABC-VISA-2026-001', 'account_maintenance_monthly', 150.0, NULL, 'per_month', 'Monthly maintenance');
```
</ex-insertion>

<ex-reindex>
## Example — reindex the RAG store

Two paths:

**Path A (user-facing):** Gradio app → Documents tab → upload the PDF. The app handles chunking, embedding, FAISS insert.

**Path B (programmatic, for batch onboarding):**
```python
from components.document_processing.document_processor import DocumentProcessor
from components.vector_store.faiss_store import FAISSVectorStore

vs = FAISSVectorStore()
doc_proc = DocumentProcessor()
result = doc_proc.process_uploaded_files(['data/contracts/ABC_VISA_2026.txt'])
chunks = [c for d in result['documents'] for c in d['chunks']]
vs.add_documents_from_chunks(chunks)
```
</ex-reindex>

<fix-missing-from-rag>
## Common mistake — inserted into Postgres but forgot to RAG-index

Symptom: `check_fee_compliance(new_contract_id)` works, but `search_contract_documents` returns nothing when asked about the new contract's clauses.

**Cause:** Step 5 skipped — PDF added to data/contracts/ but FAISS index wasn't rebuilt.

**Fix:** run the Path B programmatic reindex above, or re-upload in the Gradio UI.
</fix-missing-from-rag>

<fix-category-typo>
## Common mistake — new fee_category that doesn't match transaction_type

If you coin a new fee_category (e.g. `pos_terminal`) but existing transactions still use `pos`, the LEFT JOIN in reconciliation queries will miss. `expected_fee` becomes NULL → `check_fee_compliance` either misses real overcharges or flags everything.

**Fix:** before inserting, check what `transactions.transaction_type` values already exist:

```sql
SELECT DISTINCT transaction_type FROM transactions WHERE contract_id = '<new_id>';
```

For a brand-new contract with no transactions yet, this is fine — just make sure your transaction generator uses the same names you inserted into `fee_schedules`.
</fix-category-typo>

<fix-date-interpretation>
## Common mistake — effective_date vs signature date

Contracts often show two dates: the effective date (when the fees apply) and the signature date (when both parties signed). For compliance purposes, **always use the effective_date**. Signature dates don't matter for fee calculations.

If the PDF says "This Addendum, effective as of March 18, 2025, is entered into on [signature date]" — effective_date is 2025-03-18.
</fix-date-interpretation>

<verification>
## Post-onboarding verification

Run these three checks after every onboarding:

1. **Header exists:** `SELECT * FROM contracts WHERE contract_id = '<new_id>';` returns one row.
2. **Fee schedule populated:** `SELECT COUNT(*) FROM fee_schedules WHERE contract_id = '<new_id>';` > 0.
3. **RAG finds it:** `search_contract_documents(query='<distinctive phrase from new contract>')` returns a hit whose source matches the new filename.

If all three pass, the contract is fully onboarded.
</verification>

<boundaries>
## Boundaries

- **PDF extraction is manual in the POC.** Automated parsing is out of scope — a human reads each contract and extracts the fees. Consider this a checklist, not a parser spec.
- **One contract per file.** Amendments and addenda should still get their own `contract_id` (link them via notes/metadata, not overloading).
- **Don't mutate transactions.** Onboarding a contract is pure addition — contracts + fee_schedules only. Don't touch existing transactions.
</boundaries>
