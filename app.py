"""
app.py

Streamlit UI for the Resume Interview Agent.

Flow (tracked in st.session_state.stage):
  upload  -> profile -> interview -> report

Run with:
    streamlit run app.py
"""

import streamlit as st
from dotenv import load_dotenv

from resume_parser import extract_text, ResumeParseError
import interview_agent as agent

load_dotenv()  # reads ANTHROPIC_API_KEY from a local .env file if present

st.set_page_config(page_title="Resume Interview Agent", page_icon="🗂️", layout="centered")

NUM_QUESTIONS = 8


# ---------------------------------------------------------------------------
# Session state setup
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "stage": "upload",       # upload | profile | interview | report
        "resume_text": "",
        "profile": None,
        "questions": [],
        "current_index": 0,
        "qa_results": [],
        "report": None,
        "answer_submitted": False,
        "last_verdict": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_all():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()


init_state()

st.title("🗂️ Resume Interview Agent")
st.caption("Upload a resume, get tailored interview questions, and grade answers for accuracy.")


# ---------------------------------------------------------------------------
# STAGE 1: Upload resume
# ---------------------------------------------------------------------------
if st.session_state.stage == "upload":
    st.subheader("Step 1 — Upload the resume")

    uploaded_file = st.file_uploader("Resume file (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"])
    pasted_text = st.text_area("...or paste resume text directly", height=180)

    if st.button("Read the file →", type="primary"):
        try:
            if uploaded_file is not None:
                with st.spinner("Extracting text from the document..."):
                    text = extract_text(uploaded_file)
            elif pasted_text.strip():
                text = pasted_text.strip()
            else:
                st.error("Please upload a file or paste resume text first.")
                st.stop()

            with st.spinner("Reading the resume for skills and roles..."):
                profile = agent.extract_profile(text)

            st.session_state.resume_text = text
            st.session_state.profile = profile
            st.session_state.stage = "profile"
            st.rerun()

        except ResumeParseError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Something went wrong: {e}")


# ---------------------------------------------------------------------------
# STAGE 2: Show extracted profile, generate questions
# ---------------------------------------------------------------------------
elif st.session_state.stage == "profile":
    profile = st.session_state.profile
    st.subheader("Step 2 — Candidate profile")

    st.markdown(f"### {profile.get('name', 'Candidate')}")
    st.caption(profile.get("headline", ""))

    st.markdown("**Roles identified**")
    st.write(", ".join(profile.get("roles", [])) or "—")

    st.markdown("**Key skills**")
    st.write(", ".join(profile.get("skills", [])) or "—")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Draft interview questions →", type="primary"):
            with st.spinner("Drafting questions from the resume..."):
                try:
                    questions = agent.generate_questions(
                        profile, st.session_state.resume_text, NUM_QUESTIONS
                    )
                    st.session_state.questions = questions
                    st.session_state.current_index = 0
                    st.session_state.qa_results = []
                    st.session_state.stage = "interview"
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't generate questions: {e}")
    with col2:
        if st.button("← Start over"):
            reset_all()
            st.rerun()


# ---------------------------------------------------------------------------
# STAGE 3: Ask questions one at a time, judge each answer
# ---------------------------------------------------------------------------
elif st.session_state.stage == "interview":
    questions = st.session_state.questions
    idx = st.session_state.current_index
    total = len(questions)

    st.subheader("Step 3 — Interview")
    st.progress(idx / total)
    st.caption(f"Question {idx + 1} of {total}")

    q = questions[idx]
    st.markdown(f"**[{q['skill_area']} · {q['difficulty']}]**")
    st.markdown(f"### {q['question']}")

    answer = st.text_area("Candidate's answer", key=f"answer_{idx}", height=150)

    if not st.session_state.answer_submitted:
        if st.button("Submit answer →", type="primary"):
            if len(answer.strip()) < 2:
                st.warning("Enter the candidate's answer before submitting.")
            else:
                with st.spinner("Checking the answer against the resume..."):
                    try:
                        result = agent.judge_answer(st.session_state.profile, q, answer.strip())
                        result.update(
                            {
                                "question": q["question"],
                                "skill_area": q["skill_area"],
                                "difficulty": q["difficulty"],
                                "answer": answer.strip(),
                            }
                        )
                        st.session_state.qa_results.append(result)
                        st.session_state.last_verdict = result
                        st.session_state.answer_submitted = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Couldn't grade that answer: {e}")
    else:
        result = st.session_state.last_verdict
        verdict = result["verdict"]
        icon = {"correct": "✅", "partial": "🟡", "incorrect": "🔴"}.get(verdict, "•")
        st.markdown(f"### {icon} {verdict.title()} — {result['score']}/10")
        st.write(result["feedback"])

        label = "Next question →" if idx + 1 < total else "See final report →"
        if st.button(label, type="primary"):
            st.session_state.current_index += 1
            st.session_state.answer_submitted = False
            st.session_state.last_verdict = None
            if st.session_state.current_index >= total:
                st.session_state.stage = "report"
            st.rerun()


