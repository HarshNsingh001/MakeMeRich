**INDIAN EQUITY INTELLIGENCE PLATFORM**

System Architecture, Data Platform & Multi-Agent Decision Support Specification

*Implementation handoff for an AI-assisted Indian equity research product*

| **Document item** | **Value**                                                                                                                              |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| Primary scope     | Indian listed equities first; F&O and additional asset classes later                                                                   |
| Client platforms  | Responsive Web + Android + iOS                                                                                                         |
| Core backend      | Python + FastAPI                                                                                                                       |
| Primary datastore | PostgreSQL + TimescaleDB                                                                                                               |
| Cache / real-time | Redis + WebSockets                                                                                                                     |
| AI approach       | Quantitative engines + ML + multi-agent orchestration + adversarial critique                                                           |
| Document purpose  | Provide a senior-architect-level blueprint that an implementation agent can convert into code, infrastructure, schemas, APIs and tasks |

**Important product principle:** The platform is a decision-support and market-intelligence system, not a guaranteed-profit engine. It should present evidence, uncertainty, risk, scenarios and confidence so the end user can make the investment decision.

# Contents

- 1\. Product vision and goals

- 2\. Current scope and non-goals

- 3\. Data-source and broker-API strategy

- 4\. System architecture

- 5\. Data platform and data contracts

- 6\. Multi-agent architecture

- 7\. Decision and opportunity engine

- 8\. Entry-price analysis

- 9\. Risk and adversarial critique

- 10\. Backtesting and model evaluation

- 11\. Backend APIs

- 12\. Real-time architecture

- 13\. Frontend and mobile architecture

- 14\. Security and operational architecture

- 15\. Infrastructure and technology stack

- 16\. Database schema outline

- 17\. Example agent contracts

- 18\. User experience and screen architecture

- 19\. Development roadmap

- 20\. Key architectural rules and trade-offs

- 21\. V1 implementation checklist

- 22\. Future F&O architecture

- 23\. Product/financial-data considerations

# 1. Product Vision and Goals

The target product is an Indian-market intelligence platform that continuously evaluates equity-market conditions and individual stocks, combines historical, technical, fundamental and current-market evidence, and produces transparent opportunity analyses. The platform should identify situations that may be interesting for a user to research rather than claim certainty about future returns.

## The core user question is:

“Given the current Indian market state and this stock’s current price, what does the available evidence say about the opportunity, possible entry zones, risks, invalidation conditions and appropriate time horizon?”

The product should answer that through a sequence of independent analyses, not through a single LLM prompt.

Raw Market Data -\> Clean/Validate -\> Quantitative Features -\> Independent Analyses  
-\> Critic / Risk  
-\> Decision Synthesis  
-\> Evidence + Uncertainty + Scenarios

# 2. Current Scope and Non-Goals

V1 should focus on Indian listed equity stocks. Keep the architecture extensible, but do not implement F&O, commodities and mutual funds in the first production milestone.

## V1 universe and evidence types:

- NSE equities first; BSE can be added in the data-normalization layer

- NIFTY 50 / NIFTY 100 as an initial high-quality universe, then expand to the broader equity universe

- OHLC, volume, VWAP, market capitalization and corporate actions

- Fundamentals such as revenue, profit, EPS, ROE, ROCE, debt, cash flow, valuation metrics, shareholding and earnings context

- Technical indicators such as RSI, MACD, EMA/SMA, ATR, Bollinger Bands, ADX, support/resistance, volume behavior and momentum

- Market context including NIFTY, sector indices, India VIX, breadth and relative strength

## Non-goals for V1:

- Direct order execution and automated trading

- Guaranteeing profit or returns

- Using an LLM as the source of truth for prices or calculations

- Allowing unvalidated public data directly into recommendation logic

- F&O/Options strategy automation before the equity engine is stable and backtested

# 3. Data-Source and Broker-API Strategy

The earlier architecture discussion identified broker APIs as a practical way to obtain market data rather than relying only on direct exchange endpoints. The exact product terms, quotas, segment coverage and historical depth must be verified against each provider’s current documentation before production because pricing and API policies can change.

