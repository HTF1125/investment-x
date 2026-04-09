"""Seed the strategy_result table with all strategy backtests.

Usage:
    python -m ix.core.backtesting.strategies.seed              # all (production + batch)
    python -m ix.core.backtesting.strategies.seed --production # production only (10)
    python -m ix.core.backtesting.strategies.seed --batch      # batch only (191)
    python -m ix.core.backtesting.strategies.seed CreditCycle  # single (partial match)
"""

import sys
import time
from ix.common import get_logger

logger = get_logger(__name__)


def seed_production():
    from ix.core.backtesting.strategies import all_strategies
    strategies = all_strategies()
    total = len(strategies)
    for i, cls in enumerate(strategies, 1):
        name = cls.__name__
        logger.info(f"[{i}/{total}] {name}...")
        try:
            instance = cls()
            instance.backtest().save()
            perf = instance.calculate_metrics(instance.nav)
            logger.info(f"  Sharpe: {perf['Sharpe']:.3f}, CAGR: {perf['CAGR']:.2%}")
        except Exception as e:
            logger.error(f"  Failed: {e}")
    return total


def seed_batch():
    from ix.core.backtesting.batch import build_batch_registry
    strategies = build_batch_registry()
    total = len(strategies)
    success = 0
    for i, s in enumerate(strategies, 1):
        sid = s.strategy_id
        logger.info(f"[{i}/{total}] {sid}...")
        try:
            s.backtest().save()
            perf = s.calculate_metrics(s.nav)
            logger.info(f"  Sharpe: {perf['Sharpe']:.3f}, CAGR: {perf['CAGR']:.2%}")
            success += 1
        except Exception as e:
            logger.error(f"  Failed: {e}")
    return success


def seed_one(query: str):
    from ix.core.backtesting.strategies import STRATEGY_REGISTRY
    from ix.core.backtesting.batch import build_batch_registry

    # Try production first
    matches = [n for n in STRATEGY_REGISTRY if query.lower() in n.lower()]
    for name in matches:
        cls = STRATEGY_REGISTRY[name]
        logger.info(f"Running {name}...")
        cls().backtest().save()
        logger.info(f"Saved {name}")

    # Try batch
    if not matches:
        batch = build_batch_registry()
        for s in batch:
            if query.lower() in s.strategy_id.lower():
                logger.info(f"Running {s.strategy_id}...")
                s.backtest().save()
                logger.info(f"Saved {s.strategy_id}")
                matches.append(s.strategy_id)

    if not matches:
        logger.error(f"No strategy matching '{query}'")


if __name__ == "__main__":
    args = sys.argv[1:]
    t0 = time.time()

    if not args or args == ["--all"]:
        n1 = seed_production()
        n2 = seed_batch()
        logger.info(f"Done. {n1} production + {n2} batch in {time.time()-t0:.0f}s")
    elif args[0] == "--production":
        n = seed_production()
        logger.info(f"Done. {n} production strategies in {time.time()-t0:.0f}s")
    elif args[0] == "--batch":
        n = seed_batch()
        logger.info(f"Done. {n} batch strategies in {time.time()-t0:.0f}s")
    else:
        seed_one(args[0])
        logger.info(f"Done in {time.time()-t0:.0f}s")
