"""
Task data: content policy, posts, and ground-truth labels for grading.
"""

CONTENT_POLICY = """
CONTENT MODERATION POLICY v2.1

RULES:
R1 - Hate Speech: Content that attacks, demeans, or incites violence against individuals
     or groups based on race, ethnicity, religion, gender, sexual orientation, disability,
     or national origin. Severity: HIGH to CRITICAL.

R2 - Harassment: Targeted abuse, threats, intimidation, or sustained unwanted contact
     directed at a specific individual. Severity: MEDIUM to HIGH.

R3 - Spam / Scam: Unsolicited commercial content, phishing links, fake giveaways,
     cryptocurrency scams, or deceptive promotions. Severity: LOW to MEDIUM.

R4 - Misinformation: Demonstrably false claims about health, safety, elections, or
     emergencies that could cause real-world harm. Severity: MEDIUM to HIGH.

R5 - Violence / Graphic Content: Glorification of violence, graphic depictions of injury,
     or content that encourages self-harm. Severity: HIGH to CRITICAL.

R6 - Adult / Sexual Content: Sexually explicit material or content inappropriate for
     general audiences. Severity: MEDIUM to HIGH.

R7 - Privacy Violation: Sharing personal information (addresses, phone numbers, SSNs,
     private photos) without consent. Severity: HIGH.

ACTIONS:
- approve: Content does not violate any rules.
- warn: Minor or first-time violation; notify the user.
- remove: Clear violation; take down the content.
- escalate: Ambiguous, severe, or multi-rule violation needing human review.

GUIDELINES:
- When in doubt between warn and remove, consider author history.
- Authors with 2+ prior violations should receive stricter action.
- Satire and criticism of public figures is generally allowed unless it crosses into R1 or R2.
- Report severity as the highest applicable level across all violated rules.
""".strip()


# Each post: id, content, author info, ground truth
# Ground truth: verdict, violated_rules, severity, key_concepts (for explanation scoring)

EASY_POSTS = [
    {
        "id": "easy-1",
        "content": "🎉 CONGRATULATIONS! You've been selected to win a FREE iPhone 15! Click here ➡️ bit.ly/fr33phone to claim NOW! Only 3 left! Act fast! 💰💰💰",
        "author_name": "PrizeBot9000",
        "author_account_age_days": 1,
        "author_prior_violations": 5,
        "truth": {
            "verdict": "remove",
            "violated_rules": ["R3"],
            "severity": "medium",
            "key_concepts": ["scam", "phishing", "fake giveaway", "deceptive"],
        },
    },
    {
        "id": "easy-2",
        "content": "People of [ethnic group] are subhuman vermin and should be exterminated. They are ruining this country and we need to take action NOW.",
        "author_name": "TruthSpeaker88",
        "author_account_age_days": 14,
        "author_prior_violations": 3,
        "truth": {
            "verdict": "remove",
            "violated_rules": ["R1", "R5"],
            "severity": "critical",
            "key_concepts": ["hate speech", "dehumanization", "incitement", "violence"],
        },
    },
    {
        "id": "easy-3",
        "content": "Just finished a 10k run in the park! Beautiful weather today. Anyone else enjoy running in the autumn? 🍂🏃",
        "author_name": "FitnessFan22",
        "author_account_age_days": 730,
        "author_prior_violations": 0,
        "truth": {
            "verdict": "approve",
            "violated_rules": [],
            "severity": "none",
            "key_concepts": ["benign", "no violation", "personal update"],
        },
    },
]

MEDIUM_POSTS = [
    {
        "id": "med-1",
        "content": "My neighbor Karen is the WORST. She called the cops on my kid's birthday party. Her address is 742 Evergreen Terrace if anyone wants to let her know what they think 😤",
        "author_name": "FrustratedDad",
        "author_account_age_days": 365,
        "author_prior_violations": 0,
        "truth": {
            "verdict": "remove",
            "violated_rules": ["R7", "R2"],
            "severity": "high",
            "key_concepts": ["doxxing", "address", "privacy", "harassment", "targeted"],
        },
    },
    {
        "id": "med-2",
        "content": "Studies show that vaccine X has a 0.001% rate of side effects. But Big Pharma doesn't want you to know that natural immunity is 100% effective and vaccines actually LOWER your immunity. Do your own research! #truth",
        "author_name": "NaturalHealth101",
        "author_account_age_days": 200,
        "author_prior_violations": 1,
        "truth": {
            "verdict": "remove",
            "violated_rules": ["R4"],
            "severity": "high",
            "key_concepts": ["misinformation", "health", "false claim", "anti-vaccine"],
        },
    },
    {
        "id": "med-3",
        "content": "lol politicians are all the same, bunch of useless clowns. Can't believe we pay taxes for this circus 🤡🤡🤡",
        "author_name": "AngryVoter",
        "author_account_age_days": 900,
        "author_prior_violations": 0,
        "truth": {
            "verdict": "approve",
            "violated_rules": [],
            "severity": "none",
            "key_concepts": ["opinion", "political criticism", "protected speech", "no violation"],
        },
    },
    {
        "id": "med-4",
        "content": "Hey everyone! I'm a financial advisor and I've found an AMAZING crypto opportunity. Just send 1 ETH to this wallet and get 10 ETH back. My clients have made millions! DM for the wallet address. Not financial advice 😉",
        "author_name": "CryptoKing",
        "author_account_age_days": 7,
        "author_prior_violations": 0,
        "truth": {
            "verdict": "remove",
            "violated_rules": ["R3"],
            "severity": "medium",
            "key_concepts": ["crypto scam", "fraud", "ponzi", "deceptive"],
        },
    },
]

