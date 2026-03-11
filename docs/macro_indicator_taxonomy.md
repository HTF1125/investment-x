# Macro Indicator Taxonomy — 4 Categories

**Rule:** Every indicator belongs to exactly ONE group. No overlap.

Legend:
- **[E]** = Existing derived indicator (already in `ix/db/custom/`)
- **[N]** = New — raw series exists in DB, needs new derived function
- **[I]** = Inverted (higher raw value = bearish for that axis)
- `(monthly)` = released monthly, use shorter z-score window

---

## 1. GROWTH (Real economic activity, leading indicators, earnings cycle)

> Measures: Is the economy accelerating or decelerating?

### 1a. PMI / Surveys (diffusion breadth)
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 1 | PMI Mfg Diffusion (% countries rising) | `pmi.py` | [E] | (monthly) |
| 2 | PMI Services Diffusion (% countries rising) | `pmi.py` | [E] | (monthly) |
| 3 | Global Composite PMI | `MPMIGLCA INDEX` | [N] | JPMorgan Global Composite |
| 4 | Global Mfg PMI | `MPMIGLMA INDEX` | [N] | JPMorgan Global Manufacturing |
| 5 | Global Services PMI | `MPMIGLSA INDEX` | [N] | JPMorgan Global Services |
| 6 | China Caixin Mfg PMI | `MPMICNMA INDEX` | [N] | private-sector China |
| 7 | China Caixin Services PMI | `MPMICNSA INDEX` | [N] | private-sector China |
| 8 | Eurozone Composite PMI | `MPMIEZCA INDEX` | [N] | |
| 9 | ASEAN Mfg PMI | `NTCPMIASNMANHE` | [N] | (monthly) |

### 1b. OECD Leading Indicators
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 10 | OECD CLI World Diffusion | `oecd.py` | [E] | (monthly, 4wk lag) |
| 11 | OECD CLI Developed Diffusion | `oecd.py` | [E] | (monthly, 4wk lag) |
| 12 | OECD CLI Emerging Diffusion | `oecd.py` | [E] | (monthly, 4wk lag) |
| 13 | US OECD CLI Amplitude Adjusted | `USA.LOLITOAA.STSA` | [N] | (monthly) |

### 1c. ISM Sub-Components
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 14 | ISM New Orders | `ism.py` | [E] | (monthly) |
| 15 | ISM New Orders minus Inventories | `ism.py` | [E] | (monthly) |
| 16 | ISM Services Breadth | `ism.py` | [E] | (monthly) |
| 17 | ISM Mfg Breadth (% sub-indices > 50) | `ism.py` | [E] | (monthly) |
| 18 | ISM Mfg Momentum Breadth | `ism.py` | [E] | (monthly) |

### 1d. Economic Surprise
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 19 | CESI Breadth (% regions positive) | `sentiment.py` | [E] | |
| 20 | CESI Momentum (% regions improving) | `sentiment.py` | [E] | |

### 1e. Trade / Exports
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 21 | Asian Exports Diffusion | `global_trade.py` | [E] | (monthly) |
| 22 | Asian Exports Momentum | `global_trade.py` | [E] | (monthly) |
| 23 | Global Trade Composite | `global_trade.py` | [E] | (monthly) |
| 24 | Korea Semi Exports YoY | `korea.py` | [E] | (monthly) |

### 1f. Earnings Cycle
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 25 | SPX EPS Revision Ratio | `earnings.py` | [E] | (monthly) |
| 26 | Regional EPS Breadth | `earnings.py` | [E] | |
| 27 | EPS Estimate Dispersion Z | `earnings_deep.py` | [E] | |
| 28 | Earnings Momentum Score | `earnings_deep.py` | [E] | |
| 29 | Earnings Composite | `earnings_deep.py` | [E] | |

### 1g. Cross-Asset Growth Proxies
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 30 | Copper/Gold Ratio | `cross_asset.py` | [E] | market-implied growth |
| 31 | Small/Large Cap Ratio | `intermarket.py` | [E] | |
| 32 | Cyclical/Defensive Ratio | `sector_rotation.py` | [E] | |
| 33 | Baltic Dry Index | `cross_asset.py` | [E] | shipping demand |
| 34 | SOX Momentum | `alt_data.py` | [E] | semi cycle leads |
| 35 | SOX/SPX Ratio | `alt_data.py` | [E] | tech cycle breadth |

