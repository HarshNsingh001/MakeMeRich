from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

from core.database import get_db
from models.models import BacktestExecution, BacktestCase, BacktestResult, Instrument
from evaluation.backtester import evaluate_case, get_historical_snapshot

router = APIRouter()

class BacktestRequest(BaseModel):
    name: str
    target_dates: List[datetime]
    max_stocks: int = 10
    symbols: Optional[List[str]] = None

class ExecutionResponse(BaseModel):
    execution_id: str
    status: str
    message: str

async def process_execution_queue(db: AsyncSession, execution_id: str):
    """Background task to sequentially process all cases in an execution."""
    stmt = select(BacktestCase).where(BacktestCase.execution_id == execution_id)
    cases = (await db.execute(stmt)).scalars().all()
    
    for case in cases:
        # We spawn each sequentially here for V1 to not overload Gemini API rate limits
        await evaluate_case(db, case)
        
    # Mark execution as completed
    exec_stmt = select(BacktestExecution).where(BacktestExecution.execution_id == execution_id)
    execution = (await db.execute(exec_stmt)).scalar_one_or_none()
    if execution:
        execution.status = "COMPLETED"
        execution.completed_at = datetime.utcnow()
        await db.commit()

@router.post("/run", response_model=ExecutionResponse)
async def run_backtest(req: BacktestRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Triggers a new async walk-forward backtest job."""
    
    execution_id = f"BT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"
    
    # Create execution record
    execution = BacktestExecution(
        execution_id=execution_id,
        name=req.name,
        pipeline_version="v1.0",
        model_version="gemini-3.6-flash",
        prompt_version="v1",
        feature_version="v1",
        total_cases=0,
        llm_budget=req.max_stocks * len(req.target_dates),
        started_at=datetime.utcnow()
    )
    db.add(execution)
    
    # Pick stocks
    if req.symbols:
        symbols = req.symbols[:req.max_stocks]
    else:
        # Just grab top stocks by volume or randomly for V1
        stock_stmt = select(Instrument.symbol).where(Instrument.is_active == True).limit(req.max_stocks)
        symbols = (await db.execute(stock_stmt)).scalars().all()
        
    # Create cases
    cases = []
    for symbol in symbols:
        for t_date in req.target_dates:
            case = BacktestCase(
                execution_id=execution_id,
                symbol=symbol,
                target_date=t_date
            )
            cases.append(case)
            db.add(case)
            
    execution.total_cases = len(cases)
    await db.commit()
    
    # Dispatch to background task
    background_tasks.add_task(process_execution_queue, db, execution_id)
    
    return ExecutionResponse(
        execution_id=execution_id,
        status="QUEUED",
        message=f"Queued {len(cases)} cases for execution in the background."
    )

@router.get("/executions")
async def get_executions(db: AsyncSession = Depends(get_db)):
    """List all backtest executions."""
    stmt = select(BacktestExecution).order_by(BacktestExecution.created_at.desc())
    results = (await db.execute(stmt)).scalars().all()
    return results

@router.get("/executions/{execution_id}/results")
async def get_execution_results(execution_id: str, db: AsyncSession = Depends(get_db)):
    """Get metrics and results for a specific execution."""
    stmt = select(BacktestResult).where(BacktestResult.execution_id == execution_id)
    results = (await db.execute(stmt)).scalars().all()
    
    # Calculate simple aggregate metrics
    if not results:
        return {"total_completed": 0, "metrics": {}}
        
    total = len(results)
    high_opps = [r for r in results if r.opportunity_level == "HIGH"]
    
    avg_t5_return = sum(float(r.gross_return_t5) for r in results if r.gross_return_t5) / total
    
    return {
        "execution_id": execution_id,
        "total_completed": total,
        "high_opportunities_found": len(high_opps),
        "metrics": {
            "avg_gross_return_t5": avg_t5_return
        },
        "raw_results": results
    }
