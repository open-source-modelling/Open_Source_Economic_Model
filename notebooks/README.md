# Jupyter notebooks

This directory contains maintained notebooks and their rendered PDFs. Keeping exploratory work outside the repository root makes the executable model files easier to find while preserving notebooks as reproducible technical references.

## Structure

| Directory | Purpose |
| --- | --- |
| [`prototypes/`](prototypes/) | Topic deep dives for pricing, curves, unit-linked liabilities, and trading |
| [`examples/`](examples/) | Notebooks focused on presenting or summarizing model output |

The [`Documentation/`](../Documentation/) directory contains the maintained methodology document. Historical or superseded notebooks remain in [`Archive/`](../Archive/) and liability-specific working material remains in [`Liability_Dev/`](../Liability_Dev/).

## Conventions

- Use lowercase `snake_case` names.
- Put a notebook and its rendered PDF in the same topic directory.
- Add a short entry here when introducing a maintained notebook.
- Do not commit `.ipynb_checkpoints/`; these are generated automatically by Jupyter.
