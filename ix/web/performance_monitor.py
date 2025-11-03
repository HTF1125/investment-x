"""
Performance monitoring utility for Dash application.
Use this to identify bottlenecks and track performance metrics.
"""

import time
import functools
from typing import Callable, Any
from ix.misc import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """Monitor and log performance metrics."""

    _metrics = {}

    @classmethod
    def track_time(cls, func: Callable) -> Callable:
        """Decorator to track function execution time."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                # Store metric
                func_name = f"{func.__module__}.{func.__name__}"
                if func_name not in cls._metrics:
                    cls._metrics[func_name] = {
                        "calls": 0,
                        "total_time": 0,
                        "min_time": float("inf"),
                        "max_time": 0,
                    }

                cls._metrics[func_name]["calls"] += 1
                cls._metrics[func_name]["total_time"] += elapsed
                cls._metrics[func_name]["min_time"] = min(
                    cls._metrics[func_name]["min_time"], elapsed
                )
                cls._metrics[func_name]["max_time"] = max(
                    cls._metrics[func_name]["max_time"], elapsed
                )

                # Log if slow
                if elapsed > 1.0:  # More than 1 second
                    logger.warning(f"⚠️  Slow function: {func_name} took {elapsed:.2f}s")
                elif elapsed > 0.5:  # More than 500ms
                    logger.info(f"⏱️  {func_name} took {elapsed:.2f}s")

                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"❌ {func.__name__} failed after {elapsed:.2f}s: {e}")
                raise

        return wrapper

    @classmethod
    def get_metrics(cls) -> dict:
        """Get current performance metrics."""
        return {
            func_name: {
                **metrics,
                "avg_time": (
                    metrics["total_time"] / metrics["calls"]
                    if metrics["calls"] > 0
                    else 0
                ),
            }
            for func_name, metrics in cls._metrics.items()
        }

    @classmethod
    def print_report(cls):
        """Print performance report."""
        metrics = cls.get_metrics()

        if not metrics:
            logger.info("No performance metrics collected yet")
            return

        logger.info("\n" + "=" * 80)
        logger.info("📊 PERFORMANCE REPORT")
        logger.info("=" * 80)

        # Sort by total time
        sorted_metrics = sorted(
            metrics.items(), key=lambda x: x[1]["total_time"], reverse=True
        )

        for func_name, data in sorted_metrics[:10]:  # Top 10
            logger.info(f"\n{func_name}:")
            logger.info(f"  Calls:     {data['calls']}")
            logger.info(f"  Total:     {data['total_time']:.2f}s")
            logger.info(f"  Average:   {data['avg_time']:.3f}s")
            logger.info(f"  Min:       {data['min_time']:.3f}s")
            logger.info(f"  Max:       {data['max_time']:.3f}s")

        logger.info("\n" + "=" * 80)

    @classmethod
    def reset(cls):
        """Reset all metrics."""
        cls._metrics = {}
        logger.info("Performance metrics reset")


# Convenience decorator
track_performance = PerformanceMonitor.track_time

