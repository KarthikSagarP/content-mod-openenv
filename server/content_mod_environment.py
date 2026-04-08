"""
Content Moderation Environment Implementation.

An agent reviews user-generated posts against a content policy. Each episode
presents a sequence of posts; the agent must classify, assign severity, and
choose a moderation action for each one.
"""

import os
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import ContentModAction, ContentModObservation
    from .tasks import CONTENT_POLICY, TASKS
except ImportError:
    from models import ContentModAction, ContentModObservation
    from server.tasks import CONTENT_POLICY, TASKS


def _grade_action(action: ContentModAction, truth: dict) -> tuple[float, str]:
    """Grade a moderation action against the ground truth.

    Returns (reward, feedback_string). Reward in [0.0, 1.0].
    Scoring breakdown:
      - Correct verdict:       0.40
      - Correct rules:         0.30  (partial: Jaccard similarity)
      - Correct severity:      0.20  (partial: 1 - distance/4)
      - Explanation quality:   0.10  (mentions key concepts)
    """
    feedback_parts = []
    total = 0.0

    # --- Verdict (0.40) ---
    v_agent = action.verdict.strip().lower()
    v_truth = truth["verdict"].strip().lower()
    if v_agent == v_truth:
        total += 0.40
        feedback_parts.append("Verdict: correct")
    else:
        # Partial credit for close verdicts
        close_pairs = {
            frozenset({"warn", "remove"}): 0.15,
            frozenset({"remove", "escalate"}): 0.20,
            frozenset({"warn", "escalate"}): 0.10,
        }
        pair = frozenset({v_agent, v_truth})
        partial = close_pairs.get(pair, 0.0)
        total += partial
        feedback_parts.append(
            f"Verdict: wrong (expected '{v_truth}', got '{v_agent}', +{partial:.2f})"
        )

    # --- Violated rules (0.30) ---
    rules_agent = set(r.strip().upper() for r in action.violated_rules)
    rules_truth = set(r.strip().upper() for r in truth["violated_rules"])

    if not rules_truth and not rules_agent:
        total += 0.30
        feedback_parts.append("Rules: correct (none violated)")
    elif rules_truth or rules_agent:
        union = rules_truth | rules_agent
        intersection = rules_truth & rules_agent
        jaccard = len(intersection) / len(union) if union else 0.0
        rule_score = 0.30 * jaccard
        total += rule_score
        feedback_parts.append(
            f"Rules: {intersection} correct out of expected {rules_truth} (+{rule_score:.2f})"
        )
    # --- Severity (0.20) ---
    sev_order = ["none", "low", "medium", "high", "critical"]
    s_agent = action.severity.strip().lower()
    s_truth = truth["severity"].strip().lower()

    if s_agent in sev_order and s_truth in sev_order:
        dist = abs(sev_order.index(s_agent) - sev_order.index(s_truth))
        sev_score = 0.20 * max(0.0, 1.0 - dist / 4.0)
        total += sev_score
        if dist == 0:
            feedback_parts.append("Severity: correct")
        else:
            feedback_parts.append(
                f"Severity: off by {dist} level(s) (expected '{s_truth}', got '{s_agent}', +{sev_score:.2f})"
            )
    else:
        feedback_parts.append(f"Severity: invalid value '{s_agent}'")

    # --- Explanation (0.10) ---
    explanation_lower = action.explanation.lower()
    key_concepts = truth.get("key_concepts", [])
    if key_concepts:
        matches = sum(1 for kc in key_concepts if kc.lower() in explanation_lower)
        concept_ratio = matches / len(key_concepts)
        expl_score = 0.10 * concept_ratio
        total += expl_score
        feedback_parts.append(
            f"Explanation: mentioned {matches}/{len(key_concepts)} key concepts (+{expl_score:.2f})"
        )
    else:
        total += 0.10
        feedback_parts.append("Explanation: ok")

    return round(total, 4), " | ".join(feedback_parts)


class ContentModEnvironment(Environment):
    """
    Content Moderation Environment.

    Each episode presents a queue of user-generated posts. The agent reviews
    one post per step and submits a moderation decision. Reward is computed
    per-post via a multi-factor grader.

    Tasks:
        easy_moderation   — obvious violations & safe content (3 posts)
        medium_moderation — context-dependent & borderline (4 posts)
        hard_moderation   — adversarial, obfuscated, nuanced (5 posts)
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task_id = os.getenv("CONTENT_MOD_TASK", "easy_moderation")
        self._posts = []
        self._current_idx = 0
        self._feedback = ""

    def reset(self) -> ContentModObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        task = TASKS.get(self._task_id, TASKS["easy_moderation"])
        self._posts = list(task["posts"])  # shallow copy
        self._current_idx = 0
        self._feedback = ""

        post = self._posts[0]
        return ContentModObservation(
            post_id=post["id"],
            post_content=post["content"],
            author_name=post["author_name"],
            author_account_age_days=post["author_account_age_days"],
            author_prior_violations=post["author_prior_violations"],
            content_policy=CONTENT_POLICY,
            task_id=self._task_id,
            posts_remaining=len(self._posts) - 1,
            feedback="Episode started. Review the post and submit your moderation decision.",
            done=False,
            reward=0.0,
        )

    def step(self, action: ContentModAction) -> ContentModObservation:
        self._state.step_count += 1

        # Grade current post
        post = self._posts[self._current_idx]
        reward, feedback = _grade_action(action, post["truth"])

        self._current_idx += 1
        done = self._current_idx >= len(self._posts)

        if done:
            return ContentModObservation(
                post_id=post["id"],
                post_content="",
                author_name="",
                author_account_age_days=0,
                author_prior_violations=0,
                content_policy="",
                task_id=self._task_id,
                posts_remaining=0,
                feedback=f"[Post {post['id']}] {feedback}. Episode complete.",
                done=True,
                reward=reward,
            )

        next_post = self._posts[self._current_idx]
        return ContentModObservation(
            post_id=next_post["id"],
            post_content=next_post["content"],
            author_name=next_post["author_name"],
            author_account_age_days=next_post["author_account_age_days"],
            author_prior_violations=next_post["author_prior_violations"],
            content_policy=CONTENT_POLICY,
            task_id=self._task_id,
            posts_remaining=len(self._posts) - self._current_idx - 1,
            feedback=f"[Post {post['id']}] {feedback}",
            done=False,
            reward=reward,
        )

    @property
    def state(self) -> State:
        return self._state
