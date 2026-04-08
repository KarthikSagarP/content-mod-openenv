"""Content Moderation Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import ContentModAction, ContentModObservation
except (ImportError, ModuleNotFoundError):
    from models import ContentModAction, ContentModObservation


class ContentModEnv(EnvClient[ContentModAction, ContentModObservation, State]):
    """
    Client for the Content Moderation Environment.

    Example:
        >>> with ContentModEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.post_content)
        ...     result = client.step(ContentModAction(
        ...         verdict="remove", violated_rules=["R1"], severity="high",
        ...         explanation="Hate speech targeting ethnic group"
        ...     ))
    """

    def _step_payload(self, action: ContentModAction) -> Dict:
        return {
            "verdict": action.verdict,
            "violated_rules": action.violated_rules,
            "severity": action.severity,
            "explanation": action.explanation,
        }

    def _parse_result(self, payload: Dict) -> StepResult[ContentModObservation]:
        obs_data = payload.get("observation", {})
        observation = ContentModObservation(
            post_id=obs_data.get("post_id", ""),
            post_content=obs_data.get("post_content", ""),
            author_name=obs_data.get("author_name", ""),
            author_account_age_days=obs_data.get("author_account_age_days", 0),
            author_prior_violations=obs_data.get("author_prior_violations", 0),
            content_policy=obs_data.get("content_policy", ""),
            task_id=obs_data.get("task_id", ""),
            posts_remaining=obs_data.get("posts_remaining", 0),
            feedback=obs_data.get("feedback", ""),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
