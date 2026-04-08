"""
Data models for the Content Moderation Environment.

An AI agent must review user-generated content against a content policy,
classify violations, assign severity, and choose a moderation action.
"""

from enum import Enum
from typing import List, Optional

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class Verdict(str, Enum):
    APPROVE = "approve"
    WARN = "warn"
    REMOVE = "remove"
    ESCALATE = "escalate"


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentModAction(Action):
    """The agent's moderation decision for a piece of content."""

    verdict: str = Field(
        ..., description="Moderation action: approve, warn, remove, or escalate"
    )
    violated_rules: List[str] = Field(
        default_factory=list,
        description="List of policy rule IDs violated (e.g. ['R1', 'R3']). Empty if approved.",
    )
    severity: str = Field(
        default="none",
        description="Severity of violation: none, low, medium, high, or critical",
    )
    explanation: str = Field(
        default="", description="Brief explanation of the moderation decision"
    )


class ContentModObservation(Observation):
    """What the agent sees: a post to moderate plus the content policy."""

    post_id: str = Field(default="", description="Unique ID for the current post")
    post_content: str = Field(default="", description="The user-generated content to review")
    author_name: str = Field(default="", description="Display name of the post author")
    author_account_age_days: int = Field(default=0, description="How old the author's account is in days")
    author_prior_violations: int = Field(default=0, description="Number of prior policy violations by author")
    content_policy: str = Field(default="", description="The content policy rules the agent must enforce")
    task_id: str = Field(default="", description="Current task identifier")
    posts_remaining: int = Field(default=0, description="Number of posts left to moderate in this episode")
    feedback: str = Field(default="", description="Feedback on the previous moderation decision")
