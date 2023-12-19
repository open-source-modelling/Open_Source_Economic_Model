<div align="center">
  <a href="https://github.com/open-source-modelling" target="_blank">
    <picture>
      <img src="images/Open-source modelling-logos_transparent.png" width=280 alt="Logo"/>
    </picture>
  </a>
</div>


<h1 align="center" style="border-botom: none">
  <b>
    🐍 Open Source Asset Liability (OSAL) 🐍     
  </b>
</h1>

</br>

## Problem
Financial institutions such as life insurers or pension funds have a fiduciary duty to manage long-term commitments to their customers. They initially collect premiums/contributions from their clients, and in exchange promise to provide a guarantee or a higher return at a further date. A large part of risk management in such companies is focused on making sure that the invested assets are managed in such a way as to guarantee the honouring of all commitments (pensions, annuities, insurance claims etc.). One such tool is an asset-liability model. Such models try to simulate three things simultaneously:
 - Evolution and performance of company's investments
 - Evolution of liabilities
 - The ability of the company to adapt and manage the interplay between investments and liabilities throughout time  

Historically, these models were either implemented internally at a great cost to the organisation, or by a specialized vendor under a proprietary license. 

## Solution
There might be a third way. An open implementation that can be upgraded and maintained by the wider community of interested parties. Actuaries, students, companies, regulators, and other interested professionals. The result of this thought is the Open Source Asset Liability model (OSAL). A project with the aim to write a model using technologies that are open-source and widely used (Pyhon and specific packages such as Pands, Numpy, Datetime etc.).

Ultimately, OSAL should be able to take as input:
 - Description and size of investments
 - Description of economic factors such as interest rates, credit spreads etc.
 - Description and size of liabilities
 - Description of the factor influencing the size and timing of liability outflows
 - Projected new business that a company plans to achieve

The OSAL should be able to produce a projection of what would happen to the balance sheet of this company under the assumptions provided as input (In a simplified way). 

## Methodology
The development of the OSAL model is still very much an ongoing project. However, a draft of the methodology document can be found in the [Documentation] folder as [OSAL pdf] or a [OSAL Jupyter notebook].

Specific deep dives into topics related to the methodology are available as Jupyter notebooks or pdf-s. We found this to be a usefull method to open the floor to feedback. Note that notebooks are currently sparsely maintained. If interested, let us know and we can update the notebook to the latest version. The specific topics are:
 - Yield-curve calibration/projection [Term structure Jupyter notebook] 
 - Equity pricing [Equity pricing Jupyter notebook]
 - Fixed income pricing [Bond pricing Jupyter notebook]

## Getting started
So far, we have produced a simple example that can be ran using the script `POC_main.py`. A hypothetical portfolio of a few equities and a single fixed liability cash flow profile. This example will grow as more development is committed to the main branch.

## Ask to the community
Send us an email at gregor@osmodelling.com with feedback, comments, ideas on what we could do better etc. Do you want to help us on this (very niche) open source project?

[Documentation]:https://github.com/open-source-modelling/Asset_Liability_Model_POC_python/tree/main/Documentation
[OSAL pdf]:https://github.com/open-source-modelling/Asset_Liability_Model_POC_python/blob/main/Documentation/OSAL_POC_Documentation_draft.pdf
[OSAL Jupyter notebook]:https://github.com/open-source-modelling/Asset_Liability_Model_POC_python/blob/main/Documentation/OSAL_POC_Documentation_draft.ipynb
[Term structure Jupyter notebook]:https://github.com/open-source-modelling/Asset_Liability_Model_POC_python/blob/main/Documentation/PROTOTYPE%20CALIBRATION%20AND%20PROJECTION.ipynb
[Equity pricing Jupyter notebook]:https://github.com/open-source-modelling/Asset_Liability_Model_POC_python/blob/main/Documentation/PROTOTYPE%20EQUITY%20PRICING.ipynb
[Bond pricing Jupyter notebook]: https://github.com/open-source-modelling/Asset_Liability_Model_POC_python/blob/main/Documentation/PROTOTYPE%20BOND%20PRICING.ipynb
