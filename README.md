<div align="center">
  <a href="https://github.com/open-source-modelling" target="_blank">
    <picture>
      <img src="images/OSM_logo.jpeg" width=280 alt="Logo"/>
    </picture>
  </a>
</div>


<h1 align="center" style="border-botom: none">
  <b>
    🐍 Open-Source Economic Model (OSEM) 🐍     
  </b>
</h1>

</br>

Financial institutions such as life insurers or pension funds have a fiduciary duty to manage long-term commitments to their customers. They initially collect premiums/contributions from their clients, and in exchange promise to provide a guarantee or a higher return at a further date. A large part of risk management in such companies is focused on making sure that the invested assets are managed in such a way as to guarantee the honouring of all commitments (pensions, annuities, insurance claims etc.). One such tool is an asset-liability model. Such models try to simulate three things simultaneously:
 - Evolution and performance of company's investments
 - Evolution of liabilities
 - The impact on profitability by different trading strategies in response to outflows and inflows throughout time  

## Description
The aim of this project is to write an Asset-Liability model that uses agent-based modelling concepts to generate insight on the company's portfolio. All technologies used are open-source and widely used (Pyhon and specific packages such as Pands, Numpy, Datetime etc.).

Ultimately, OSEM should be able to take as input:
 - Description and size of investments
 - Description of economic factors such as interest rates, credit spreads etc.
 - Description and size of outflows
 - Description of the factor influencing the size and timing of outflows
 - Description of planned new business that a company wishes to include into the projection

OSEM should be able to produce a projection of what would happen to the balance sheet of this company in 5, 10, 20, 50 years. 

## Methodology
The development of the OSEM model is still very much an ongoing project. However, a draft of the methodology document can be found in the [Documentation] folder as [OSEM pdf] or a [OSEM Jupyter notebook].

Specific deep dives into topics related to the methodology are available as Jupyter notebooks or PDFs in the [`notebooks/`](notebooks/) directory:
 - Yield-curve calibration/projection [Term structure example]
 - Equity pricing [Equity pricing example]
 - Fixed income pricing [Bond pricing example]
 - Unit-linked liabilities [Unit-linked example]
 - Trading and rebalancing [Trading example]
 - Summary charts [Summary charts example]

See the [`notebooks/README.md`](notebooks/README.md) index for the notebook categories and guidance on adding new exploratory work.

## Getting started
So far, we have produced a simple example that can be run using the `osem` package's entry point. It models a small fictional life insurer: 12 government and corporate bonds, 10 equities and cash, about 3.6m in total, backing either a book of 40 unit-linked policies or a pension-annuity run-off, both worth about 3.0m. The company starts with assets at 120% of liabilities. See [`Input/README.md`](Input/README.md) for the full description of the sample data. This example will grow as more development is committed to the main branch.

The production code lives under [`src/osem/`](src/osem/) as an installable package; `main.py` there (`src/osem/main.py`) is the orchestration entry point.

### Install and run

From the repository root (Python 3.10+):

```bash
pip install -e . && python -m osem.main
```

This installs `osem` in editable mode (from `pyproject.toml`, `src`-layout) alongside its dependencies, and runs the model as a module. Equivalently, once installed, the `osem` console script does the same thing:

```bash
osem
```

Results are written to `Output/Results.csv`.

A simple summary of what goes into the run and what are the outputs can be found in the [Summary pdf]

[Summary pdf]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/notebooks/examples/summary_charts.pdf

## Modelfile

For coding agents, see [AGENTS.md](AGENTS.md) at the repository root. It describes the architecture, methodology, and coding conventions agents should follow when editing this project.

## Ask to the community
Send us an email at gregor@osmodelling.com with feedback, comments, ideas on what we could do better etc. Do you want to help us on this open source project?
Check our wiki page also on [GitHub Wiki]

[GitHub Wiki]: https://github.com/open-source-modelling/Open_Source_Economic_Model/wiki/Introduction
[Documentation]:https://github.com/open-source-modelling/Open_Source_Economic_Model/tree/main/Documentation
[OSEM pdf]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/Documentation/OSEM_Documentation_draft.pdf
[OSEM Jupyter notebook]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/Documentation/OSEM_Documentation_draft.ipynb
[Term structure example]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/notebooks/prototypes/risk_free_curve_projection.pdf
[Equity pricing example]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/notebooks/prototypes/equity_pricing.pdf
[Bond pricing example]: https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/notebooks/prototypes/bond_pricing.pdf
[Unit-linked example]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/notebooks/prototypes/unit_linked.pdf
[Trading example]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/notebooks/prototypes/trading.pdf
[Summary charts example]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/notebooks/examples/summary_charts.pdf
