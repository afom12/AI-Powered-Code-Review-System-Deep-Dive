"""Dashboard routes"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict
from datetime import datetime, timedelta
import os

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Code Review Dashboard"
    })


@router.get("/stats")
async def dashboard_stats() -> Dict:
    """Get dashboard statistics"""
    # In production, fetch from database
    return {
        "total_reviews": 0,
        "reviews_today": 0,
        "reviews_this_week": 0,
        "average_confidence": 0.0,
        "top_categories": [],
        "feedback_stats": {
            "total_feedback": 0,
            "positive_ratio": 0.0
        }
    }


@router.get("/reviews")
async def dashboard_reviews(
    limit: int = 50,
    offset: int = 0,
    category: str = None,
    priority: str = None
) -> Dict:
    """Get recent reviews"""
    # In production, fetch from database
    return {
        "reviews": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }


@router.get("/analytics")
async def dashboard_analytics(
    days: int = 30
) -> Dict:
    """Get analytics data"""
    # In production, fetch from database
    return {
        "reviews_over_time": [],
        "category_distribution": {},
        "priority_distribution": {},
        "confidence_trends": []
    }

