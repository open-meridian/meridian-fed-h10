# Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| **Not answering** | No check has reached the Board's site: no network, a proxy, or the site down | Check the deployment's outbound access to www.federalreserve.gov; the plugin tries again every hour |
| **Answering**, with a warning | An earlier check worked; the last did not | Nothing, usually: the next check runs within the hour. The detail says what failed |
| **N currencies not resolved** | A currency's ISO 4217 code found no cash instrument, or two | Complete or merge the instrument at the Instruments page; the next check records its rates |
| A currency the plugin cannot name | The Board printed a currency this version has no code for | Its rates are not recorded; a new version adds it |
| A day asked is declined, *source silent* | The Board has not published that week yet | Wait for Monday's release |
| A subject declined, *not covered* | H.10 never prices it: a currency quoted per dollar is the price of the dollar, not of itself | Read the dollar's price in that currency, and invert it in the reader |
| Datasets: **Not licensed yet** | No deployment admin has licensed the dataset | Ask a deployment admin to license it on Data sources; the page says so within a minute |
