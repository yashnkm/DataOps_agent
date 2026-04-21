---
name: contract-compliance
description: Analyze fee compliance of bank ↔ payment-network contracts using the FBE MCP server. Use when asked to audit contracts, find fee discrepancies, reconcile transaction fees vs contract schedules, or interpret contract clauses alongside billing data.
---

<oneliner>
Combine the `fbe-contracts` MCP server's DB tools (Postgres: contracts, fee_schedules, transactions) with the RAG tool (contract PDFs) to answer fee-compliance questions. Always cite both sources.
</oneliner>

<when-to-use>
## When to apply this skill

Invoke this procedure whenever the user asks about:

- **Fee discrepancies** — "Are we being overcharged by MasterCard?"
- **Contract vs billing reconciliation** — "Do last month's transactions match what our DBS contract says?"
- **Clause interpretation backed by data** — "What does our VISA contract say about fraud protection, and is the fee we're paying consistent with that clause?"
- **Contract inventory questions** — "What contracts do we have with VISA?"

If the question is purely about contract text with no billing/data component, use the RAG tool only — don't query Postgres.
</when-to-use>

<tools-available>
## Tools on the `fbe-contracts` MCP server

| Tool | Use when… |
|---|---|
| `list_contracts()` | You need to enumerate contracts or map a bank name to its `contract_id` |
| `query_contracts(sql, limit)` | You need structured data — fees, transactions, aggregates |
| `search_contract_documents(query, k)` | You need clauses, obligations, definitions, SLA language |
| `check_fee_compliance(contract_id, date_from?, date_to?)` | One-call audit returning summary + top overcharges |

Plus the `contract://{contract_id}` resource — full PDF text on demand.
</tools-available>

<schema>
## Database schema (Postgres)

**`contracts`** — one row per contract
```
contract_id        TEXT  PK         e.g. 'DBS-MC-2021-001'
participant        TEXT             e.g. 'DBS BANK'
service_provider   TEXT             'VISA' | 'MASTERCARD' | 'PULSE'
contract_type      TEXT             free text
effective_date     DATE
term_months        INT  nullable
source_file        TEXT             filename in DOCS_DIR
```

**`fee_schedules`** — each fee line from each contract
```
fee_id          SERIAL PK
contract_id     FK → contracts.contract_id
fee_category    TEXT    e.g. 'atm_withdrawal', 'pos', 'credit_interchange_fixed'
fee_amount      NUMERIC nullable   fixed-dollar component
fee_percentage  NUMERIC nullable   rate as decimal (0.0175 = 1.75%)
fee_unit        TEXT    'per_transaction' | 'per_month' | 'percentage' | 'per_year' | 'per_case'
notes           TEXT
```

**`transactions`** — simulated live transactions
```
transaction_id      SERIAL PK
contract_id         FK
transaction_date    TIMESTAMP
transaction_type    TEXT  (matches fee_category values)
transaction_amount  NUMERIC
fee_charged         NUMERIC
currency            TEXT default 'USD'
merchant_name       TEXT
```

**Compliance rule** (the key insight):
```
expected_fee = fee_schedules.fee_amount + fee_schedules.fee_percentage * transactions.transaction_amount
```
A transaction is overcharged if `fee_charged > expected_fee + threshold` (default $0.0001).
</schema>

<procedure>
## Standard procedure

1. **Identify the contract.** If the user gives a bank name, call `list_contracts()` to find the `contract_id`. If they give a contract_id, skip ahead.
2. **Pick the right tool for the question type:**
   - Fee discrepancy → `check_fee_compliance(contract_id)` (one call, opinionated)
   - Custom aggregation → `query_contracts(sql)` with a focused SELECT
   - Contract clause → `search_contract_documents(query)`
   - Both needed → call them in sequence, reconcile in the response
3. **Cite both sources.** When crossing DB and RAG, name which fact came from which: *"The contract (DBS-MC-2021-001 PDF) specifies 1.1% + $0.08 for debit; the database shows 3 transactions charged at 1.5% + $0.12."*
4. **Report dollar impact.** For overcharges, always include total USD and number of affected transactions.
</procedure>

<ex-simple-discrepancy>
## Example — fee discrepancy audit

**User:** "Are any transactions for the DBS MasterCard contract overcharged?"

**Agent:**
```
Call 1: check_fee_compliance(contract_id="DBS-MC-2021-001")
→ { summary: { overcharged: 8, total_transactions: 42, total_overcharge_usd: 2.34 },
    flagged: [ ... top 50 offenders ... ] }
```