# ---------------------------------------------------------------------------
# STAGE 4: Final report
# ---------------------------------------------------------------------------
elif st.session_state.stage == "report":
    st.subheader("Step 4 — Final report")

    if st.session_state.report is None:
        with st.spinner("Writing up the assessment..."):
            try:
                st.session_state.report = agent.generate_report(
                    st.session_state.profile, st.session_state.qa_results
                )
            except Exception as e:
                st.error(f"Couldn't generate the report: {e}")
                st.stop()

    report = st.session_state.report
    profile = st.session_state.profile

    rec_labels = {
        "strong_yes": ("🟢 Strong yes", "success"),
        "yes": ("🟢 Yes", "success"),
        "maybe": ("🟡 Maybe — needs follow-up", "warning"),
        "no": ("🔴 No", "error"),
    }
    label, kind = rec_labels.get(report["recommendation"], ("Maybe", "warning"))

    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric("Overall score", f"{report['avg_score']}/10")
    with c2:
        getattr(st, kind)(label)

    st.markdown("**Strengths**")
    for s in report.get("strengths", []):
        st.markdown(f"- {s}")

    st.markdown("**Gaps / follow-ups**")
    for g in report.get("gaps", []):
        st.markdown(f"- {g}")

    st.markdown("**Assessment**")
    st.write(report.get("assessment", ""))

    st.divider()
    st.markdown("### Full transcript")
    for i, r in enumerate(st.session_state.qa_results, start=1):
        with st.expander(f"Q{i}. {r['question']}  —  {r['verdict']} ({r['score']}/10)"):
            st.write(f"**Answer:** {r['answer']}")
            st.write(f"**Feedback:** {r['feedback']}")

    # ---- Downloadable report ----
    lines = [
        "RESUME INTERVIEW REPORT",
        "=" * 50,
        f"Candidate: {profile.get('name')}",
        f"Headline: {profile.get('headline')}",
        f"Roles: {', '.join(profile.get('roles', []))}",
        f"Key skills: {', '.join(profile.get('skills', []))}",
        "",
        f"OVERALL SCORE: {report['avg_score']}/10",
        f"RECOMMENDATION: {report['recommendation']}",
        "",
        "STRENGTHS",
        *[f"  - {s}" for s in report.get("strengths", [])],
        "",
        "GAPS / FOLLOW-UPS",
        *[f"  - {g}" for g in report.get("gaps", [])],
        "",
        "ASSESSMENT",
        report.get("assessment", ""),
        "",
        "=" * 50,
        "FULL TRANSCRIPT",
        "=" * 50,
    ]
    for i, r in enumerate(st.session_state.qa_results, start=1):
        lines += [
            "",
            f"Q{i} [{r['skill_area']} / {r['difficulty']}]: {r['question']}",
            f"Answer: {r['answer']}",
            f"Verdict: {r['verdict'].upper()}  |  Score: {r['score']}/10",
            f"Feedback: {r['feedback']}",
        ]

    st.download_button(
        "Download full report (.txt)",
        data="\n".join(lines),
        file_name=f"interview-report-{profile.get('name', 'candidate').replace(' ', '_')}.txt",
        mime="text/plain",
        type="primary",
    )

    if st.button("Interview another candidate"):
        reset_all()
        st.rerun()
