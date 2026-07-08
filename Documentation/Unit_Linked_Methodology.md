# Unit-Linked Liability Methodology (MVP)

## Scope

Single-pool unit-linked pension model for OSEM MVP. All policies share the same portfolio return `r`.
Policy account values (`MV`) are tracked separately from the asset book; reserve equals the sum of
**active** policy `MV` after stochastic decrements.

Modelling periods are **not required to be exactly one year**. The same `time_frac` used on the
asset side applies to liability steps:

```
time_frac = (current_date − previous_date).days / 365.25
```

Fund parameters (`premium_growth`, `admin_fee`, `lapse_rate`) and mortality rates `q` are defined
on an annual basis and converted to the elapsed period using `time_frac` (see formulas below).

Visual guide: [`Liability_Dev/Unit_Linked_Methodology.html`](../Liability_Dev/Unit_Linked_Methodology.html)

## Liability modes

| Mode | Input | Behaviour |
|------|-------|-----------|
| `cashflow` | `Liability_Cashflow.csv` | Static pre-uploaded outflows (existing POC) |
| `unit_linked` | `Unit_Linked_Policies.csv`, `Unit_Linked_Fund.csv`, `mortality.csv` | Dynamic per-period cash flows from policy state |

Default: `cashflow` (unchanged existing runs).

## Dual cash accounts

| Account | Owner | Credits | Debits |
|---------|-------|---------|--------|
| `bank_account` | Fund / policyholder pool | Gross premium inflows | Full MV on liquidated policies |
| `company_account` | Insurer | Entry fee (gross − net), admin fee | — (accumulates in MVP) |

**Key rule:** Fees never pass through `trade()` — they are insurer revenue, not investable fund liquidity.

## Per-period calculation order

Executed **after** portfolio mark-to-market growth and **before** `trade()`:

1. Capitalize `MV` (and `GV` if guaranteed) by `(1 + r)^time_frac`
2. Grow gross premium; credit full gross to `bank_account`; credit entry fee (gross − net) to `company_account`; allocate net to `MV`
3. Deduct admin fee from `MV`; credit `company_account`
4. Mortality sampling (stochastic, all active policies)
5. Lapse sampling (stochastic, survivors only)
6. Reserve = sum of remaining active `MV`

## Formulas

Let `r` = annual portfolio return rate (same economic basis as asset-side growth) and
`time_frac = (current_date − previous_date).days / 365.25`. The period portfolio return
reported in summary is `(1 + r)^time_frac − 1`.

**Capitalize:** `MV ← MV × (1 + r)^time_frac`; if guaranteed: `GV ← GV × (1 + r)^time_frac`.

**Premium and entry fee (step 2):**
```
gross_premium ← premium × (1 + premium_growth)^time_frac
premium ← gross_premium
entry_fee_cash ← gross_premium × entry_fee          # = gross − net
net_premium ← gross_premium − entry_fee_cash

bank_account += gross_premium
company_account += entry_fee_cash                     # gross − net (insurer revenue)
MV += net_premium
```

`bank_account` is **not** reduced by the entry fee. It receives the full gross premium;
`company_account` records the entry-fee portion (gross − net) as insurer revenue.

**Admin fee (period-scaled):**
```
admin_fee_cash ← MV × (1 − (1 − admin_fee)^time_frac)
MV ← MV − admin_fee_cash
company_account += admin_fee_cash
```

**Mortality (stochastic, period-scaled):** For each active policy, using `random_seed`:
```
age ← floor((current_date − birth_date).days / 365.25)
q_annual ← mortality_table[sex, age]
q_period ← 1 − (1 − q_annual)^time_frac
draw u ~ Uniform(0, 1)
if u < q_period: bank_account −= MV; remove policy
else: keep policy unchanged
```

**Lapse (stochastic, survivors only, period-scaled):**
```
lapse_period ← 1 − (1 − lapse_rate)^time_frac
draw u ~ Uniform(0, 1)
if u < lapse_period: bank_account −= MV; remove policy
else: keep policy unchanged
```

**Reserve:** `sum(MV)` across remaining active policies.

## Random seed

`Parameters.csv` includes `random_seed` (integer). Same seed and inputs produce identical
death/lapse outcomes across runs.

## Cash and reporting sign convention

| Flow | Destination | Summary column | Sign |
|------|-------------|----------------|------|
| Gross premium | `bank_account` | UL gross premium cash flow | Positive |
| Entry fee (gross − net) | `company_account` | UL entry fee cash flow | Positive |
| Net premium (to MV) | — (MV only) | UL net premium allocated | — |
| Admin fee | `company_account` | UL admin fee cash flow | Positive |
| Death liquidation | `bank_account` debit | UL mortality cash flow | Negative |
| Surrender liquidation | `bank_account` debit | UL lapse cash flow | Negative |
| Reserve | — | UL reserve | Level |
| Company balance | — | Company account | Level |
| Policy counts | — | UL policies in force / UL deaths / UL lapses | Count |

## Reconciliation checks

- Reserve bridge: changes reflect capitalization, gross premiums to bank, net to MV, admin fees on survivors, and full MV removals
- t0 reserve = sum of uploaded in-force MV
- Fund cash bridge: start + asset CFs + gross premiums − liquidations + trade ≈ end
- Company account bridge: closing = opening + entry fees + admin fees
- Policy count: in force + deaths + lapses = previous in force
- Reproducibility: same `random_seed` → same outcomes

## Out of scope (MVP)

New business, lifecycle fund migration, full DCF `RESERVE()`, morbidity/retirement tables,
multi-fund asset buckets, company account payouts to shareholders.