### 1h. Nowcasting / Hard Data
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 36 | GDPNow | `nowcasting.py` | [E] | Atlanta Fed |
| 37 | Weekly Economic Index (WEI) | `nowcasting.py` | [E] | NY Fed |
| 38 | WEI Momentum | `nowcasting.py` | [E] | |
| 39 | Initial Claims | `nowcasting.py` | [E] | [I] high = bearish |
| 40 | Nowcast Composite | `nowcasting.py` | [E] | |
| 41 | Industrial Production YoY | `nowcasting.py` | [E] | (monthly) |
| 42 | Capacity Utilization | `nowcasting.py` | [E] | (monthly) |

### 1i. NEW — Consumer / Labor / Confidence
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 43 | Consumer Confidence Index | `CCI INDEX` | [N] | Conference Board (monthly) |
| 44 | Consumer Confidence Present Situation | `CCIPRESENT INDEX` | [N] | (monthly) |
| 45 | UMich Consumer Sentiment | `CONSSENT INDEX` | [N] | |
| 46 | NFIB Small Business Optimism | `USSU0062552` | [N] | (monthly) |
| 47 | Chicago Fed National Activity (CFNAI) | `CFNAIMA3 INDEX` | [N] | 3mo MA (monthly) |
| 48 | Conference Board Leading Index | `USLEI` / `G0M910 INDEX` | [N] | (monthly) |
| 49 | Durable Goods Orders YoY | `DGNOYOY INDEX` | [N] | (monthly) |
| 50 | Retail Sales ex-Auto | `CENRETAIL&FS_MVP_US` | [N] | (monthly) |
| 51 | JOLTS Job Openings | `JOLTTOTL INDEX` | [N] | (monthly) |
| 52 | Nonfarm Payrolls MoM Change | `NFP TCH INDEX` | [N] | (monthly) |
| 53 | Temp Help Employment | `BLSCES6056132001` | [N] | leading indicator (monthly) |
| 54 | Philly Fed Mfg Survey | `PNMABNIN INDEX` | [N] | (monthly) |
| 55 | Empire State Mfg Survey | `EMPRGBCI INDEX` | [N] | (monthly) |

### 1j. NEW — China Hard Data
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 56 | China IP YoY | `EHIUCNY INDEX` | [N] | (monthly) |
| 57 | China Official Mfg PMI | `CPMINDX INDEX` | [N] | NBS PMI (monthly) |
| 58 | China New Loans | `CKAJJU` | [N] | credit pulse (monthly) |

### 1k. NEW — Housing Cycle
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 59 | Housing Starts | `alt_data.py` | [E] | (monthly) |
| 60 | Building Permits | `alt_data.py` | [E] | (monthly) |
| 61 | Case-Shiller Home Price | `CSUSHPINSA` | [N] | (monthly, 2mo lag) |
| 62 | Housing Affordability Index | `alt_data.py` | [E] | (monthly) |
| 63 | New Home Sales | `CENHSOLDTOT_US` | [N] | (monthly) |

---

## 2. INFLATION (Price pressures, expectations, wage dynamics)

> Measures: Are prices accelerating or decelerating?

### 2a. Headline / Core CPI & PCE
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 1 | Inflation Surprise (CPI deviation from trend) | `inflation.py` | [E] | (monthly) |
| 2 | CPI 3M Annualized | `indicators.py` | [E] | (monthly) |
| 3 | PCE Core YoY | `PCE CYOY INDEX` | [N] | Fed's preferred (monthly) |
| 4 | Cleveland Fed Inflation Nowcast | `CLEVCPYC INDEX` | [N] | real-time |
| 5 | Atlanta Fed Sticky CPI 3M Ann | `SCPIS3MO INDEX` | [N] | persistent component |

### 2b. Inflation Expectations (Market-Based)
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 6 | 10Y Breakeven Inflation | `rates.py` | [E] | |
| 7 | Breakeven Momentum | `inflation.py` | [E] | |
| 8 | 5Y Breakeven Inflation | `T5YIE` / `USGGBE05 INDEX` | [N] | shorter-term |
| 9 | 5Y5Y Forward Inflation Swap | `FWISUS55 INDEX` | [N] | long-term anchor |
| 10 | 1Y Inflation Swap | `USSWIT1 CURNCY` | [N] | near-term pricing |
| 11 | 2Y Inflation Swap | `USSWIT2 CURNCY` | [N] | |
| 12 | Euro 5Y5Y Forward Swap | `FWISEU55 INDEX` | [N] | global reflation |

