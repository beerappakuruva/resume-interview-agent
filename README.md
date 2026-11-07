# Resume Interview Agent

A Streamlit app that reads a candidate's resume, generates tailored interview
questions from it, and scores the candidate's answers for accuracy — powered
by the Claude API.

## How it's organized

| File | Purpose |
|---|---|
| `resume_parser.py` | Extracts plain text from PDF / DOCX / TXT resumes |
| `interview_agent.py` | All Claude API calls: profile extraction, question generation, answer grading, final report |
| `app.py` | The Streamlit UI that ties everything together |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for your API key — copy to `.env` |

---

## Step-by-step setup (VSCode + git)

### 1. Install prerequisites
- [Python 3.10+](https://www.python.org/downloads/)
- [VSCode](https://code.visualstudio.com/)
- VSCode's **Python extension** (Extensions panel → search "Python" → install, by Microsoft)
- [Git](https://git-scm.com/downloads)
- An Anthropic API key from [console.anthropic.com](https://console.anthropic.com/settings/keys)

### 2. Get the project into a folder and open it in VSCode
```bash
mkdir resume-interview-agent
cd resume-interview-agent
# copy all the files (app.py, interview_agent.py, resume_parser.py,
# requirements.txt, .env.example, .gitignore, README.md) into this folder
code .
```
`code .` opens the current folder in VSCode. If that command isn't recognized,
open VSCode manually and use **File → Open Folder**.

### 3. Create a virtual environment
In VSCode's integrated terminal (**Terminal → New Terminal**):
```bash
python3 -m venv .venv

# activate it:
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows
```
VSCode will usually prompt "Select interpreter" — choose the one inside
`.venv`. This keeps this project's packages separate from the rest of your
system.

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Add your API key
```bash
cp .env.example .env        # macOS/Linux
copy .env.example .env      # Windows
```
Open `.env` in VSCode and paste in your real key:
```
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
```
`.env` is already listed in `.gitignore`, so it will never be committed.

### 6. Run the app
```bash
streamlit run app.py
```
This opens the app in your browser at `http://localhost:8501`. Upload a
resume (or paste text), generate questions, answer them as if you were the
candidate, and review the final scored report.

### 7. Initialize git and make your first commit
```bash
git init
git add .
git commit -m "Initial commit: resume interview agent"
```

### 8. Push to GitHub
Create an empty repo on GitHub (no README/license, so it doesn't conflict),
then:
```bash
git remote add origin https://github.com/<your-username>/resume-interview-agent.git
git branch -M main
git push -u origin main
```
From then on, after making changes:
```bash
git add .
git commit -m "Describe what changed"
git push
```

---

## How the pieces fit together

1. **`resume_parser.extract_text()`** turns the uploaded file into plain text.
2. **`interview_agent.extract_profile()`** sends that text to Claude and gets
   back structured JSON: name, headline, roles, key skills.
3. **`interview_agent.generate_questions()`** sends the profile + resume text
   back to Claude, asking for 8 tailored questions (mix of warm-up/core/deep,
   grounded in the specific skills and projects on that resume).
4. As each question is answered in the Streamlit UI,
   **`interview_agent.judge_answer()`** scores it 0–10 with a verdict
   (correct/partial/incorrect) and short feedback.
5. Once all questions are answered, **`interview_agent.generate_report()`**
   summarizes strengths, gaps, and a hire recommendation, and the UI offers a
   downloadable `.txt` report.

## Extending it
- **Change question count**: edit `NUM_QUESTIONS` in `app.py`.
- **Swap models**: edit `MODEL` in `interview_agent.py`.
- **Batch mode**: loop `st.file_uploader(..., accept_multiple_files=True)` in
  `app.py` and run the same pipeline per resume.
- **Persist results**: write `qa_results` / `report` to a database or CSV
  before calling `reset_all()`, if you want a history across candidates.

## Troubleshooting
- **`ANTHROPIC_API_KEY is not set`** — make sure `.env` exists (not just
  `.env.example`) and contains your real key, then restart `streamlit run`.
- **PDF text comes out empty** — the PDF is likely a scanned image rather
  than real text. Try exporting the resume as a text-based PDF, or paste the
  text directly.
- **Streamlit doesn't reload after edits** — save the file, then click
  "Rerun" in the top-right of the browser tab, or re-run `streamlit run app.py`.
