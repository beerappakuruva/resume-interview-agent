"""
interview_agent.py

All calls to the Claude API live here. Each function sends a focused prompt
and asks Claude to reply with ONLY a JSON object/array, which we parse and
return as plain Python data (dicts/lists) so app.py never has to think
about prompts at all.
"""

import json
import os
from anthropic import Anthropic

MODEL = "claude-sonnet-5"

_client = None


def get_client() -> Anthropic:
    """Lazily create the Anthropic client using ANTHROPIC_API_KEY from the environment."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file "
                "(see .env.example)."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def _call_json(system: str, user: str, max_tokens: int = 2000):
    """Send one message to Claude and parse the reply as JSON."""
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return _parse_json(text)


def _parse_json(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.split("\n", 1)[-1] if cleaned.lower().startswith("json") else cleaned
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back to grabbing the first {...} or [...] block in the reply
        for open_ch, close_ch in [("{", "}"), ("[", "]")]:
            start = cleaned.find(open_ch)
            end = cleaned.rfind(close_ch)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"Could not parse Claude's response as JSON:\n{text}")


# ---------------------------------------------------------------------------
# 1. Extract a structured candidate profile from raw resume text
# ---------------------------------------------------------------------------
def extract_profile(resume_text: str) -> dict:
    system = (
        "You extract structured candidate profiles from resumes. "
        "Respond ONLY with a single valid JSON object, no markdown fences, "
        "no preamble, no commentary."
    )
    user = f"""Resume text:
\"\"\"
{resume_text[:12000]}
\"\"\"

Return a JSON object with exactly these fields:
{{
  "name": "candidate's name, or 'Candidate' if not found",
  "headline": "one-line summary, e.g. 'Senior Data Engineer, 6 yrs, AWS/Spark/Kafka'",
  "roles": ["1-4 job titles/roles evident from the resume"],
  "skills": ["6-12 specific key skills/technologies/tools, most important first"]
}}"""
    return _call_json(system, user)


# ---------------------------------------------------------------------------
# 2. Generate interview questions tailored to that profile
# ---------------------------------------------------------------------------
def generate_questions(profile: dict, resume_text: str, num_questions: int = 8) -> list:
    system = (
        "You are an experienced technical interviewer. You write sharp, specific "
        "interview questions grounded in a candidate's actual resume content. "
        "Respond ONLY with a valid JSON array, no markdown fences, no commentary."
    )
    user = f"""Candidate profile:
Name: {profile.get('name')}
Headline: {profile.get('headline')}
Roles: {', '.join(profile.get('roles', []))}
Skills: {', '.join(profile.get('skills', []))}

Full resume text:
\"\"\"
{resume_text[:8000]}
\"\"\"

Write {num_questions} interview questions that probe whether the claims on this
resume reflect real, working knowledge. Mix question types:
- Some ask the candidate to explain a specific project or claim from their resume in more depth
- Some are scenario/problem-solving questions tied to their stated key skills
- Some test conceptual depth on their top 2-3 technologies (things a real
  practitioner would know but someone padding a resume would not)
- Vary difficulty: a couple of warm-up questions, several core questions,
  one or two probing/deep questions

Return a JSON array of exactly {num_questions} objects, each with:
{{"id": 1, "skill_area": "short tag e.g. 'Apache Spark'", "question": "...", "difficulty": "warm-up" | "core" | "deep"}}"""
    return _call_json(system, user)


# ---------------------------------------------------------------------------
# 3. Judge one answer for accuracy
# ---------------------------------------------------------------------------
def judge_answer(profile: dict, question: dict, answer: str) -> dict:
    system = (
        "You are a rigorous, fair technical interviewer grading a candidate's "
        "answer for accuracy. Respond ONLY with a valid JSON object, no markdown "
        "fences, no commentary."
    )
    user = f"""Candidate's resume context:
Roles: {', '.join(profile.get('roles', []))}
Skills: {', '.join(profile.get('skills', []))}

Interview question (skill area: {question.get('skill_area')}, difficulty: {question.get('difficulty')}):
"{question.get('question')}"

Candidate's answer:
\"\"\"
{answer}
\"\"\"

Judge the technical accuracy and depth of this answer. Be fair but rigorous:
reward correct, specific, well-reasoned answers; penalize vague, evasive, or
factually wrong answers; give partial credit for answers on the right track
but incomplete or slightly imprecise.

Return a JSON object:
{{
  "score": integer 0-10,
  "verdict": "correct" | "partial" | "incorrect",
  "feedback": "2-3 sentences explaining the score"
}}"""
    return _call_json(system, user)


# ---------------------------------------------------------------------------
# 4. Generate the final hiring-panel-style report
# ---------------------------------------------------------------------------
def generate_report(profile: dict, qa_results: list) -> dict:
    avg_score = sum(r["score"] for r in qa_results) / len(qa_results)

    transcript_lines = []
    for i, r in enumerate(qa_results, start=1):
        transcript_lines.append(
            f"{i}. [{r['skill_area']}, {r['verdict']}, {r['score']}/10] "
            f"Q: {r['question']}\n   Feedback: {r['feedback']}"
        )
    transcript = "\n".join(transcript_lines)

    system = (
        "You are a hiring panel lead writing a concise, honest candidate "
        "assessment based on a completed technical interview. Respond ONLY "
        "with a valid JSON object, no markdown fences, no commentary."
    )
    user = f"""Candidate: {profile.get('name')} — {profile.get('headline')}
Resume skills: {', '.join(profile.get('skills', []))}

Interview results:
{transcript}

Average score: {avg_score:.1f}/10

Return a JSON object:
{{
  "strengths": ["2-4 short bullet points on genuine strengths shown"],
  "gaps": ["2-4 short bullet points on gaps or suggested follow-up questions"],
  "assessment": "3-4 sentence overall written assessment",
  "recommendation": "strong_yes" | "yes" | "maybe" | "no"
}}"""
    report = _call_json(system, user)
    report["avg_score"] = round(avg_score, 1)
    return report
