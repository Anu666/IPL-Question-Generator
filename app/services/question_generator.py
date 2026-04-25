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
{direction_block}
You are an IPL expert. You know the current squads, season form, playing
conditions, and head-to-head records for {team1} and {team2} in IPL 2026.
Use that knowledge. The data above may be sparse — fill every gap with your
own expertise.

Generate prediction questions fans answer BEFORE the match.
These are NOT trivia. No correct answer exists yet — fans predict what
WILL happen; answers are revealed post-match.

=== DEFAULT QUESTION MIX (ignored if ADMIN DIRECTION overrides it) ===

Focus primarily on TEAM and MATCH-LEVEL predictions.
Limit player-specific questions to a maximum of 4.
Default count: 15 to 18 questions.

Preferred question types:
  - "Will {team1} score 180+ in their innings?"
  - "Will the match go to a Super Over?"
  - "Which team will take more wickets in the powerplay?"
  - "Will there be 15+ sixes in the match?"
  - "Will {team2} lose more than 3 wickets in the powerplay?"
  - "Will the winning team win by more than 20 runs?"
  - "Who will win the toss — {team1} or {team2}?"
  - "Will there be a 100+ run partnership in the match?"
  - "Will {team1} restrict {team2} under 160?"

Player-specific questions (maximum 4, only for marquee players):
  - "Will [Star Batsman] score 50+?"
  - "Will [Key Bowler] take 2+ wickets?"

Every question must be a concrete, measurable prediction.

=== FORMAT ===

Return ONLY a valid JSON array:

[
  {{
    "id": 1,
    "questionText": "Will {team1} score 180+ in their innings?",
    "options": [
      {{"id": 1, "optionText": "Yes, 180+"}},
      {{"id": 2, "optionText": "No, under 180"}}
    ],
    "credits": 15
  }}
]

Credits (based on how unlikely the event is):
  10 = near-certain (toss winner, does match complete full 20 overs)
  15 = common (team scores 160+, 8+ sixes in the match)
  20 = moderate (team scores 185+, 50+ partnership in powerplay)
  25 = unlikely (team scores 200+, 3 wickets in first 2 overs)
  30 = rare (super over, hat-trick, last-ball finish)

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


def generate_questions(match_context: dict, direction: str | None = None) -> list[MCQQuestion]:
    """
    Call Gemini with the match context and return parsed MCQ questions.
    Raises RuntimeError if Gemini fails or returns no usable questions.
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    match = match_context.get("match", {})

    direction_block = ""
    if direction and direction.strip():
        direction_block = (
            f"\n"
            f"╔══════════════════════════════════════════════════════╗\n"
            f"║              !! MANDATORY ADMIN OVERRIDE !!          ║\n"
            f"╚══════════════════════════════════════════════════════╝\n"
            f"\n"
            f"The following instruction from the admin MUST be followed EXACTLY\n"
            f"and takes ABSOLUTE PRIORITY over every other instruction in this\n"
            f"prompt, including the default question count, topic mix, and\n"
            f"player-question limits.\n"
            f"\n"
            f"ADMIN INSTRUCTION:\n"
            f"  {direction.strip()}\n"
            f"\n"
            f"Rules for complying with the admin instruction:\n"
            f"  - If a SPECIFIC NUMBER of questions is mentioned, generate EXACTLY\n"
            f"    that number — not one more, not one less.\n"
            f"  - If a TOPIC or THEME is specified (e.g. 'batting', 'powerplay',\n"
            f"    'bowling', 'boundaries'), ALL questions must be about that topic.\n"
            f"    Do not generate questions outside the specified topic.\n"
            f"  - If a PLAYER is mentioned, generate questions specifically about\n"
            f"    that player and ignore the usual player-question limit.\n"
            f"  - If a FORMAT restriction is given (e.g. 'Yes/No only', '4 options'),\n"
            f"    apply it to every question.\n"
            f"  - If the instruction contradicts the default question mix below,\n"
            f"    the admin instruction WINS. Ignore the default mix entirely.\n"
            f"  - Do NOT add extra questions beyond what is requested, and do NOT\n"
            f"    silently substitute a different topic just because it seems\n"
            f"    'more interesting'.\n"
            f"\n"
        )

    prompt = _PROMPT_TEMPLATE.format(
        team1=match.get("team1", "Team 1"),
        team2=match.get("team2", "Team 2"),
        date=match.get("date", ""),
        context_json=json.dumps(match_context, indent=2),
        direction_block=direction_block,
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
