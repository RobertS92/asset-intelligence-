# Gate 1 report

**Result: `insufficient_data`**

| Metric | Value |
|---|---|
| Positives (12m, test) | 170 |
| Positives (6m, test) | 170 |
| Baseline top-10% precision | 0.5250 |
| Model top-10% precision | 0.5250 |
| Model / baseline | 1.0 |
| Top-5% precision (model) | 0.6000 |
| Brier score | 0.4725 |
| Lead time (months, top 10%) | 3.54796320630749 |
| Leakage check | True |
| Train / test n | 1200 / 400 |

Positives by county: `{'48085': 65, '48201': 50, '48439': 55}`

Pass bar (CONTEXT §6): top-10% precision ≥ 2× baseline and ≥ 200 positives.
If positives < 200, result is `insufficient_data` (not a pass).