| **Provider**         | **Earlier assessment**                                                            | **Useful capabilities for this project**                                                                                                                    | **Architectural note**                                                                                         |
|----------------------|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| FYERS                | API/data access presented as a free option                                        | Live market data, quotes, historical data, F&O/equity coverage, commodity support was discussed                                                             | Good candidate for initial prototyping; validate current quotas, segment coverage and expired-contract history |
| Upstox               | API/data access presented as free                                                 | Quotes, live data, historical candles, F&O/options data; analytics-token concept was discussed                                                              | Strong candidate for market-data experiments and analytics; validate limits and historical availability        |
| Angel One SmartAPI   | API presented as free                                                             | Full market data including LTP, OHLC, volume, OI, total buy/sell quantity and top-of-book depth; historical endpoints across NSE/BSE/F&O/MCX were discussed | Broad exchange/segment coverage; validate current rate limits, data permissions and historical depth           |
| Dhan                 | Trading API described as free; data API described as paid in the prior discussion | Historical, real-time data, option chain, OI, Greeks and market data                                                                                        | Consider when paid market-data access is acceptable                                                            |
| Zerodha Kite Connect | Market-data API described as paid in prior discussion                             | Mature live and historical ecosystem                                                                                                                        | Strong mature ecosystem, but not the default choice when the primary constraint is zero API cost               |

Important distinction: “API is free” and “all market data is free” are not equivalent. Also, broker market data is not the same thing as full exchange order-level data. Full order-by-order / tick-by-tick / deep historical order data may require licensed or commercial feeds.

## For this product, normalize all providers behind one internal interface so the rest of the system is vendor-independent:

MarketDataProvider  
get_quote(symbol)  
get_candles(symbol, timeframe, start, end)  
get_market_depth(symbol)  
get_instrument_master()  
get_corporate_actions(symbol)  
get_option_chain(symbol, expiry) \# future F&O phase  
get_historical_oi(symbol, start, end) \# future F&O phase

# 4. System Architecture

+---------------------------+  
\| Web / Android / iOS \|  
\| Responsive user clients \|  
+-------------+-------------+  
\|  
API Gateway  
\|  
+----------------------+----------------------+  
\| \|  
Auth / User / Portfolio Market / Analysis APIs  
\| \|  
+----------------------+----------------------+  
\|  
Decision Platform  
\|  
+----------------+--------------+----------------+----------------+  
\| \| \| \| \|  
Market Regime Historical Technical Fundamental Risk  
Engine Engine Engine Engine Engine  
\| \| \| \| \|  
+----------------+---------------+----------------+---------------+  
\|  
Entry / Opportunity  
\|  
Critic / Validator  
\|  
Decision Synthesizer  
\|  
+--------------+--------------+  
\| \|  
Opportunity State Evidence / Reasons  
\| \|  
+--------------+--------------+  
\|  
User-facing insight  
  
Data foundation below all of the above:  
Providers -\> Ingestion -\> Validation -\> Normalization -\> Time-series DB -\> Features -\> Cache

## Recommended deployment model:

- Start as a modular monolith rather than premature microservices.

- Keep clear internal modules and interfaces so data, analysis and AI components can be extracted into services later.

- Parallelize independent agent/engine computations for latency, but centralize final decision synthesis.

# 5. Data Platform and Data Contracts

Data quality is a higher-order dependency than the LLM. The platform should preserve raw provider data, normalized market data, derived features and recommendation snapshots separately.

Raw provider layer  
raw_market_data  
  
Normalized layer  
market_candles  
instruments  
corporate_actions  
fundamentals  
  
Derived feature layer  
technical_indicators  
market_regime_features  
valuation_features  
relative_strength_features  
  
Decision layer  
agent_runs  
recommendation_snapshots  
evidence_items  
outcome_evaluations

## Recommended data integrity practices:

- Timestamp every market observation and every agent result.

- Store source/provider identifiers and data timestamps.

- Version feature calculations and models.

- Handle stock splits, bonuses, dividends, rights issues, mergers and demergers through a corporate-action layer.

- Prevent look-ahead bias by enforcing time-aware joins and as-of data access.

- Keep raw data immutable where licensing permits and rebuild normalized/derived data from known source versions.

# 6. Multi-Agent Architecture

The multi-agent system is best treated as a structured evidence pipeline. Agents should not “chat freely” and then produce a recommendation. Each agent should return a typed, auditable result.