**Response:**
> **8 of 42 transactions** on the DBS MasterCard contract (`DBS-MC-2021-001`) are overcharged versus the contract fee schedule.
>
> **Total overcharge: $2.34.**
>
> Worst offender: a POS transaction on 2026-03-15 for $245.80 charged $0.42 (expected $0.14, contract rule: $0.140/txn).
>
> The fee schedule in the contract says `pos: $0.140 per transaction`. The billing system is charging ~3x that on this handful of transactions.

_(Cited DB row + contract section — both sources.)_
</ex-simple-discrepancy>

<ex-cross-source>
## Example — cross-source question

**User:** "What fraud protection does DBS get under its VISA contract, and how much are we paying for it?"

**Agent:**
```
Call 1: search_contract_documents(query="fraud protection DBS VISA")
→ "Enhanced Fraud Protection: Real-time fraud detection and alerting services
   shall be included as part of the standard service package..."

Call 2: list_contracts() to find contract_id for DBS + VISA
→ contract_id = 'DBS-VISA-2020-001'

Call 3: query_contracts(sql="SELECT fee_category, fee_amount, fee_unit, notes
                              FROM fee_schedules
                              WHERE contract_id = 'DBS-VISA-2020-001'
                                AND (fee_category ILIKE '%fraud%'
                                     OR notes ILIKE '%fraud%')")
→ rows: 0

Call 4 (follow-up): query_contracts(sql="SELECT fee_category, fee_amount
                                         FROM fee_schedules
                                         WHERE contract_id = 'DBS-VISA-2020-001'
                                           AND fee_unit = 'per_month'")
→ rows showing: network_security_fee = $200/month
```

**Response:**
> Under `DBS-VISA-2020-001`, **Enhanced Fraud Protection is bundled in the standard service package** — the contract states it's "included" (source: DBS VISA 2020 PDF).
>
> No separate line-item fraud fee exists in `fee_schedules`. The closest monthly charge is `network_security_fee: $200/month`, which the contract text does not explicitly tie to fraud. That's worth clarifying with finance before concluding there's no fraud-protection cost.
</ex-cross-source>

<ex-cite-both-sources>
## Example — correct citation pattern

**WRONG** — answer without source attribution:
```
"The fee is 1.75% and the transactions look fine."
```

**CORRECT** — dual citation:
```
"The contract (SCB-VISA-2023-002, source: SC_Bank_VISA_Contract_2023.txt)
specifies interchange fees of **1.75% of transaction amount** (Exhibit A -
Fee Schedule). Running check_fee_compliance across the 23 transactions in
the database for this contract, none exceed the threshold — all are charged
at exactly 1.75%."
```
</ex-cite-both-sources>

<fix-dont-over-explore>
## Common mistake — exhaustive schema exploration

**WRONG:** listing tables → describing each table → sampling rows → *then* querying.

**CORRECT:** use the schema block above (already in this skill). Go straight to one focused `query_contracts` call.

The schema rarely changes. If your SELECT fails with a column-not-found error, THEN introspect — don't introspect preemptively.
</fix-dont-over-explore>

<fix-missing-fee-rule>
## Common mistake — treating NULL expected_fee as $0

If `transactions.transaction_type` has no matching row in `fee_schedules`, the LEFT JOIN yields NULL. `COALESCE(...,0)` will then say "expected fee $0" — and flag the transaction as an overcharge of the whole charged amount. That's usually wrong.

**CORRECT approach:** when `fee_amount` and `fee_percentage` are both NULL, the contract simply doesn't specify that transaction_type. Report it as "unspecified fee category" rather than an overcharge.

Example filter that respects this:
```sql
WHERE fee_charged > expected_fee + 0.0001
  AND (f.fee_amount IS NOT NULL OR f.fee_percentage IS NOT NULL)
```
</fix-missing-fee-rule>

<boundaries>
## Boundaries

- **Read-only.** `query_contracts` rejects INSERT/UPDATE/DELETE. If the user asks to fix a fee, propose the SQL change — don't execute it.
- **Scope.** Only the three tables in the schema block are accessible. Don't try to read `pg_catalog` or join other databases.
- **Don't invent fees.** If the contract PDF doesn't mention a specific fee category, say so — don't extrapolate from similar contracts.
</boundaries>

<vocabulary>
## Domain vocabulary cheat sheet

- **Interchange** — the fee the issuing bank collects when a card is used at a merchant. Usually a % + fixed component.
- **Acquirer / Issuer** — the bank that processes the merchant's side (acquirer) vs the bank that issued the card (issuer).
- **Chargeback** — customer dispute reversing a transaction; networks charge admin fees per case.
- **CNP (Card-Not-Present)** — online / phone transactions. Usually more expensive than card-present.
- **PULSE** — US debit network, owned by Discover. Different fee structure from VISA/MasterCard.
- **Fee amendment / addendum** — contracts are often modified by addenda that replace parts of the fee schedule. Always cite the effective_date.
</vocabulary>
