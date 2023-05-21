<h1 align="center" style="border-botom: none">
  <b>
    🐍 Asset Liability Model POC 🐍     
  </b>
</h1>

</br>

Proof of concept for an integrated asset-liability model. 

 - PROTOTYPE CALIBRATION AND PROJECTION imports the EIOPA curve, calculates the forward rates and uses them to project the spot curve forward.
 A separate instance of the Smith-Wilson algorithm is calibrated to each of the "forward" spot rates using a modified bisection algorithm.
 
 - PROTOTYPE BOND PRICING creates an example of a bond from input data. The ZeroCouponBond class then generates the bond's cash flows togetehr with dates at which the cash flows are paid. The bond is then proced using the imported EIOPA curve using the Smith-Wilson algorithm to calculate the yield at each time-point. With the introduction of a specific modelling date, the cash-flows are modified and the bond is priced usign the yield curve.
 
 Future modules:
 - Module simulating cash outflows from some common types of "life" policies.
 - Model that tradies and simulates the evolution of the economy and the functioning of the company.
 - Aggregation of the balance sheet and the income statement.

For suggestions,comments or inquiries: gregor@osmodelling.com
 