| **\#** | **Agent / Engine**               | **Question answered**                                            | **Primary inputs**                                                                         | **Primary output**              |
|--------|----------------------------------|------------------------------------------------------------------|--------------------------------------------------------------------------------------------|---------------------------------|
| 1      | Market Regime Agent              | Overall Indian market state                                      | Trend, volatility, breadth, index conditions, sector context                               | Market regime + evidence        |
| 2      | Historical Stock Agent           | Long-term and historical behavior of a stock                     | Returns, drawdowns, volatility, support/resistance history, valuation history              | Historical context              |
| 3      | Current Market / Technical Agent | Current price action and technical state                         | RSI, MACD, EMA/SMA, volume, ATR, ADX, momentum, breakouts/breakdowns                       | Current signal state            |
| 4      | Fundamental / Valuation Agent    | Business quality and valuation context                           | Revenue, profit, EPS, ROE/ROCE, debt, cash flow, P/E, P/B, EV/EBITDA, peer context         | Fundamental/valuation thesis    |
| 5      | Entry / Price Agent              | Potential entry zones under the current scenario                 | Support, ATR, volatility, historical reaction, volume profile, valuation and market regime | Entry scenarios                 |
| 6      | Risk / Bear Agent                | Try to break the current thesis                                  | Contradicting signals, macro/sector risk, invalidation conditions, downside scenarios      | Risk thesis / invalidation      |
| 7      | Critic / Evidence Validator      | Challenge agent claims and consistency                           | Claim verification, conflicting evidence, stale inputs, unsupported statements             | Validation result               |
| 8      | Decision Synthesizer             | Combine structured evidence into a user-facing opportunity state | All validated agent outputs                                                                | Opportunity state + explanation |

# 7. Decision and Opportunity Engine

Do not reduce the whole product to a single “BUY score.” A more robust representation separates opportunity, confidence, risk, time horizon, evidence strength and invalidation conditions.

Opportunity State  
opportunity_level: LOW \| MODERATE \| HIGH  
confidence: 0..1  
risk_level: LOW \| MEDIUM \| HIGH  
time_horizon: INTRADAY \| SWING \| 1-3M \| 6-12M \| 3-5Y  
evidence_strength: 0..1  
supporting_factors: \[...\]  
contradictory_factors: \[...\]  
invalidation_conditions: \[...\]  
data_timestamp: ...  
model_version: ...

Quantitative engines should produce the measurable signals. LLMs should interpret, summarize and challenge evidence. The final synthesis should only be generated from validated structured inputs.

# 8. Entry-Price Analysis

For a question such as “is the current price attractive?”, the system should not invent a price target. It should derive one or more scenario zones from measurable market structure and explain the evidence.

Example:  
Current price: Rs 1,425  
  
Possible zones (illustrative architecture output, not a live recommendation):  
Zone A: Rs 1,390 - 1,410 -\> primary pullback zone  
Zone B: Rs 1,350 - 1,375 -\> deeper historical support zone  
  
Evidence may include:  
- historical support reactions  
- ATR / volatility bands  
- moving averages  
- volume profile  
- valuation distribution  
- current market regime  
- sector strength

Every entry zone should carry its own evidence and invalidation logic. The system must avoid implying that a lower price automatically means a lower-risk investment.

# 9. Risk and Adversarial Critique

The risk layer should actively search for evidence that would invalidate the bullish or positive thesis. This is more useful than having multiple agents independently repeat the same narrative.

Bull / Opportunity Thesis  
vs  
Risk / Bear Thesis  
\|  
v  
Evidence Validator  
\|  
v  
Decision Synthesizer  
\|  
+--\> supporting evidence  
+--\> contradictory evidence  
+--\> invalidation conditions  
+--\> uncertainty / confidence

# 10. Backtesting and Model Evaluation

Every production recommendation path should be measurable against later outcomes. Store the complete decision snapshot so the team can evaluate what the system knew at the time and what happened afterward.

Recommendation snapshot  
timestamp  
symbol  
price  
market state  
technical state  
fundamental state  
valuation state  
agent outputs  
critic output  
final opportunity state  
model versions  
data versions  
  
Outcome evaluation  
+1d / +7d / +30d / +90d / +180d  
realized return  
max adverse excursion  
max favorable excursion  
volatility  
thesis invalidation  
benchmark-relative result

## Backtesting principles:

- Use time-sliced, out-of-sample evaluation.

- Use walk-forward testing for models that depend on time-varying distributions.

- Protect against look-ahead and survivorship bias.

- Evaluate transaction-cost and slippage assumptions where relevant.

- Compare signal quality by regime, sector and time horizon.

- Track calibration of confidence estimates instead of assuming confidence equals correctness.

# 11. Backend APIs

The frontend should never talk directly to data vendors or agent internals. Use the backend as the consistent contract and policy boundary.

