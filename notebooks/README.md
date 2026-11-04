# Jupyter notebooks

This directory contains maintained notebooks and their rendered PDFs. Keeping exploratory work outside the repository root makes the executable model files easier to find while preserving notebooks as reproducible technical references.

## Structure

| Directory | Purpose |
| --- | --- |
| [`prototypes/`](prototypes/) | Topic deep dives for pricing (equities, corporate bonds and, in `government_bond_pricing`, government bonds), curves, unit-linked liabilities, and trading |
| [`examples/`](examples/) | Notebooks focused on presenting or summarizing model output |
| [`data/`](data/) | The inputs every notebook reads, and the results of a run on them |

The [`Documentation/`](../Documentation/) directory contains the maintained methodology document. Liability-specific working material remains in [`Liability_Dev/`](../Liability_Dev/).

## Conventions

- Use lowercase `snake_case` names.
- Put a notebook and its rendered PDF in the same topic directory.
- Add a short entry here when introducing a maintained notebook.
- Notebooks locate the repository root by finding `ALM.ini`, so they can be opened and run from either their own directory or the repository root.
- Notebooks read their inputs from `data/`, never from the live `Input/` and `Output/` folders, so they give the same results whatever the model's own inputs hold. Load the configuration with `get_configuration(os.path.join(base_folder, "notebooks", "data", "notebooks.ini"), os)` and take every file path from it.
- Do not commit `.ipynb_checkpoints/`; these are generated automatically by Jupyter.

## Notebook inputs

[`data/notebooks.ini`](data/notebooks.ini) has the same sections and keys as `ALM.ini`, and names the files in [`data/Input/`](data/Input/), a small input set built from the live `Input/` folder of 4 November 2026:

| File | Contents |
| --- | --- |
| `Parameters.csv` | The live run parameters, with 50 projection years, `cashflow` mode, and the EIOPA paths pointing at the copies below |
| `Param_no_VA.csv`, `Curves_no_VA.csv` | The EIOPA risk-free curve of September 2026 |
| `Sector_Spread.csv`, `mortality.csv`, `Unit_Linked_Fund.csv`, `Liability_Cashflow.csv` | Copies of the live files |
| `Cash_Portfolio.csv` | 100,000 of cash |
| `Equity_Portfolio.csv` | Five illustrative shares with dummy ids, 100 units each |
| `Corporate_Bond_Portfolio.csv` | Five corporate bonds from the live file: AB InBev 2028, BNP Paribas 2029, Sanofi 2030, Orange 2033 and Bouygues 2042, 100 units each, at their live prices, from which the calibration on the curve above recovers each bond's observed z-spread |
| `Government_Bond_Portfolio.csv` | Four government bonds from the live file: Germany 0% 2032, France 4% 2055, Italy 2.45% 2050 and Slovenia 0.6875% 2081, 100 units each |
| `Unit_Linked_Policies.csv` | The first ten policies of the live file |

[`data/Output/Results.csv`](data/Output/Results.csv) is the result of a `cashflow` run on these inputs, read by `summary_charts.ipynb`. After changing a file in `data/Input/`, rerun the model on them, then rerun the notebooks and their PDFs:

```
python notebooks/data/make_results.py
```
