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
short_description: Multilingual OpenEnv content moderation environment for AI agents
---

# Content Moderation Environment

An OpenEnv environment where AI agents act as content moderators, reviewing user-generated posts against a detailed content policy and making moderation decisions. Features **multilingual content** in English, Hindi, Hinglish, and Kannada for realistic Indian platform moderation scenarios.

## Motivation

Content moderation is one of the most important and challenging real-world tasks at scale. Platforms in India process millions of posts daily across multiple languages, and AI-assisted moderation must handle code-switching, regional languages, and culturally-specific context. This environment lets researchers train and evaluate agents on realistic multilingual moderation scenarios — from obvious spam to adversarial, obfuscated hate speech in mixed languages.

## How It Works

Each episode presents the agent with a queue of user-generated posts. For each post, the agent sees:
- The post content (may be in English, Hindi, Hinglish, or Kannada)
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
| `post_content` | string | The user-generated content to review (multilingual) |
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
| Correct verdict | 0.35 | Exact match; partial credit for close verdicts |
| Correct rules | 0.25 | Jaccard similarity between predicted and true violated rules |
| Correct severity | 0.15 | Partial credit based on distance in severity scale |
| Explanation quality | 0.10 | Proportion of key concepts mentioned |
| Over-moderation penalty | -0.10 | Penalizes removing or escalating safe content |
| False negative penalty | -0.10 | Penalizes approving content that violates policy |
| Author history bonus | +0.05 | Rewards considering repeat offenders and clean authors |

Episode score is the mean reward across all posts, normalized to [0, 1].

## Tasks (22 posts total)

### 1. `easy_moderation` (Easy — 5 posts)
Obvious violations: clear spam/scam (English + Hinglish), explicit hate speech, and benign content (English + Kannada). A competent agent should score >0.8.

### 2. `medium_moderation` (Medium — 9 posts)
Context-dependent cases: doxxing, health misinformation (English + Hinglish), protected political speech (English + Kannada), crypto scams, and community-targeted hate speech in Hinglish. Requires understanding nuance across languages. Expected baseline: 0.5–0.7.

### 3. `hard_moderation` (Hard — 8 posts)
Adversarial content: leetspeak-obfuscated hate speech (English + Hinglish), harmful advice disguised as concern, mixed misinformation + affiliate spam (English + Hinglish), literary satire, celebrity privacy violations, positive community content in Kannada (must not be falsely flagged). Challenges frontier models. Expected baseline: 0.3–0.5.

## Languages Covered

- **English** — standard moderation scenarios
- **Hindi** (Devanagari script) — pure Hindi posts
- **Hinglish** (Hindi-English code-switching) — the most common format on Indian social media
- **Kannada** (Kannada script) — regional language content

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
