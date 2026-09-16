import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import json
from decimal import Decimal

from core.database import AsyncSessionLocal
from models.models import RecommendationSnapshot, MarketQuote, TechnicalIndicator, Fundamental, ExchangeEnum
from feature_engine.screener import get_candidate_universe
from agents.graph import agent_pipeline
from agents.state import OpportunityState

logger = logging.getLogger(__name__)

async def fetch_latest_market_context(db: AsyncSession, symbol: str) -> dict:
    """Helper to fetch the latest context to inject into LangGraph."""
    # 1. Price
    quote_stmt = select(MarketQuote).where(MarketQuote.symbol == symbol).order_by(desc(MarketQuote.quote_timestamp)).limit(1)
    quote = (await db.execute(quote_stmt)).scalar_one_or_none()
    
    # 2. Technicals
    tech_stmt = select(TechnicalIndicator).where(TechnicalIndicator.symbol == symbol).order_by(desc(TechnicalIndicator.timestamp)).limit(1)
    tech = (await db.execute(tech_stmt)).scalar_one_or_none()
    
    # 3. Fundamentals
    fund_stmt = select(Fundamental).where(Fundamental.symbol == symbol).order_by(desc(Fundamental.as_of_date)).limit(1)
    fund = (await db.execute(fund_stmt)).scalar_one_or_none()
    
    context = {
        "ltp": float(quote.ltp) if quote else 100.0,
        "technicals": {
            "RSI": float(tech.rsi_14) if tech and tech.rsi_14 else 50,
            "MACD": float(tech.macd) if tech and tech.macd else 0,
            "Volume_Ratio": float(tech.volume_ratio) if tech and tech.volume_ratio else 1.0,
        },
        "fundamentals": {
            "PE": float(fund.pe_ratio) if fund and fund.pe_ratio else 20,
            "ROE": float(fund.roe) if fund and fund.roe else 15,
            "Debt_to_Equity": float(fund.debt_to_equity) if fund and fund.debt_to_equity else 0.5
        }
    }
    return context


async def generate_opportunities_batch():
    """
    Cron job function. Runs the quantitative screen, then runs the multi-agent graph
    on the resulting candidates, and saves high-conviction opportunities to the DB.
    """
    logger.info("Starting Opportunity Generation Batch...")
    
    from core.monitoring import AgentStatusEnum
    
    async with AsyncSessionLocal() as db:
        # 1. Quantitative Screen
        candidates = await get_candidate_universe(db, limit_per_strategy=5)
        if not candidates:
            logger.info("No candidates found in screening phase. Exiting batch.")
            return

        # 1.5 Enriched Context & ML Ranking
        enriched_candidates = []
        for cand in candidates:
            symbol = cand["symbol"]
            ctx = await fetch_latest_market_context(db, symbol)
            cand.update(ctx)
            enriched_candidates.append(cand)
            
        from feature_engine.model import xgboost_ranker
        ranked_candidates = xgboost_ranker.predict(enriched_candidates)
        
        # Top 10 to limit LLM costs
        top_candidates = ranked_candidates[:10]
        logger.info(f"ML Ranker selected top {len(top_candidates)} from {len(candidates)} candidates.")
        
        # 2. Multi-Agent Pipeline Execution
        for cand in top_candidates:
            symbol = cand["symbol"]
            try:
                logger.info(f"Running Agent Pipeline for {symbol} (Matched: {cand['matched_strategies']})...")
                
                # Fetch context
                market_context = await fetch_latest_market_context(db, symbol)
                
                initial_state = {
                    "symbol": symbol,
                    "market_data": market_context,
                    "screener_context": {
                        "matched_strategies": cand["matched_strategies"],
                        "score": cand["aggregate_score"]
                    }
                }
                
                # Execute graph
                final_state = await agent_pipeline.ainvoke(initial_state)
                
                # Check explicit agent failure status (we will inject this in graph.py later, but handle here)
                agent_status = final_state.get("agent_status", AgentStatusEnum.SUCCESS)
                if agent_status != AgentStatusEnum.SUCCESS:
                    logger.warning(f"[{symbol}] Agent pipeline did not complete successfully. Status: {agent_status}")
                    continue
                
                # Extract OpportunityState
                opportunity: OpportunityState = final_state.get("opportunity_state")
                
                # We only save MODERATE or HIGH opportunities to avoid noise
                if opportunity and opportunity.opportunity_level in ["MODERATE", "HIGH"]:
                    logger.info(f"[{symbol}] Found {opportunity.opportunity_level} Opportunity! Saving to DB.")
                    
                    snapshot = RecommendationSnapshot(
                        symbol=symbol,
                        exchange=ExchangeEnum.NSE,
                        current_price=Decimal(str(market_context["ltp"])),
                        opportunity_level=opportunity.opportunity_level,
                        confidence=Decimal(str(opportunity.confidence)),
                        risk_level=opportunity.risk_level,
                        time_horizon=opportunity.time_horizon,
                        opportunity_state_json=opportunity.model_dump(),
                        agent_evidence_json={
                            "market_regime": final_state.get("market_regime_evidence", {}).model_dump() if final_state.get("market_regime_evidence") else {},
                            "historical": final_state.get("historical_evidence", {}).model_dump() if final_state.get("historical_evidence") else {},
                            "technical": final_state.get("technical_evidence", {}).model_dump() if final_state.get("technical_evidence") else {},
                            "fundamental": final_state.get("fundamental_evidence", {}).model_dump() if final_state.get("fundamental_evidence") else {},
                            "entry": final_state.get("entry_evidence", {}).model_dump() if final_state.get("entry_evidence") else {},
                            "risk": final_state.get("risk_evidence", {}).model_dump() if final_state.get("risk_evidence") else {}
                        },
                        critic_feedback=final_state.get("critic_feedback", "")
                    )
                    
                    db.add(snapshot)
                    await db.commit()
                else:
                    logger.info(f"[{symbol}] Skipped. Level: {opportunity.opportunity_level if opportunity else 'NONE'}")
            
            except Exception as e:
                from core.monitoring import log_audit_event
                logger.error(f"Error processing {symbol}: {str(e)}")
                log_audit_event(logger, "AGENT_FAIL", "agent_pipeline", symbol, {"status": "FAILED", "error": str(e)})
                await db.rollback()
                
    logger.info("Batch generation complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(generate_opportunities_batch())