### 2c. Inflation Surprise Indices (Breadth)
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 13 | Citi Inflation Surprise — US | `CSIIUSD INDEX` | [N] | |
| 14 | Citi Inflation Surprise — Eurozone | `EUZPRCSIIEUR` | [N] | |
| 15 | Citi Inflation Surprise — UK | `GBPRCSIIGBP` | [N] | |
| 16 | Citi Inflation Surprise — Japan | `JPPRCSIIJPY` | [N] | |
| 17 | Citi Inflation Surprise — G10 | `WDPRCSIIG10` | [N] | |
| 18 | Citi Inflation Surprise — EM | `WDPRCSIIEM` | [N] | |
| 19 | Citi Inflation Surprise — World | `WDSU8280922` | [N] | |

### 2d. Commodity / Input Prices
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 20 | Commodity Inflation Pressure | `inflation.py` | [E] | oil/copper/CRB z-composite |
| 21 | CRB Commodity Index | `cross_asset.py` | [E] | |
| 22 | ISM Prices Paid | `indicators.py` | [E] | (monthly) |
| 23 | PPI Final Demand YoY | `FDIUFDYO INDEX` | [N] | (monthly) |
| 24 | PPI Core YoY | `FDIUSGYO INDEX` | [N] | (monthly) |
| 25 | Import Prices YoY | `IMP1YOY% INDEX` | [N] | (monthly) |
| 26 | WTI Crude Oil | `alt_data.py` | [E] | energy component |
| 27 | Natural Gas | `alt_data.py` | [E] | energy component |

### 2e. Wage / Shelter
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 28 | Atlanta Fed Wage Growth Tracker | `WGTROVER INDEX` | [N] | (monthly) |
| 29 | Avg Hourly Earnings | `US.LMWAGES` | [N] | (monthly) |
| 30 | ECI YoY | `ECI YOY INDEX` | [N] | (quarterly) |
| 31 | Shelter CPI | `CPSHSHLT INDEX` | [N] | stickiest component (monthly) |
| 32 | Used Cars CPI | `CUSR0000SETA02` | [N] | volatile leading (monthly) |

### 2f. Survey-Based Inflation
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 33 | NFIB Price Plans (Net %) | `SBOIPPNP INDEX` | [N] | small biz (monthly) |
| 34 | NFIB Higher Prices | `SBOIPRIC INDEX` | [N] | (monthly) |
| 35 | UMich 1Y Inflation Expectations | `USSU0014396` | [N] | |
| 36 | UMich 5Y Inflation Expectations | `USSU1094524` | [N] | |
| 37 | Eurozone HICP YoY | `ECCPEMUY INDEX` | [N] | (monthly) |

---

## 3. LIQUIDITY (Central banks, monetary policy, credit conditions, funding)

> Measures: Is money/credit expanding or contracting?

### 3a. Central Bank Balance Sheets
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 1 | Fed Total Assets | `central_bank.py` | [E] | |
| 2 | Fed Assets YoY | `central_bank.py` | [E] | |
| 3 | Fed Assets Momentum (13wk) | `central_bank.py` | [E] | |
| 4 | Fed Net Liquidity (WALCL-TGA-RRP) | `liquidity.py` | [E] | core signal |
| 5 | G4 Balance Sheet Total | `central_bank.py` | [E] | |
| 6 | G4 Balance Sheet YoY | `central_bank.py` | [E] | |
| 7 | CB Liquidity Composite | `central_bank.py` | [E] | |
| 8 | Treasury Securities Held | `WSHOSHO` | [N] | Fed holdings detail |

### 3b. TGA / Fiscal Flow
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 9 | TGA Drawdown (13wk change) | `liquidity.py` | [E] | [I] refill = drains |
| 10 | Treasury Net Issuance | `liquidity.py` | [E] | [I] supply pressure |

### 3c. Money Supply
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 11 | US M2 | `liquidity.py` | [E] | |
| 12 | US M2 YoY | `M2 INDEX` | [N] | growth rate |
| 13 | Global M2 YoY | `liquidity.py` | [E] | (monthly, 6wk lag) |
| 14 | Global Liquidity YoY | `liquidity.py` | [E] | (monthly, 4wk lag) |
| 15 | ECB M2 YoY | `ECMSM2Y INDEX` | [N] | |
| 16 | China M2 YoY | `china_em.py` | [E] | |
| 17 | China M2 Momentum | `china_em.py` | [E] | |

