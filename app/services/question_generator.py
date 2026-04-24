# Question generator service
# Sends the match context to Gemini and parses the MCQ response.
# Uses gemini-1.5-flash for fast, cost-efficient generation.

import json
import re

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.question import MCQOption, MCQQuestion

_PROMPT_TEMPLATE = """
You are designing a prediction game for an upcoming IPL 2026 match:

  {team1} vs {team2} on {date}

Below is pre-match data from live sources. Study it carefully — use win/loss
records, recent form, and match statuses to inform your questions.

--- MATCH DATA ---
{context_json}
--- END DATA ---

CRITICAL INSTRUCTION: You are an IPL expert. You know the current squads,
key players, batting order, strike bowlers, and season form for {team1}
and {team2} in IPL 2026. Use that knowledge. The data above may be sparse —
fill every gap with your own expertise.

Generate 15 to 18 prediction questions fans answer BEFORE the match.
These are NOT trivia. No correct answer exists yet — fans predict what
WILL happen; answers are revealed post-match.

=== QUALITY BAR ===

A mix of question types is fine, but at least 10 of the 15-18 questions MUST
be specific — naming real players or referencing concrete thresholds.

Generic questions (allowed, max 5):
  - "Who will win the match?"
  - "Which team will win the toss?"
  - "Will there be a super over?"

Specific questions (required — at least 10):
  - "Will Rohit Sharma hit a six in the powerplay overs?"
  - "Will Jasprit Bumrah concede fewer than 30 runs in his 4 overs?"
  - "Will {team1} score 180+ in their innings?"
  - "Who will be {team2}'s highest scorer — [Player A], [Player B], or [Player C]?"
  - "Will MS Dhoni bat at position 5 or lower?"

Every specific question MUST either:
  a) Name a real player from the {team1} or {team2} IPL 2026 squad, OR
  b) Reference a concrete, measurable threshold (e.g. 180+, 2+ wickets, 4+ sixes)

=== FORMAT ===

Return ONLY a valid JSON array:

[
  {{
    "id": 1,
    "questionText": "Will Rohit Sharma score 50+ runs today?",
    "options": [
      {{"id": 1, "optionText": "Yes, he will score 50+"}},
      {{"id": 2, "optionText": "No, he won't reach 50"}}
    ],
    "credits": 20
  }}
]

Credits (based on likelihood):
  10 = near-certain (who wins toss, does match go full 20 overs)
  15 = common event (team scores 170+, top-order bat scores 30+)
  20 = moderate (player scores 50+, bowler takes 2 wkts)
  25 = unlikely (century, 3 wickets in a spell, 8+ sixes by one batter)
  30 = rare (hat-trick, super over, bowled for golden duck by star batter)

Rules:
  - 2 to 4 options per question (Yes/No is fine for binary events)
  - NO is_correct field on any option
  - Return ONLY the JSON array, no markdown, no explanation
""".strip()


def _extract_json_array(text: str) -> list:
    """Extract JSON array from Gemini response, handling any extra text."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find the first [ ... ] block in the response
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return []


def _parse_questions(raw: list) -> list[MCQQuestion]:
    """Convert raw dicts from Gemini into validated MCQQuestion models."""
    questions = []
    for idx, item in enumerate(raw, start=1):
        try:
            raw_options = item.get("options", [])
            options = [
                MCQOption(
                    id=opt.get("id", i),
                    optionText=opt.get("optionText", opt.get("text", "")),
                )
                for i, opt in enumerate(raw_options, start=1)
            ]
            if len(options) < 2:
                continue
            questions.append(MCQQuestion(
                id=item.get("id", idx),
                questionText=item.get("questionText", item.get("question", "")),
                options=options,
                credits=item.get("credits", 10),
            ))
        except Exception:
            continue
    return questions


def generate_questions(match_context: dict) -> list[MCQQuestion]:
    """
    Call Gemini with the match context and return parsed MCQ questions.
    Raises RuntimeError if Gemini fails or returns no usable questions.
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    match = match_context.get("match", {})
    prompt = _PROMPT_TEMPLATE.format(
        team1=match.get("team1", "Team 1"),
        team2=match.get("team2", "Team 2"),
        date=match.get("date", ""),
        context_json=json.dumps(match_context, indent=2),
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7),
    )

    raw = _extract_json_array(response.text)
    questions = _parse_questions(raw)

    if not questions:
        raise RuntimeError("Gemini returned no valid questions. Check the API key and model availability.")

    return questions
