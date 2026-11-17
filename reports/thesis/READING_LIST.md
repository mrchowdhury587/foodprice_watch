# Reading list for the report (report_v5)

Every paper cited in `report_v5/ref.bib`. The bibliographic details were checked on 2026-11-17 against the page given in `ref.bib`; the report text was written from the **abstracts only**. Before submission, read each paper (at least abstract, method and results) and tick "read". Anything in the report that needs more than the abstract is marked `\todo{check in paper}`.

| Key | Paper | What the report uses it for | Read |
|---|---|---|---|
| agripricebd | Muhammad et al. (2026), AgriPriceBD benchmark, arXiv 2604.06227 | Closest work: Bangladeshi daily retail prices from government reports; naive persistence wins on near-random-walk commodities. **One co-author is listed as Mahmudul Hasan: check whether this is your supervisor.** | [ ] |
| onionnardl | Mila et al. (2023), PLOS ONE | Onion price transmission in Bangladesh (imported onion prices and local prices) | [ ] |
| jubayer2024 | Jubayer et al. (2024), J. Bangladesh Agricultural University | Onion price forecasting in Bangladesh with SARIMA (monthly, peak in Oct-Nov) | [ ] |
| cpd2026 | Centre for Policy Dialogue (2026) dialogue report | Context: food is 59 % of the CPI, food inflation near 14 %; supply-chain margins. **Its summary uses words the report must not use; cite only the context figures.** | [ ] |
| tcb | Trading Corporation of Bangladesh, daily price reports | Data source. **Confirm the exact page URL of the daily report.** | [ ] |
| baquedano2015 | Baquedano (2015), FAO GIEWS | Indicator of price anomalies (weighted compound growth rates); basis of SDG 2.c.1 | [ ] |
| wfpalps2014 | WFP (2014), ALPS guidance note | Alert for Price Spikes: price against its seasonal trend, alert levels | [ ] |
| klenow2010 | Klenow and Malin (2010), Handbook of Monetary Economics | Price stickiness facts: prices change infrequently; many changes are small | [ ] |
| nakamura2008 | Nakamura and Steinsson (2008), QJE | Frequency of price change; role of temporary sales | [ ] |
| cavallo2018 | Cavallo (2018), REStat | Daily (scraped) prices: long durations, few tiny changes | [ ] |
| ogol2025 | Ogol et al. (2025), Frontiers in AI | ML (XGBoost / gradient boosting, LightGBM) for Kenyan food prices; WFP data; deployed web app | [ ] |
| manogna2025 | Manogna et al. (2025), Scientific Reports | Deep learning vs ARIMA etc. for 23 Indian commodities, daily wholesale prices; **no naive benchmark** (a point for the review) | [ ] |
| meese1983 | Meese and Rogoff (1983), J. International Economics | Classic result: the random walk is hard to beat out of sample | [ ] |
| makridakis2022 | Makridakis et al. (2022), IJF | M5 competition: large-scale evaluation of forecasting methods on retail data | [ ] |
| hyndman2002 | Hyndman et al. (2002), IJF | Automatic exponential smoothing (ETS), the ETS candidate | [ ] |
| lightgbm | Ke et al. (2017), NeurIPS | LightGBM | [ ] |
| hk2006 | Hyndman and Koehler (2006), IJF | Scale-free error measures, relative MAE | [ ] |
| dm1995 | Diebold and Mariano (1995), JBES | Test of equal forecast accuracy | [ ] |
| hln1997 | Harvey, Leybourne and Newbold (1997), IJF | Small-sample correction of the DM test | [ ] |
| holm1979 | Holm (1979), Scand. J. Statistics | Multiple-test correction | [ ] |
| lee2014 | Lee and Scholtes (2014), IJF | Prediction intervals from empirical out-of-sample errors (the ranges) | [ ] |
| kupiec | Kupiec (1995), J. Derivatives | Coverage test of the ranges | [ ] |
| gradio | Abid et al. (2019), arXiv | Gradio, the monitor's interface | [ ] |
| statsforecast | Garza et al. (2022), StatsForecast | Software for ETS | [ ] |
| openmeteo | Zippenfenig (2023), Open-Meteo | Weather data source | [ ] |

Not found or dropped: a "Uganda food price, Springer 2024" study named in the project plan could not be found (only bachelor's projects and a 2025 IMF working paper turned up); it is not cited.

Checked on 2026-11-17 against the publisher pages (the report text now follows them; reading the full papers is still needed): cpd2026 ("59 per cent of the consumer price index basket"; food inflation "around 14 per cent at its peaks", no date given); onionnardl (monthly wholesale and retail prices of local and imported onion 2006-2020, NARDL, imported prices lead local prices); jubayer2024 (production 1970-2022, CV 71.10 %, SARIMA(1,0,2)(1,1,1)12 for monthly prices, peak in October-November).