| **Endpoint**                      | **Purpose**                                                | **Example response**         |
|-----------------------------------|------------------------------------------------------------|------------------------------|
| GET /market/overview              | Current market regime, index snapshot, breadth, volatility | Market regime object         |
| GET /stocks                       | Search/filter equity universe                              | Paged stock list             |
| GET /stocks/{symbol}              | Stock profile and current quote                            | Instrument + current state   |
| GET /stocks/{symbol}/chart        | Historical OHLCV / derived series                          | Time series                  |
| GET /stocks/{symbol}/technical    | Technical state                                            | Indicators + evidence        |
| GET /stocks/{symbol}/fundamentals | Fundamental and valuation context                          | Metrics + periods            |
| GET /stocks/{symbol}/analysis     | Combined multi-agent analysis                              | Opportunity state + evidence |
| GET /stocks/{symbol}/opportunity  | Current entry/opportunity state                            | Zones + risks + confidence   |
| GET /opportunities/today          | Candidate stock universe after quantitative screening      | Opportunity cards            |
| GET /recommendations/{id}         | Historical, auditable recommendation snapshot              | Full decision snapshot       |
| WS /market/stream                 | Live market updates to clients                             | Quote/market event stream    |

# 12. Real-Time Architecture

Broker / market WebSocket  
\|  
v  
Market Data Collector  
\|  
+----\> validation / normalization  
\|  
v  
Redis  
\|  
+----\> analytics cache  
\|  
v  
WebSocket Gateway  
\|  
+----\> Web / Android / iOS

Clients should share the backend’s market stream rather than each client establishing its own broker connection. This allows centralized rate limiting, normalization, caching, authentication and observability.

# 13. Frontend and Mobile Architecture

Recommended platform strategy based on the stated requirement for responsive web, Android and iOS:

- Web: Next.js + React + TypeScript.

- Mobile: React Native + Expo.

- Shared domain types: TypeScript contracts generated from OpenAPI where practical.

- Charts: a financial charting library suitable for responsive time-series rendering.

- Design: mobile-first cards and progressive disclosure so dense financial detail does not overwhelm smaller screens.

## Core screens:

- Market Pulse

- Opportunity / candidate list

- Stock detail

- Technical analysis

- Fundamental/valuation analysis

- Entry-zone scenarios

- Agent debate / evidence view

- Risk & invalidation view

- Saved stocks / watchlist

- Portfolio (future phase)

- Alerts / notifications

# 14. Security and Operational Architecture

- OAuth/JWT-based authentication and authorization.

- Do not store broker credentials in plaintext. Use a secrets-management service such as AWS Secrets Manager or Azure Key Vault.

- Apply rate limiting and abuse protection at the API gateway.

- Separate user data from market-data infrastructure.

- Audit important recommendation requests and model decisions.

- Use observability for data freshness, provider failures, queue latency, agent failures, model version, and recommendation generation latency.

- Use feature flags for provider or model rollouts.

- Version prompts, agent contracts, feature code and models so historical decisions remain explainable.

# 15. Infrastructure and Technology Stack

| **Layer**        | **Recommended technology**               | **Reason**                                                           |
|------------------|------------------------------------------|----------------------------------------------------------------------|
| Backend API      | Python + FastAPI                         | Strong fit for data/ML workloads and typed APIs                      |
| Time series DB   | PostgreSQL + TimescaleDB                 | Relational integrity plus time-series queries                        |
| Cache / stream   | Redis                                    | Low-latency latest-price and computed-signal access                  |
| Async jobs       | Celery or Dramatiq                       | Scheduled ingestion, feature computation, agent runs and alerts      |
| Object storage   | S3 / Azure Blob                          | Raw files, historical datasets, model artifacts                      |
| Frontend web     | Next.js + React + TypeScript             | Responsive web and mature data-dashboard ecosystem                   |
| Mobile           | React Native + Expo                      | Shared TypeScript ecosystem for Android/iOS                          |
| ML               | scikit-learn, XGBoost, PyTorch as needed | Classical models first; deep learning only when justified            |
| AI orchestration | LangGraph or custom orchestration        | Explicit stateful multi-step agent graph                             |
| Containers       | Docker                                   | Repeatable local and cloud environments                              |
| CI/CD            | GitHub Actions                           | Automated tests, builds and deployments                              |
| Cloud            | AWS or Azure                             | Managed databases, secrets, object storage, queues and observability |

# 16. Database Schema Outline

users  
portfolios  
watchlists  
  