HARD_POSTS = [
    {
        "id": "hard-1",
        "content": "Those p30pl3 from that c0untry are all thi3ves and cr1minals. They need to go B4CK where they came from. 'Diversity' is just c0de for replacing US. Wake up sheeple!! 🐑",
        "author_name": "PatriotEagle1776",
        "author_account_age_days": 60,
        "author_prior_violations": 2,
        "truth": {
            "verdict": "remove",
            "violated_rules": ["R1"],
            "severity": "high",
            "key_concepts": ["obfuscated", "hate speech", "leetspeak", "xenophobia", "replacement theory"],
        },
    },
    {
        "id": "hard-2",
        "content": "I'm really worried about my friend Sarah. She's been looking so thin lately, practically wasting away. Here are some tips that helped me lose 30 pounds in 2 weeks: skip breakfast and lunch, only drink water with lemon and cayenne, and exercise for 3 hours daily. She'll thank me later! ❤️",
        "author_name": "CaringFriend",
        "author_account_age_days": 450,
        "author_prior_violations": 0,
        "truth": {
            "verdict": "remove",
            "violated_rules": ["R5", "R4"],
            "severity": "high",
            "key_concepts": ["eating disorder", "dangerous diet", "self-harm", "harmful health advice", "disguised as concern"],
        },
    },
    {
        "id": "hard-3",
        "content": "BREAKING: The city water supply has been contaminated with lead. Officials are covering it up! I have insider information — do NOT drink tap water. Buy bottled water NOW before it's too late. Share this before they delete it!! [link to water filter affiliate store]",
        "author_name": "WhistleBlower_X",
        "author_account_age_days": 3,
        "author_prior_violations": 0,
        "truth": {
            "verdict": "escalate",
            "violated_rules": ["R4", "R3"],
            "severity": "high",
            "key_concepts": ["misinformation", "panic", "affiliate spam", "false emergency", "mixed motives"],
        },
    },
    {
        "id": "hard-4",
        "content": "A modest proposal: perhaps we should simply eat the poor. It would solve homelessness AND the food crisis. Two birds, one stone! Jonathan Swift had the right idea. 📚✨",
        "author_name": "LiteraryNerd",
        "author_account_age_days": 1200,
        "author_prior_violations": 0,
        "truth": {
            "verdict": "approve",
            "violated_rules": [],
            "severity": "none",
            "key_concepts": ["satire", "literary reference", "Jonathan Swift", "protected speech", "not literal"],
        },
    },
    {
        "id": "hard-5",
        "content": "Just heard that [public figure] was seen at [restaurant]. Posting the exact location and table number so fans can go say hi! They were with someone who is definitely NOT their spouse if you know what I mean 👀📸 [attached: blurry photo of two people dining]",
        "author_name": "CelebWatcher",
        "author_account_age_days": 180,
        "author_prior_violations": 1,
        "truth": {
            "verdict": "remove",
            "violated_rules": ["R7", "R2"],
            "severity": "high",
            "key_concepts": ["privacy", "location sharing", "stalking", "harassment", "paparazzi", "implied affair"],
        },
    },
]

TASKS = {
    "easy_moderation": {
        "description": "Obvious policy violations and clearly safe content",
        "difficulty": "easy",
        "posts": EASY_POSTS,
    },
    "medium_moderation": {
        "description": "Context-dependent and borderline content requiring careful judgement",
        "difficulty": "medium",
        "posts": MEDIUM_POSTS,
    },
    "hard_moderation": {
        "description": "Adversarial, obfuscated, and nuanced content that challenges even expert moderators",
        "difficulty": "hard",
        "posts": HARD_POSTS,
    },
}