### 3d. Credit Conditions
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 18 | Credit Impulse (2nd deriv) | `liquidity.py` | [E] | (monthly) |
| 19 | Bank Credit Impulse | `fund_flows.py` | [E] | |
| 20 | Consumer Credit Growth | `fund_flows.py` | [E] | |
| 21 | China Credit Impulse | `china_em.py` | [E] | (monthly) |
| 22 | Senior Loan Officer Survey | `DRTSCIS` | [N] | [I] tightening = bearish (quarterly) |
| 23 | Commercial Paper Outstanding | `COMPOUT` | [N] | short-term funding |
| 24 | Bank Loans & Leases (weekly) | `TOTLL` | [N] | |
| 25 | Business Loans | `BUSLOANS` | [N] | (monthly) |
| 26 | Consumer Revolving Credit | `CCLACBW027SBOG` | [N] | weekly |
| 27 | Real Estate Loans | `REALLN` | [N] | (monthly) |

### 3e. Financial Conditions Indices
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 28 | FCI US (custom composite) | `fci.py` | [E] | core signal |
| 29 | Bloomberg US Financial Conditions | `BFCIUS INDEX` | [N] | alternative FCI |
| 30 | Chicago Fed NFCI | `NFCIINDX` | [N] | weekly |
| 31 | Chicago Fed NFCI Credit Sub-Index | `NFCICRDT` | [N] | credit channel |
| 32 | Financial Conditions Credit | `credit_deep.py` | [E] | BBB+HY+bank credit |

### 3f. Policy Rates / Yield Curve
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 33 | Policy Rate Level | `monetary_policy.py` | [E] | [I] higher = tighter |
| 34 | Rate Cut Expectations | `monetary_policy.py` | [E] | |
| 35 | Rate Expectations Momentum | `monetary_policy.py` | [E] | |
| 36 | Rate Cut Probability Proxy | `central_bank.py` | [E] | |
| 37 | Term Premium Proxy | `monetary_policy.py` | [E] | [I] |
| 38 | G4 Rate Divergence | `central_bank.py` | [E] | [I] instability |
| 39 | US 3M-10Y Spread | `rates.py` | [E] | recession indicator |
| 40 | US 2s10s Spread | `rates.py` | [E] | |
| 41 | ECB Deposit Rate | `EUORDEPO INDEX` | [N] | |
| 42 | 1Y Real Interest Rate | `REAINTRATREARAT1YE` | [N] | |

### 3g. Real Rates
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 43 | US 10Y Real Yield (TIPS) | `rates.py` | [E] | [I] higher = tighter |
| 44 | 5Y Real Yield | `DFII5` | [N] | [I] |
| 45 | Real 10Y (based on core CPI) | `RR10CUS INDEX` | [N] | alternative measure |

### 3h. China/EM Liquidity
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 46 | PBoC Easing Proxy | `china_em.py` | [E] | |
| 47 | EM Sovereign Spread | `china_em.py` | [E] | [I] wider = stress |
| 48 | JP Morgan EMBI Global Spread | `JPEIGLSP INDEX` | [N] | [I] |
| 49 | JP Morgan EM Currency Index | `FXJPEMCS INDEX` | [N] | EM FX liquidity |

### 3i. Funding / Leverage
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 50 | Margin Debt YoY | `fund_flows.py` | [E] | leverage cycle |
| 51 | Reserve Balances (FARWCUR) | `FARWCUR INDEX` | [N] | bank reserves |
| 52 | RRP Facility Outstanding | `RRPONTSYD` | [E] | already used in net liq |

---

## 4. TACTICAL (Short-term risk appetite, positioning, volatility, stress)

> Measures: Is the market oversold/overbought? Risk-on or risk-off?