instruments  
market_candles  
market_quotes  
market_depth_snapshots  
corporate_actions  
  
fundamentals  
financial_periods  
shareholding  
sector_classification  
  
technical_indicators  
market_regime_features  
valuation_features  
  
agent_runs  
agent_evidence  
agent_claims  
critic_runs  
recommendation_snapshots  
recommendation_outcomes  
model_versions  
data_versions  
  
alerts  
notifications  
audit_logs

# 17. Example Agent Contracts

Every agent should produce structured output. A representative contract is below.

{  
"agent": "technical_agent",  
"symbol": "RELIANCE",  
"timestamp": "2026-09-16T14:30:00+05:30",  
"signals": {  
"trend": "neutral",  
"momentum": "bearish",  
"volume": "positive"  
},  
"evidence": \[  
{  
"metric": "RSI",  
"value": 34,  
"interpretation": "weak momentum"  
}  
\],  
"confidence": 0.74,  
"data_timestamp": "...",  
"model_version": "technical-v3"  
}

## Representative final opportunity object:

{  
"symbol": "RELIANCE",  
"market_regime": "NEUTRAL",  
"opportunity": {  
"level": "MODERATE",  
"confidence": 0.71  
},  
"current_price": 1425,  
"entry_zones": \[  
{"min": 1390, "max": 1410, "type": "PRIMARY"},  
{"min": 1350, "max": 1375, "type": "SECONDARY"}  
\],  
"time_horizon": "6-12 months",  
"supporting_factors": \[\],  
"risk_factors": \[\],  
"invalidation_conditions": \[\],  
"agent_consensus": "...",  
"critic": "...",  
"data_timestamp": "...",  
"model_version": "decision-v1"  
}

# 18. User Experience and Screen Architecture

## Example market overview:

MARKET PULSE  
NIFTY 50 25,XXX +0.72%  
Market Regime NEUTRAL / BULL / BEAR (system-defined)  
Volatility MODERATE  
  
TODAY'S OPPORTUNITIES  
  
RELIANCE Rs 1,425  
Opportunity Moderate  
Risk Medium  
Confidence 71%  
  
Entry Zones  
Rs 1,390 - 1,410 Primary  
Rs 1,350 - 1,375 Secondary  
  
WHY?  
+ Valuation context  
+ Historical support  
+ Sector context  
- Weak momentum  
- Market volatility  
  
VIEW FULL ANALYSIS -\>

The final UI should make the evidence visible. Users should be able to drill down from an opportunity card into the market, historical, technical, fundamental, entry, risk and critic evidence that produced the current state.

# 19. Development Roadmap

| **Phase**                  | **Goal**                                                | **Deliverables**                                                                                                           |
|----------------------------|---------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| V1 - Data + Analytics      | Establish the trustworthy data foundation               | NSE equities; historical data ingestion; normalized schema; indicators; fundamentals; stock dashboard; data-quality checks |
| V2 - AI Analysis           | Add independent evidence interpretation                 | Market, historical, technical, fundamental and risk agents; structured outputs; critic; synthesis; audit snapshots         |
| V3 - Opportunity Engine    | Generate candidate opportunities from the full universe | Quantitative screening; multi-agent analysis; entry zones; risk validation; opportunity states; notifications              |
| V4 - Personal Intelligence | Personalize the evidence to user context                | Risk profile, horizon, portfolio context, sector exposure, watchlists, personalized alerts                                 |
| V5 - F&O                   | Expand to derivatives                                   | Option chain, OI, IV, Greeks, futures basis, OI buildup/unwinding, expiry-aware logic                                      |

F&O should not be added to V1. Options and futures introduce expiry, strike, CE/PE, OI, IV, Greeks, volatility-surface and term-structure complexity that multiplies the data and model surface area.

# 20. Key Architectural Rules and Trade-offs

