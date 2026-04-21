---
name: fee-reconciliation
description: Write and debug SQL for reconciling transaction fees against contract fee schedules in the FBE database. Use when building reconciliation queries, dashboards, ETL jobs, or batch audits over contracts / fee_schedules / transactions tables.
---

<oneliner>
The canonical recon formula is `expected_fee = fee_amount + fee_percentage * transaction_amount`. Get this one join right and every downstream question (overcharges, trends, root-cause) follows.
</oneliner>

<core-formula>
## The one formula you need to memorize

```sql
expected_fee = COALESCE(fee_schedules.fee_amount, 0)
             + COALESCE(fee_schedules.fee_percentage, 0) * transactions.transaction_amount
```

Joined on:
```sql
ON fee_schedules.contract_id = transactions.contract_id
AND fee_schedules.fee_category = transactions.transaction_type
```

A discrepancy is `transactions.fee_charged - expected_fee`. Positive = overcharge; negative = undercharge.
</core-formula>

<ex-overcharge-audit>
## Recipe — flag overcharges for a single contract

```sql
SELECT
    t.transaction_id,
    t.transaction_date,
    t.transaction_type,
    t.transaction_amount,
    t.fee_charged,
    COALESCE(f.fee_amount, 0)
        + COALESCE(f.fee_percentage, 0) * t.transaction_amount    AS expected_fee,
    t.fee_charged -
        (COALESCE(f.fee_amount, 0)
         + COALESCE(f.fee_percentage, 0) * t.transaction_amount)  AS variance
FROM transactions t
LEFT JOIN fee_schedules f
    ON f.contract_id = t.contract_id
    AND f.fee_category = t.transaction_type
WHERE t.contract_id = 'DBS-MC-2021-001'
  AND t.fee_charged >
      (COALESCE(f.fee_amount, 0)
       + COALESCE(f.fee_percentage, 0) * t.transaction_amount) + 0.0001
ORDER BY variance DESC;
```
</ex-overcharge-audit>

<ex-totals-by-contract>
## Recipe — overcharge totals across all contracts

```sql
WITH audit AS (
    SELECT
        t.contract_id,
        t.fee_charged -
            (COALESCE(f.fee_amount, 0)
             + COALESCE(f.fee_percentage, 0) * t.transaction_amount)
            AS variance
    FROM transactions t
    LEFT JOIN fee_schedules f
        ON f.contract_id = t.contract_id
        AND f.fee_category = t.transaction_type
)
SELECT
    c.contract_id,
    c.participant,
    c.service_provider,
    COUNT(*)                                     AS total_txns,
    COUNT(*) FILTER (WHERE variance > 0.0001)    AS overcharged,
    COALESCE(SUM(variance) FILTER (WHERE variance > 0.0001), 0)
                                                 AS total_overcharge_usd
FROM audit a
JOIN contracts c USING (contract_id)
GROUP BY c.contract_id, c.participant, c.service_provider
ORDER BY total_overcharge_usd DESC;
```
</ex-totals-by-contract>

<ex-monthly-trend>
## Recipe — monthly overcharge trend

```sql
SELECT
    DATE_TRUNC('month', t.transaction_date) AS month,
    t.contract_id,
    SUM(
        GREATEST(
            t.fee_charged -
                (COALESCE(f.fee_amount, 0)
                 + COALESCE(f.fee_percentage, 0) * t.transaction_amount),
            0
        )
    ) AS overcharge_usd
FROM transactions t
LEFT JOIN fee_schedules f
    ON f.contract_id = t.contract_id
    AND f.fee_category = t.transaction_type
GROUP BY 1, 2
ORDER BY month DESC, overcharge_usd DESC;
```
</ex-monthly-trend>

<fix-null-fee-rule>
## Gotcha — NULL fee rule is not a $0 expected fee

If `fee_schedules` has no row for a given `(contract_id, transaction_type)` pair, the LEFT JOIN yields NULL for both `fee_amount` and `fee_percentage`. `COALESCE` to zero makes `expected_fee = 0`, which means any `fee_charged > 0` gets flagged as 100% overcharge — **usually wrong**.

**Fix:** exclude unspecified fee categories from overcharge counts, or report them as a separate class.

```sql
-- WRONG: flags everything without a matching rule
WHERE t.fee_charged > expected_fee + 0.0001

-- CORRECT: only flag if the contract actually specified a rule
WHERE t.fee_charged > expected_fee + 0.0001
  AND (f.fee_amount IS NOT NULL OR f.fee_percentage IS NOT NULL)
```
</fix-null-fee-rule>

<fix-multiple-matching-rules>
## Gotcha — multiple fee rules matching

If the contract has multiple rules for the same category (e.g., per-transaction AND per-month), your LEFT JOIN will row-multiply. For POC data each `(contract_id, fee_category)` is unique, but real contracts often aren't.

**Fix:** aggregate the fee rules before joining.

```sql
WITH applicable_rules AS (
    SELECT
        contract_id,
        fee_category,
        SUM(fee_amount)     AS fee_amount,
        SUM(fee_percentage) AS fee_percentage
    FROM fee_schedules
    WHERE fee_unit IN ('per_transaction', 'percentage')  -- skip monthly/yearly here
    GROUP BY 1, 2
)
SELECT ...
FROM transactions t
LEFT JOIN applicable_rules f ON f.contract_id = t.contract_id
                             AND f.fee_category = t.transaction_type
```
</fix-multiple-matching-rules>

<fix-monthly-vs-per-txn>
## Gotcha — mixing per-transaction and per-month fees

Per-transaction fees (unit = 'per_transaction') apply to individual transactions. Per-month fees (unit = 'per_month') are flat charges to the bank itself — they don't attach to a specific transaction. The recon formula above only applies to per-transaction fees.

For per-month reconciliation you'd compare the `service_charges` paid over a month to the sum of monthly fees in the schedule — a separate query entirely. Know which class of fee you're auditing.
</fix-monthly-vs-per-txn>

<ex-fee-rate-mismatch>
## Recipe — find contracts where charged rate != schedule rate

Useful for root-cause analysis ("are we using the right rate for this contract at all?"). Groups by contract + fee_category, computes the implied rate per group, compares to schedule.

```sql
SELECT
    t.contract_id,
    t.transaction_type,
    AVG(t.fee_charged / NULLIF(t.transaction_amount, 0)) AS implied_rate,
    MAX(f.fee_percentage)                                AS schedule_rate,
    COUNT(*)                                             AS n
FROM transactions t
LEFT JOIN fee_schedules f
    ON f.contract_id = t.contract_id
    AND f.fee_category = t.transaction_type
WHERE f.fee_percentage IS NOT NULL
GROUP BY 1, 2
HAVING ABS(AVG(t.fee_charged / NULLIF(t.transaction_amount, 0)) - MAX(f.fee_percentage)) > 0.001
ORDER BY n DESC;
```
</ex-fee-rate-mismatch>

<boundaries>
## Boundaries

- These recipes assume the FBE schema (`contracts`, `fee_schedules`, `transactions`). For other schemas, adapt join keys — the expected-fee formula stays the same.
- The POC data is simulated. Real production data will have volume incentives, tiered pricing, and cross-border adjustments that aren't captured in single-row fee rules.
- Always use numeric types (`NUMERIC`, not `FLOAT`) when comparing financial amounts; float rounding causes spurious overcharges.
</boundaries>
