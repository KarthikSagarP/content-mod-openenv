"""
Inference Script — Content Moderation Environment
==================================================
Runs a baseline LLM agent against all 3 content moderation tasks.

MANDATORY env vars:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    IMAGE_NAME     The name of the local image (optional, for from_docker_image)
"""

import asyncio
import json
import os
import textwrap
from typing import List, Optional

from openai import OpenAI

from client import ContentModEnv
from models import ContentModAction

IMAGE_NAME = os.getenv("IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
SPACE_URL = os.getenv("SPACE_URL", "https://skibidikarthik-content-moderation-env.hf.space")
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


def build_user_prompt(obs) -> str:
    return textwrap.dedent(f"""
POST TO MODERATE:
Post ID: {obs.post_id}
Content: {obs.post_content}

AUTHOR INFO:
Name: {obs.author_name}
Account age: {obs.author_account_age_days} days
Prior violations: {obs.author_prior_violations}

CONTENT POLICY:
{obs.content_policy}

Posts remaining after this: {obs.posts_remaining}

Previous feedback: {obs.feedback}

Respond with a JSON moderation decision.
""").strip()


def parse_model_response(text: str) -> ContentModAction:
    """Parse the LLM JSON response into a ContentModAction."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
        return ContentModAction(
            verdict=data.get("verdict", "approve"),
            violated_rules=data.get("violated_rules", []),
            severity=data.get("severity", "none"),
            explanation=data.get("explanation", ""),
        )
    except (json.JSONDecodeError, Exception) as e:
        print(f"[DEBUG] Parse error: {e}, raw: {text[:200]}", flush=True)
        return ContentModAction(
            verdict="approve", violated_rules=[], severity="none",
            explanation="Failed to parse model response",
        )


def get_model_decision(client: OpenAI, obs) -> ContentModAction:
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
        return ContentModAction(
            verdict="approve", violated_rules=[], severity="none",
            explanation="Model request failed",
        )


async def run_task(task_name: str, llm_client: OpenAI) -> float:
    """Run a single task and return the normalized score [0, 1]."""
    os.environ["CONTENT_MOD_TASK"] = task_name
    max_posts = TASK_POST_COUNTS.get(task_name, 3)

    # Connect to running HF Space, fall back to Docker if IMAGE_NAME is set
    if IMAGE_NAME:
        env = await ContentModEnv.from_docker_image(IMAGE_NAME)
    else:
        env = ContentModEnv(base_url=SPACE_URL)

    rewards: List[float] = []
    steps_taken = 0

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset()
        obs = result.observation

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            action = get_model_decision(llm_client, obs)
            action_str = f"verdict={action.verdict},rules={action.violated_rules},sev={action.severity}"

            result = await env.step(action)
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done
            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_str, reward=reward, done=done, error=None)

            if done:
                break

        score = sum(rewards) / max_posts if max_posts > 0 else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= 0.3

    except Exception as e:
        print(f"[DEBUG] Task {task_name} error: {e}", flush=True)
        score = 0.0
        success = False
    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main() -> None:
    llm_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    scores = {}
    for task_name in TASK_NAMES:
        score = await run_task(task_name, llm_client)
        scores[task_name] = score

    print("\n=== BASELINE RESULTS ===", flush=True)
    for task, sc in scores.items():
        print(f"  {task}: {sc:.3f}", flush=True)
    avg = sum(scores.values()) / len(scores) if scores else 0.0
    print(f"  AVERAGE: {avg:.3f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