### 4a. Volatility Structure
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 1 | VIX | `cross_asset.py` | [E] | contrarian (high = bullish) |
| 2 | VIX Term Structure (VIX/VIX3M) | `volatility.py` | [E] | >1 = backwardation |
| 3 | VIX Term Spread (VIX3M-VIX) | `volatility.py` | [E] | neg = stress |
| 4 | VIX-Realized Vol Spread | `intermarket.py` | [E] | fear premium |
| 5 | Vol Risk Premium Z-Score | `volatility.py` | [E] | |
| 6 | SKEW Index | `volatility.py` | [E] | tail risk priced |
| 7 | SKEW Z-Score | `volatility.py` | [E] | |
| 8 | VVIX/VIX Ratio | `volatility.py` | [E] | vol-of-vol |
| 9 | Gamma Exposure Proxy | `volatility.py` | [E] | dealer gamma |
| 10 | Realized Vol Regime | `volatility.py` | [E] | [I] expansion = bearish |
| 11 | VXN (Nasdaq Vol) | `VXN INDEX` | [N] | |
| 12 | RVX (Russell 2000 Vol) | `RVX INDEX` | [N] | small-cap stress |
| 13 | OVX (Oil Vol) | `OVX INDEX` | [N] | commodity stress |
| 14 | GVZ (Gold Vol) | `GVZ INDEX` | [N] | haven demand vol |

### 4b. Credit Stress (Short-Term)
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 15 | HY Spread | `rates.py` | [E] | [I] wider = stress |
| 16 | IG Spread | `rates.py` | [E] | [I] |
| 17 | BBB Spread | `rates.py` | [E] | [I] |
| 18 | HY/IG Ratio | `rates.py` | [E] | [I] rises in stress |
| 19 | HY Spread Momentum | `credit_deep.py` | [E] | [I] widening = bearish |
| 20 | HY Spread Velocity | `credit_deep.py` | [E] | [I] panic detection |
| 21 | IG/HY Compression | `credit_deep.py` | [E] | rising = risk appetite |
| 22 | Credit Stress Index | `credit_deep.py` | [E] | [I] composite |
| 23 | Credit Cycle Phase | `credit_deep.py` | [E] | |
| 24 | FCI Stress (VIX+MOVE+spreads) | `fci.py` | [E] | [I] |
| 25 | Credit-Equity Divergence | `intermarket.py` | [E] | [I] SPX vs HY gap |
| 26 | Bloomberg HY OAS | `LF98OAS INDEX` | [N] | [I] alternative HY |
| 27 | Bloomberg IG OAS | `LUACOAS INDEX` | [N] | [I] |
| 28 | CMBS OAS | `LUCMOAS INDEX` | [N] | [I] real estate stress |
| 29 | MBS OAS | `LUMSOAS INDEX` | [N] | [I] mortgage stress |

### 4c. Sentiment & Positioning
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 30 | Put/Call Z-Score | `sentiment.py` | [E] | contrarian (high = bullish) |
| 31 | CBOE Put Volume | `OPIXEQTP INDEX` | [N] | raw hedging volume |
| 32 | CBOE Call Volume | `OPIXEQTC INDEX` | [N] | speculation volume |
| 33 | ERP Z-Score | `equity_valuation.py` | [E] | valuation support |
| 34 | CFTC SPX Net Positioning | `sentiment.py` | [E] | |
| 35 | CFTC USD Net Positioning | `sentiment.py` | [E] | |
| 36 | CFTC Gold Net Positioning | `sentiment.py` | [E] | |
| 37 | CFTC 10Y Treasury Net | `sentiment.py` | [E] | |
| 38 | CFTC JPY Net Positioning | `sentiment.py` | [E] | |
| 39 | CFTC 2Y Treasury Net | `CFTC_UST2Y_NET` | [N] | front-end positioning |
| 40 | CFTC EUR Net Positioning | `CFTC_EUR_NET` | [N] | |
| 41 | CFTC Oil Net Positioning | `CFTC_OIL_NET` | [N] | |
| 42 | CFTC Extreme Count | `sentiment.py` | [E] | # assets at extremes |
| 43 | NFIB Small Biz Profits (actual) | `SBOIPROF INDEX` | [N] | sentiment proxy |
| 44 | Gold ETF Demand | `SGLDWDEQ INDEX` | [N] | haven flows |
| 45 | Central Bank Gold Demand | `SGLDWDUQ INDEX` | [N] | de-dollarization |