| **\#** | **Rule**                                    | **Why it matters**                                                                                                 |
|--------|---------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| 1      | AI is above the data foundation             | LLMs interpret evidence; they do not define market truth.                                                          |
| 2      | Quant first, LLM second                     | Filter thousands of securities with deterministic/ML signals before spending LLM compute.                          |
| 3      | Independent agents must have different jobs | Do not create five agents that all repeat the same narrative.                                                      |
| 4      | Use adversarial critique                    | A dedicated risk/bear path should search for evidence that breaks the thesis.                                      |
| 5      | Everything must be timestamped              | Market data, features, model versions and agent outputs must be reproducible.                                      |
| 6      | Keep a full decision snapshot               | This is required for auditability, debugging and later outcome analysis.                                           |
| 7      | Start modular monolith                      | Avoid premature microservices. Extract services after real scale or ownership boundaries emerge.                   |
| 8      | Protect against look-ahead bias             | All historical and fundamental joins must obey “what was known then.”                                              |
| 9      | Treat corporate actions as first-class data | Historical prices and returns depend on accurate adjustment logic.                                                 |
| 10     | Do not expose “profit guaranteed” language  | Use probabilistic, evidence-based opportunity states and risk/invalidation views.                                  |
| 11     | Provider abstraction is mandatory           | Vendor changes should not require rewriting the analytics/agent layers.                                            |
| 12     | Design for extensibility                    | The same architecture should later support F&O, commodities and other datasets without rewriting the client shell. |

# 21. V1 Implementation Checklist

- Create repository structure for backend, frontend-web, mobile, infrastructure and shared contracts.

- Implement instrument master ingestion and symbol normalization.

- Implement one market-data provider adapter first; add a second provider adapter before production.

- Build raw -\> normalized -\> derived data pipeline.

- Set up PostgreSQL + TimescaleDB and Redis.

- Create market-candle schema and corporate-action handling.

- Build technical-indicator pipeline.

- Build fundamentals ingestion and normalization.

- Build market-regime calculation for NIFTY/sector/breadth/volatility.

- Build stock detail APIs and responsive web UI.

- Build market pulse and opportunity-card UX shell.

- Implement structured agent interfaces, starting with analysis-only mode.

- Implement critic/risk validator.

- Implement recommendation snapshots and audit logs.

- Create walk-forward/backtest harness before enabling any production opportunity feed.

- Add monitoring for data freshness, API failures, queue latency and agent failures.

- Create provider failover/health status and data-quality checks.

# 22. Future F&O Architecture

Once the equity platform is stable, extend the normalized data model and decision engine rather than creating a separate product. F&O introduces new dimensions:

- Expiry calendars

- Strike ladders

- Call/Put structure

- Open interest and change in OI

- Implied volatility

- Greeks

- Futures basis

- OI buildup / unwinding

- Volatility term structure

- Volatility surface

- Liquidity and spread

- Contract rollovers

Equity Intelligence Engine  
+  
Futures Intelligence Engine  
+  
Options Intelligence Engine  
+  
Volatility Engine  
\|  
v  
Derivatives Opportunity / Risk Layer

# 23. Product / Financial-Data Considerations

- Market-data licensing, redistribution rights and commercial usage terms must be checked before exposing provider data to end users.

- Broker API quotas, websocket limits, historical retention and segment permissions vary by provider and can change.

- “Current price” and “historical price” are different data-quality problems; store source and timestamp for both.

- A provider API that exposes quotes is not automatically a replacement for licensed exchange-grade full-depth or order-level data.

- Expired options and deep historical derivatives datasets are frequently subject to different availability and licensing constraints than current-market quotes.

- All data-provider assumptions in this document should be treated as architecture candidates to validate against current provider documentation before production deployment.

## Reference note

This document consolidates the architecture and implementation concepts discussed in the conversation. It intentionally turns the earlier conversational recommendations into a neutral technical specification. Provider pricing, API access and exchange-data terms are time-sensitive; the implementation team should re-check the current official provider documentation and exchange licensing requirements before committing to a vendor.

# Appendix A - Target Repository Structure

repo/  
apps/  
web/  
mobile/  
services/  
api/  
market_data/  
feature_engine/  
agents/  
recommendations/  
notifications/  
packages/  
shared_types/  
market_models/  
ui/  
data/  
migrations/  
seeds/  
infra/  
docker/  
terraform/  
ml/  
training/  
backtests/  
evaluation/  
docs/  
architecture/  
api/

# Appendix B - Example Agent Graph

START  
\|  
+--\> Load symbol + as-of market data  
\|  
+--\> Market Regime -----------+  
\| \|  
+--\> Historical Stock --------+  
\| \|  
+--\> Technical ---------------+----\> Evidence Aggregator  
\| \|  
+--\> Fundamental/Valuation ---+  
\| \|  
+--\> Entry/Price -------------+  
\| \|  
+--\> Risk/Bear ---------------+  
\|  
v  
Critic / Validator  
\|  
v  
Decision Synthesizer  
\|  
v  
Opportunity + Evidence + Risk  
\|  
v  
API / UI / Alert

*End of system-design handoff*
