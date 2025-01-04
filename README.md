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
The aim of this project is to write an Asset-Liability model that uses agent-based modelling concepts and LLMs to extract insight on the company's portfolio.  All technologies used are open-source and widely used (Pyhon and specific packages such as Pands, Numpy, Datetime etc., Ollama).

Ultimately, OSEM should be able to take as input:
 - Description and size of investments
 - Description of economic factors such as interest rates, credit spreads etc.
 - Description and size of outflows
 - Description of the factor influencing the size and timing of outflows
 - Description of planned new business that a company wishes to include into the projection

OSEM should be able to produce a projection of what would happen to the balance sheet of this company in 5, 10, 20, 50 years. 

## Methodology
The development of the OSEM model is still very much an ongoing project. However, a draft of the methodology document can be found in the [Documentation] folder as [OSEM pdf] or a [OSEM Jupyter notebook].

Specific deep dives into topics related to the methodology are available as Jupyter notebooks or pdf-s. The topics covered so far are:
 - Yield-curve calibration/projection [Term structure example] 
 - Equity pricing [Equity pricing example]
 - Fixed income pricing [Bond pricing example]
 - Summary charts [Summary charts example]

## Getting started
So far, we have produced a simple example that can be ran using the script `main.py`. A hypothetical portfolio of 3 equities and 3 corporate bonds and a single fixed liability cash flow profile. This example will grow as more development is committed to the main branch.
To run the example:
 - Download the OSEM repository
 - Open the Anaconda command prompt
 - Make the OSEM repository the root folder
 - Run the script main.py
 - In the folder Output, look at the cash flow time-series

A simple summary of what goes into the run and what are the outputs can be found in the [Summary pdf]

[Summary pdf]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/_SUMMARY%20CHARTS%20FOR%20OSEM%20RUN.pdf

## Llama agents
OSEM uses a simple LLM agent for trading decisions. In particular we are excited to try mimicing human decisionmakers in the future versions. This was inspired by for example in [Generative Agent Simulations of 1,000 People]. This slows the model considerably since each decision must use the LLM inference call which is slower than deterministic logic. To make sure the agents run, first run [llama3.2] using [Ollama]. 

## Modelfile
If you use copilots to further develope the code, we have started assembling a modelingfile that can be used to refine the prompts. The file is located in the [llm_modelfile] folder.

## Ask to the community
Send us an email at gregor@osmodelling.com with feedback, comments, ideas on what we could do better etc. Do you want to help us on this open source project?
Check our wiki page also on [GitHub Wiki]

[Generative Agent Simulations of 1,000 People]:https://arxiv.org/pdf/2411.10109
[Ollama]:https://ollama.com/
[llama3.2]: https://ollama.com/library/llama3.2
[llm_modelfile]:https://github.com/open-source-modelling/Open_Source_Economic_Model/tree/main/llm_modelfile
[GitHub Wiki]: https://github.com/open-source-modelling/Open_Source_Economic_Model/wiki/Introduction
[Documentation]:https://github.com/open-source-modelling/Open_Source_Economic_Model/tree/main/Documentation
[OSEM pdf]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/Documentation/OSEM_Documentation_draft.pdf
[OSEM Jupyter notebook]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/Documentation/OSEM_Documentation_draft.ipynb
[Term structure example]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/Documentation/Archive/_PROJECTION%20OF%20THE%20RISK%20FREE%20CURVE%20AND%20RECALIBRATION_v2.pdf
[Equity pricing example]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/Documentation/Archive/_PROTOTYPE%20EQUITY%20PRICING_v2.pdf
[Bond pricing example]: https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/Documentation/Archive/_PROTOTYPE%20BOND%20PRICING_v2.pdf
[Summary charts example]:https://github.com/open-source-modelling/Open_Source_Economic_Model/blob/main/_SUMMARY%20CHARTS%20FOR%20OSEM%20RUN.pdf