### 4d. Risk Appetite / Breadth
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 46 | Risk Appetite (composite) | `rates.py` | [E] | |
| 47 | Risk On/Off Breadth | `intermarket.py` | [E] | % signals risk-on |
| 48 | US Sector Breadth | `sector_rotation.py` | [E] | % sectors > SPX |
| 49 | US Sector Dispersion | `sector_rotation.py` | [E] | high = divergence |
| 50 | Momentum Breadth | `factors.py` | [E] | % assets positive mom |
| 51 | Momentum Composite | `factors.py` | [E] | multi-asset score |
| 52 | Risk Rotation Index | `fund_flows.py` | [E] | equity/bond/HY composite |
| 53 | Equity/Bond Flow Proxy | `fund_flows.py` | [E] | SPY/TLT rotation |

### 4e. Cross-Asset Regime
| # | Indicator | Source | Status | Notes |
|---|-----------|--------|--------|-------|
| 54 | Equity/Bond Correlation Z | `correlation_regime.py` | [E] | regime signal |
| 55 | Safe Haven Demand | `correlation_regime.py` | [E] | [I] gold+tsy strength |
| 56 | Tail Risk Index | `correlation_regime.py` | [E] | [I] VIX+skew+spreads |
| 57 | Cross-Asset Correlation | `correlation_regime.py` | [E] | [I] high = contagion |
| 58 | Diversification Index | `correlation_regime.py` | [E] | |
| 59 | Correlation Surprise | `correlation_regime.py` | [E] | short vs long deviation |
| 60 | Dollar Index | `cross_asset.py` | [E] | [I] strong $ = risk-off |
| 61 | Citi Macro Risk Index (ST) | `WDPRMRIST INDEX` | [N] | short-term risk |
| 62 | Citi Macro Risk Index (LT) | `WDPRMRILT INDEX` | [N] | long-term risk |
| 63 | Citi EM Macro Risk Index | `MRIEM INDEX` | [N] | EM-specific risk |
| 64 | NYSE Down Volume | `DVOLNYE INDEX` | [N] | selling pressure |

---

## Summary

| Category | Existing [E] | New [N] | Total |
|----------|-------------|---------|-------|
| Growth | 42 | 21 | 63 |
| Inflation | 7 | 30 | 37 |
| Liquidity | 33 | 19 | 52 |
| Tactical | 38 | 26 | 64 |
| **TOTAL** | **120** | **96** | **216** |

---

## Key Reassignment Decisions

These indicators moved between categories vs the old system:

| Indicator | Old Category | New Category | Rationale |
|-----------|-------------|-------------|-----------|
| CESI Breadth/Momentum | Growth (regime) | **Growth** | stays — economic surprise is growth signal |
| Credit Impulse | Liquidity | **Liquidity** | stays — credit creation is liquidity |
| HY/IG/BBB Spreads | Liquidity (in research app) | **Tactical** | moved — spreads are short-term stress |
| FCI Stress | Tactical | **Tactical** | stays |
| Dollar Index | Tactical | **Tactical** | stays — short-term risk signal |
| Margin Debt YoY | Flows (in research app) | **Liquidity** | moved — leverage is funding/liquidity |
| Eq/Bond Flow Proxy | Flows (in research app) | **Tactical** | moved — rotation is positioning |
| Copper/Gold | Growth | **Growth** | stays — growth expectations proxy |
| Baltic Dry | Growth | **Growth** | stays — shipping = trade activity |
| 10Y Breakeven | was in both Liquidity & Inflation | **Inflation** | moved — it's inflation expectations |
| ISM Prices Paid | Inflation | **Inflation** | stays |
| US 10Y Real | Liquidity | **Liquidity** | stays — real rate = liquidity conditions |
| Policy Rate | Liquidity | **Liquidity** | stays — monetary policy stance |
| Nowcasting (WEI, Claims) | was separate | **Growth** | moved — real-time activity |
| Housing Starts/Permits | was alt_data | **Growth** | moved — housing cycle = growth |
| Consumer Credit | was fund_flows | **Liquidity** | stays in credit channel |
| Senior Loan Officer Survey | unused | **Liquidity** | new — credit tightening |
| All Citi Inflation Surprise | unused | **Inflation** | new — inflation breadth |
| All Inflation Swaps | unused | **Inflation** | new — market expectations |
| Wage/Shelter data | unused | **Inflation** | new — stickiest components |
| Regional vol indices | unused | **Tactical** | new — cross-asset stress |
| CFTC EUR/Oil/2Y | unused | **Tactical** | new — positioning breadth |
