"""
Inference Script — Content Moderation Environment
==================================================
Runs a baseline LLM agent against all 3 content moderation tasks.

MANDATORY env vars:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    LOCAL_IMAGE_NAME  Optional, not used in this script.
"""

import json
import os
import textwrap
from typing import List, Optional

import requests
from openai import OpenAI

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
IMAGE_NAME = os.getenv("IMAGE_NAME")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

# Environment server URL — connect to the live HF Space
ENV_URL = os.getenv("ENV_URL", "https://skibidikarthik-content-moderation-env.hf.space")

BENCHMARK = "content_mod"
MAX_STEPS = 10
TEMPERATURE = 0.3
MAX_TOKENS = 500

TASK_NAMES = ["easy_moderation", "medium_moderation", "hard_moderation"]
TASK_POST_COUNTS = {"easy_moderation": 3, "medium_moderation": 4, "hard_moderation": 5}

SYSTEM_PROMPT = textwrap.dedent("""
You are a content moderator AI. You are given a user post and a content policy.
You must decide how to moderate the post.

You MUST respond with a valid JSON object and nothing else. No markdown, no explanation outside the JSON.

The JSON must have these fields:
{
  "verdict": "approve" | "warn" | "remove" | "escalate",
  "violated_rules": ["R1", "R3"],   // list of rule IDs, empty [] if approved
  "severity": "none" | "low" | "medium" | "high" | "critical",
  "explanation": "Brief explanation of your decision"
}

Guidelines:
- Read the content policy carefully.
- Consider the author's account age and prior violations.
- For obvious violations, use "remove". For ambiguous cases, use "escalate".
- Assign severity based on the most severe violated rule.
- If content is safe, verdict="approve", violated_rules=[], severity="none".
""").strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def env_reset(base_url: str) -> dict:
    """Call POST /reset on the environment server."""
    resp = requests.post(f"{base_url}/reset", json={}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_step(base_url: str, action_dict: dict) -> dict:
    """Call POST /step on the environment server."""
    resp = requests.post(f"{base_url}/step", json={"action": action_dict}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_user_prompt(obs: dict) -> str:
    return textwrap.dedent(f"""
POST TO MODERATE:
Post ID: {obs.get('post_id', '')}
Content: {obs.get('post_content', '')}

AUTHOR INFO:
Name: {obs.get('author_name', '')}
Account age: {obs.get('author_account_age_days', 0)} days
Prior violations: {obs.get('author_prior_violations', 0)}

CONTENT POLICY:
{obs.get('content_policy', '')}

Posts remaining after this: {obs.get('posts_remaining', 0)}

Previous feedback: {obs.get('feedback', '')}

Respond with a JSON moderation decision.
""").strip()


def parse_model_response(text: str) -> dict:
    """Parse the LLM JSON response into an action dict."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
        return {
            "verdict": data.get("verdict", "approve"),
            "violated_rules": data.get("violated_rules", []),
            "severity": data.get("severity", "none"),
            "explanation": data.get("explanation", ""),
        }
    except (json.JSONDecodeError, Exception) as e:
        print(f"[DEBUG] Parse error: {e}, raw: {text[:200]}", flush=True)
        return {
            "verdict": "approve",
            "violated_rules": [],
            "severity": "none",
            "explanation": "Failed to parse model response",
        }


def get_model_decision(client: OpenAI, obs: dict) -> dict:
    user_prompt = build_user_prompt(obs)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        return parse_model_response(text)
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return {
            "verdict": "approve",
            "violated_rules": [],
            "severity": "none",
            "explanation": "Model request failed",
        }


def run_task(task_name: str, llm_client: OpenAI, base_url: str) -> float:
    """Run a single task and return the normalized score [0, 1]."""
    max_posts = TASK_POST_COUNTS.get(task_name, 3)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_resp = env_reset(base_url)
        obs = reset_resp.get("observation", {})
        done = reset_resp.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = get_model_decision(llm_client, obs)
            action_str = f"verdict={action['verdict']},rules={action['violated_rules']},sev={action['severity']}"

            step_resp = env_step(base_url, action)
            obs = step_resp.get("observation", {})
            reward = step_resp.get("reward", 0.0) or 0.0
            done = step_resp.get("done", False)

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_str, reward=reward, done=done, error=None)

            if done:
                break

        score = sum(rewards) / max_posts if max_posts > 0 else 0.01
        score = min(max(score, 0.01), 0.99)  # strictly between 0 and 1
        success = score >= 0.3

    except Exception as e:
        print(f"[DEBUG] Task {task_name} error: {e}", flush=True)
        score = 0.01
        success = False
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


def main() -> None:
    llm_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    scores = {}
    for task_name in TASK_NAMES:
        score = run_task(task_name, llm_client, ENV_URL)
        scores[task_name] = score

    print("\n=== BASELINE RESULTS ===", flush=True)
    for task, sc in scores.items():
        print(f"  {task}: {sc:.3f}", flush=True)
    avg = sum(scores.values()) / len(scores) if scores else 0.0
    print(f"  AVERAGE: {avg:.3f}", flush=True)


if __name__ == "__main__":
    main()
