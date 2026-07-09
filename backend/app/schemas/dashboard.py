"""Pydantic schemas for the dashboard endpoint."""

from pydantic import BaseModel


class StatCard(BaseModel):
    label: str
    value: int


class InsightItem(BaseModel):
    label: str
    value: str


class ContinueItem(BaseModel):
    resource_type: str
    resource_id: str
    title: str
    last_accessed: str


class ActivityItem(BaseModel):
    event_type: str
    description: str
    created_at: str


class DashboardResponse(BaseModel):
    user_name: str
    stats: list[StatCard]
    insights: list[InsightItem]
    continue_learning: list[ContinueItem]
    recent_activity: list[ActivityItem]
