---
title: Content Moderation Environment
emoji: 🛡️
colorFrom: red
colorTo: blue
sdk: docker
app_port: 8000
tags:
  - openenv
pinned: false
short_description: OpenEnv content moderation environment for AI agents
---

# Content Moderation Environment

An OpenEnv environment where AI agents act as content moderators, reviewing user-generated posts against a detailed content policy and making moderation decisions.

## Motivation

Content moderation is one of the most important and challenging real-world tasks at scale. Platforms process millions of posts daily, and AI-assisted moderation is already deployed in production. This environment lets researchers train and evaluate agents on realistic moderation scenarios — from obvious spam to adversarial, obfuscated hate speech that challenges even expert human moderators.

## How It Works

Each episode presents the agent with a queue of user-generated posts. For each post, the agent sees:
- The post content
- Author metadata (account age, prior violations)
- The full content policy

The agent must submit a moderation decision: verdict, violated rules, severity, and an explanation. The environment grades each decision and returns a reward signal with detailed feedback.

## Action Space

| Field | Type | Description |
|-------|------|-------------|
| `verdict` | string | `approve`, `warn`, `remove`, or `escalate` |
| `violated_rules` | list[str] | Policy rule IDs violated, e.g. `["R1", "R3"]`. Empty if approved. |
| `severity` | string | `none`, `low`, `medium`, `high`, or `critical` |
| `explanation` | string | Brief justification for the decision |

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `post_id` | string | Unique identifier for the current post |
| `post_content` | string | The user-generated content to review |
| `author_name` | string | Display name of the author |
| `author_account_age_days` | int | Account age in days |
| `author_prior_violations` | int | Number of previous policy violations |
| `content_policy` | string | The full content policy document |
| `task_id` | string | Current task identifier |
| `posts_remaining` | int | Posts left in the episode |
| `feedback` | string | Grading feedback from previous decision |

## Reward Function

Each moderation decision is scored on four factors (total 0.0–1.0 per post):

| Component | Weight | Details |
|-----------|--------|---------|
| Correct verdict | 0.40 | Exact match; partial credit for close verdicts |
| Correct rules | 0.30 | Jaccard similarity between predicted and true violated rules |
| Correct severity | 0.20 | Partial credit based on distance in severity scale |
| Explanation quality | 0.10 | Proportion of key concepts mentioned |

Episode score is the mean reward across all posts, normalized to [0, 1].

## Tasks

### 1. `easy_moderation` (Easy — 3 posts)
Obvious violations: clear spam/scam, explicit hate speech, and benign content. A competent agent should score >0.8.

### 2. `medium_moderation` (Medium — 4 posts)
Context-dependent cases: doxxing disguised as venting, health misinformation, protected political speech, and crypto scams. Requires understanding nuance. Expected baseline: 0.5–0.7.

### 3. `hard_moderation` (Hard — 5 posts)
Adversarial content: leetspeak-obfuscated hate speech, harmful advice disguised as concern, mixed misinformation + affiliate spam, literary satire, and celebrity privacy violations. Challenges frontier models. Expected baseline: 0.3–0.5.

## Content Policy

The policy covers 7 rule categories:
- **R1** Hate Speech
- **R2** Harassment
- **R3** Spam / Scam
- **R4** Misinformation
- **R5** Violence / Graphic Content
- **R6** Adult / Sexual Content
- **R7** Privacy Violation

With 4 possible actions: approve, warn, remove, escalate.

## Setup

### Run locally
```bash
pip install openenv-core
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker build -t content-mod-env:latest .
docker run -p 8000:8000 content-mod-env:latest
```

### Run baseline inference
```bash
export HF_TOKEN=your_token_here
export IMAGE_NAME=content-mod-env:latest
python inference.py
```

## Baseline Scores

| Task | Qwen2.5-72B-Instruct |
|------|---------------------|
| easy_moderation | ~0.85 |
| medium_moderation | ~0.60 |
| hard_moderation | ~0.40 |
| **Average** | **~0.62** |

## Validation
```bash
openenv validate
```
