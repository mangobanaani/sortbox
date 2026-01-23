"""Analytics API endpoints."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException

from src.api.models import AnalyticsResponse
from src.database import (
    count_classifications,
    get_label_counts,
    count_by_method,
    get_average_confidence,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsResponse)
async def get_analytics() -> AnalyticsResponse:
    """Get classification analytics summary.

    Returns a comprehensive analytics summary with counts and metrics:

    - **total_all_time**: Total number of classifications ever recorded
    - **total_today**: Classifications since midnight UTC today
    - **total_this_week**: Classifications in the last 7 days (168 hours)
    - **by_label**: Count of classifications per label (e.g., {"finance": 5, "newsletters": 3})
    - **rule_classifications**: Count of classifications made by rules
    - **llm_classifications**: Count of classifications made by LLM
    - **avg_confidence**: Average confidence score across all classifications (0.0-1.0)

    Raises:
        HTTPException: 500 if database operation fails
    """
    try:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        return AnalyticsResponse(
            total_all_time=count_classifications(),
            total_today=count_classifications(since=today_start),
            total_this_week=count_classifications(since=week_start),
            by_label=get_label_counts(),
            rule_classifications=count_by_method("rule"),
            llm_classifications=count_by_method("llm"),
            avg_confidence=get_average_confidence(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analytics: {str(e)}"
        ) from e
