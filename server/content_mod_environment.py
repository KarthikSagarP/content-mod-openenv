"""
Content Moderation Environment Implementation.

An agent reviews user-generated posts against a content policy. Each episode
presents a sequence of posts; the agent must classify, assign severity, and
choose a moderation action for each one.

Grading factors:
  - Verdict correctness (0.35)
  - Rule identification via Jaccard similarity (0.25)
  - Severity accuracy (0.15)
  - Explanation quality / key concepts (0.10)
  - Over-moderation penalty (-0.10 for removing/escalating safe content)
  - Author history awareness bonus (+0.05 for considering repeat offenders)
  - False negative penalty (-0.10 for approving clearly violating content)
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


def _grade_action(action: ContentModAction, truth: dict, post: dict = None) -> tuple[float, str]:
    """Grade a moderation action against the ground truth.

    Returns (reward, feedback_string). Reward in [0.0, 1.0].
    Scoring breakdown:
      - Correct verdict:              0.35
      - Correct rules:                0.25  (partial: Jaccard similarity)
      - Correct severity:             0.15  (partial: 1 - distance/4)
      - Explanation quality:          0.10  (mentions key concepts)
      - Over-moderation penalty:     -0.10  (removing/escalating safe content)
      - False negative penalty:      -0.10  (approving violating content)
      - Author history bonus:        +0.05  (stricter on repeat offenders)
    """
    feedback_parts = []
    total = 0.0

    v_agent = action.verdict.strip().lower()
    v_truth = truth["verdict"].strip().lower()
    rules_truth = set(r.strip().upper() for r in truth["violated_rules"])

    # --- Verdict (0.35) ---
    if v_agent == v_truth:
        total += 0.35
        feedback_parts.append("Verdict: correct")
    else:
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

    # --- Violated rules (0.25) ---
    rules_agent = set(r.strip().upper() for r in action.violated_rules)

    if not rules_truth and not rules_agent:
        total += 0.25
        feedback_parts.append("Rules: correct (none violated)")
    elif rules_truth or rules_agent:
        union = rules_truth | rules_agent
        intersection = rules_truth & rules_agent
        jaccard = len(intersection) / len(union) if union else 0.0
        rule_score = 0.25 * jaccard
        total += rule_score
        feedback_parts.append(
            f"Rules: {intersection} correct out of expected {rules_truth} (+{rule_score:.2f})"
        )

    # --- Severity (0.15) ---
    sev_order = ["none", "low", "medium", "high", "critical"]
    s_agent = action.severity.strip().lower()
    s_truth = truth["severity"].strip().lower()

    if s_agent in sev_order and s_truth in sev_order:
        dist = abs(sev_order.index(s_agent) - sev_order.index(s_truth))
        sev_score = 0.15 * max(0.0, 1.0 - dist / 4.0)
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

    # --- Over-moderation penalty (-0.10) ---
    # Penalize removing or escalating content that is actually safe
    if v_truth == "approve" and v_agent in ("remove", "escalate"):
        total -= 0.10
        feedback_parts.append("Over-moderation penalty: -0.10 (safe content flagged)")
    elif v_truth == "approve" and v_agent == "warn":
        total -= 0.05
        feedback_parts.append("Over-moderation penalty: -0.05 (safe content warned)")

    # --- False negative penalty (-0.10) ---
    # Penalize approving content that should have been removed or escalated
    if v_truth in ("remove", "escalate") and v_agent == "approve":
        total -= 0.10
        feedback_parts.append("False negative penalty: -0.10 (violation approved)")

    # --- Author history bonus (+0.05) ---
    # Reward stricter action on repeat offenders, leniency on first-timers
    if post is not None:
        prior_violations = post.get("author_prior_violations", 0)
        if prior_violations >= 2 and rules_truth:
            # Repeat offender with actual violation — reward strict action
            if v_agent in ("remove", "escalate"):
                total += 0.05
                feedback_parts.append("Author history bonus: +0.05 (strict on repeat offender)")
            else:
                feedback_parts.append("Author history: repeat offender (2+ violations) — consider stricter action")
        elif prior_violations == 0 and v_truth == "approve" and v_agent == "approve":
            # Clean author, safe content — reward correct approval
            total += 0.05
            feedback_parts.append("Author history bonus: +0.05 (correctly approved clean author)")

    # Clamp to [0, 1]
    total = round(min(max(total, 0.0), 1.0), 4)

    return total, " | ".join(feedback_parts)


class ContentModEnvironment(Environment):
    """
    Content Moderation Environment.

    Each episode presents a queue of user-generated posts. The agent reviews
    one post per step and submits a moderation decision. Reward is computed
    per-post via a multi-factor grader with over-moderation penalties and
    author history bonuses.

    Tasks:
        easy_moderation   — obvious violations & safe content (5 posts, multilingual)
        medium_moderation — context-dependent & borderline (7 posts, multilingual)
        hard_moderation   — adversarial, obfuscated, nuanced (8 posts, multilingual)
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task_id = os.getenv("CONTENT_MOD_TASK", "easy_moderation")
        self._posts = []
        self._current_idx = 0
        self._feedback = ""

    def reset(self, task_id: str = None, **kwargs) -> ContentModObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        if task_id:
            self._task_id = task_id
        task = TASKS.get(self._task_id, TASKS["easy_moderation"])
        self._posts = list(task["posts"])
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

        # Grade current post (pass post data for author history scoring)
        post = self._posts[self._current_idx]
        reward, feedback = _grade_action(action, post["truth"], post)

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
