"""
Placement Eligibility Checker (console tool).

Flow: load CSVs -> LLM reads ONE post at a time -> Python validates the reply ->
Python fact-checks it against the post -> Python decides job status ->
Python matches students -> four output files. Every list is a DRAFT.

Student records NEVER go to the LLM. Only the post text does.
The API key is read from an environment variable and is never written in code.
"""
import csv
import json
import os
import re
from pathlib import Path

MODEL = os.environ.get("PLACEMENT_MODEL", "claude-haiku-5-5")  # change if your Week 12 API differs
PROMPT_FILE = "system_prompt.txt"
OUT_DIR = "output"

FIELDS = ["branches", "min_cgpa", "max_backlogs", "batch", "summary"]   # the only five fields we keep
ALLOWED_BRANCHES = ["CSE", "IT", "AIDS", "ECE", "EEE", "MECH", "CIVIL"]
FALLBACK = {"branches": [], "min_cgpa": None, "max_backlogs": None, "batch": None, "summary": ""}

# For each branch: (case-sensitive acronym pattern, case-insensitive full-name pattern).
# Acronyms are case-sensitive so the word "it" in a sentence is not mistaken for IT.
BRANCH_NAMES = {
    "CSE":   (r"\bCSE\b", r"computer science"),
    "IT":    (r"\bIT\b", r"information technology"),
    "AIDS":  (r"\bAI\s*(?:&|and)\s*DS\b|\bAIDS\b", r"artificial intelligence"),
    "ECE":   (r"\bECE\b", r"electronics\s*(?:and|&)\s*communication"),
    "EEE":   (r"\bEEE\b", r"electrical\s*(?:and|&)\s*electronics"),
    "MECH":  (r"\bMECH\b", r"mechanical"),
    "CIVIL": (r"\bCIVIL\b", r"civil"),
}


# ---------------------------------------------------------------- loading
def load_jobs(path):
    """Read jobs.csv into a list of dictionaries (id, company, post)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_students(path):
    """Read students.csv into a list of dictionaries.
    cgpa is converted with float() so 10.0 is not compared as text.
    A bad row is skipped (try/except) and its roll is returned in the second list."""
    students, skipped = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                students.append({
                    "roll": row["roll"].strip(),
                    "name": row["name"].strip(),
                    "branch": row["branch"].strip().upper(),
                    "cgpa": float(row["cgpa"]),
                    "backlogs": int(row["backlogs"]),
                    "batch": int(row["batch"]),
                })
            except (ValueError, KeyError, AttributeError):
                skipped.append(row.get("roll", "?"))
    return students, skipped


# ---------------------------------------------------------------- LLM
def call_llm(post):
    # pyrefly: ignore[missing-import]
    from google import genai
    # pyrefly: ignore[missing-import]
    from google.genai import types
    system_prompt = Path(PROMPT_FILE).read_text(encoding="utf-8")
    client = genai.Client()          # reads GEMINI_API_KEY from the environment
    reply = client.models.generate_content(
        model=MODEL,
        contents=f"<post>\n{post}\n</post>",
        config=types.GenerateContentConfig(system_instruction=system_prompt,
                                           max_output_tokens=300),
    )
    return reply.text


def is_number(x):
    """True for int or float, but not True/False (bool is a subclass of int in Python)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def is_valid(data):
    """Check one LLM reply against the JSON rules. True only if every rule holds."""
    if not isinstance(data, dict) or any(k not in data for k in FIELDS):
        return False
    b = data["branches"]
    if not isinstance(b, list) or not all(isinstance(x, str) for x in b):
        return False
    if b != ["ALL"] and not all(x in ALLOWED_BRANCHES for x in b):
        return False
    c = data["min_cgpa"]
    if c is not None and not (is_number(c) and 0 <= c <= 10):
        return False
    m = data["max_backlogs"]
    if m is not None and not (isinstance(m, int) and not isinstance(m, bool) and m >= 0):
        return False
    y = data["batch"]
    if y is not None and not (isinstance(y, int) and not isinstance(y, bool) and 2000 <= y <= 2100):
        return False
    s = data["summary"]
    return isinstance(s, str) and len(s.split()) <= 12


def read_criteria(post):
    """Ask the LLM about one post. Check the reply; retry once; fall back if both fail.
    Returns (criteria with ONLY the five fields, note). note is "" when the reply was good."""
    for attempt in range(2):                       # first try + one retry
        try:
            text = call_llm(post).strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)   # remove ``` fences if present
            data = json.loads(text)
            if is_valid(data):
                return {                           # copy the five fields only; extras are dropped
                    "branches": list(data["branches"]),
                    "min_cgpa": None if data["min_cgpa"] is None else float(data["min_cgpa"]),
                    "max_backlogs": data["max_backlogs"],
                    "batch": data["batch"],
                    "summary": data["summary"].strip(),
                }, ""
        except Exception:                          # network error, bad JSON, anything: try again
            pass
    return dict(FALLBACK), "LLM reply unusable after retry"


# ---------------------------------------------------------------- fact check
def branch_named(code, post):
    """True if the post names this branch (by acronym or full name)."""
    acronym, words = BRANCH_NAMES[code]
    return bool(re.search(acronym, post) or re.search(words, post, re.IGNORECASE))


def number_written(value, post):
    """True if the number is written in the post as a standalone number and is NOT a
    percentage (e.g. 7.5 is found in 'CGPA 7.5.' but 70 percent never counts as a CGPA)."""
    for form in {f"{value:g}", f"{float(value):.1f}"}:
        for m in re.finditer(rf"(?<![\d.]){re.escape(form)}(?!\d|\.\d)", post):
            tail = post[m.end(): m.end() + 12]
            if not re.match(r"\s*(?:%|per\s?cent)", tail, re.IGNORECASE):
                return True
    return False


def check_facts(c, post):
    """Compare the LLM's criteria with the post text.
    Anything the post does not support is removed. Returns (new criteria, list of reasons)."""
    c = dict(c, branches=list(c["branches"]))
    reasons = []
    if c["branches"] == ["ALL"]:
        if not re.search(r"\b(?:any|all)\s+branch(?:es)?\b", post, re.IGNORECASE):
            reasons.append("ALL removed: post does not say 'any branch' or 'all branches'")
            c["branches"] = []
    else:
        kept = [b for b in c["branches"] if branch_named(b, post)]
        for b in c["branches"]:
            if b not in kept:
                reasons.append(f"branch {b} removed: not named in post")
        c["branches"] = kept
    if c["min_cgpa"] is not None and not number_written(c["min_cgpa"], post):
        reasons.append(f"CGPA {c['min_cgpa']:g} removed: not written in post (percentages are never converted)")
        c["min_cgpa"] = None
    if c["batch"] is not None and not number_written(c["batch"], post):
        reasons.append(f"batch {c['batch']} removed: not written in post")
        c["batch"] = None
    if c["max_backlogs"] is not None and not re.search(r"backlog|arrear", post, re.IGNORECASE):
        reasons.append("backlog limit removed: post does not mention backlogs or arrears")
        c["max_backlogs"] = None
    return c, reasons


def job_status(c):
    """needs_review if there are no branches or no CGPA after the fact check, else matched."""
    if not c["branches"] or c["min_cgpa"] is None:
        return "needs_review"
    return "matched"


def review_reasons(c, notes):
    """Why a post needs the placement officer's eyes (used in review.csv)."""
    reasons = list(notes)
    if not c["branches"]:
        reasons.append("no branches")
    if c["min_cgpa"] is None:
        reasons.append("no CGPA cut-off written in post")
    return "; ".join(reasons)


# ---------------------------------------------------------------- matching
def is_eligible(student, c):
    """True if one student meets every criterion that is stated."""
    if c["branches"] != ["ALL"] and student["branch"] not in c["branches"]:
        return False
    if c["min_cgpa"] is not None and student["cgpa"] < c["min_cgpa"]:
        return False
    if c["max_backlogs"] is not None and student["backlogs"] > c["max_backlogs"]:
        return False
    if c["batch"] is not None and student["batch"] != c["batch"]:
        return False
    return True


def process_job(job, students):
    """Run one post through the whole pipeline. Returns one result dictionary."""
    raw, note = read_criteria(job["post"])
    c, reasons = check_facts(raw, job["post"])
    status = job_status(c)
    # A needs_review post gets no student list: the officer must read the post first.
    eligible = [s for s in students if is_eligible(s, c)] if status == "matched" else []
    return {"job": job, "criteria": c, "status": status, "eligible": eligible,
            "reason": review_reasons(c, ([note] if note else []) + reasons) if status == "needs_review" else "",
            "notes": reasons}


# ---------------------------------------------------------------- output
def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_reports(results, students, out_dir=OUT_DIR):
    """Write job_summary.csv, eligible.csv, review.csv and summary.txt."""
    Path(out_dir).mkdir(exist_ok=True)
    summary_rows, eligible_rows, review_rows = [], [], []
    for r in results:
        j, c = r["job"], r["criteria"]
        summary_rows.append([j["id"], j["company"], ";".join(c["branches"]),
                             "" if c["min_cgpa"] is None else c["min_cgpa"],
                             "" if c["max_backlogs"] is None else c["max_backlogs"],
                             "" if c["batch"] is None else c["batch"],
                             c["summary"], r["status"], len(r["eligible"])])
        for s in r["eligible"]:
            eligible_rows.append([j["id"], j["company"], s["roll"], s["name"], s["branch"],
                                  s["cgpa"], s["backlogs"], s["batch"]])
        if r["status"] == "needs_review":
            review_rows.append([j["id"], j["company"], j["post"], r["reason"]])

    write_csv(f"{out_dir}/job_summary.csv",
              ["id", "company", "branches", "min_cgpa", "max_backlogs", "batch", "summary", "status", "eligible_count"],
              summary_rows)
    write_csv(f"{out_dir}/eligible.csv",
              ["job_id", "company", "roll", "name", "branch", "cgpa", "backlogs", "batch"], eligible_rows)
    write_csv(f"{out_dir}/review.csv", ["id", "company", "post", "reason"], review_rows)

    placed = {s["roll"] for r in results for s in r["eligible"]}
    with open(f"{out_dir}/summary.txt", "w", encoding="utf-8") as f:
        f.write("DRAFT - the placement officer must check every list before it is shared.\n\n")
        f.write("Eligible students per job\n")
        for r in results:
            f.write(f"  {r['job']['id']}  {r['job']['company']:<26}{r['status']:<13}{len(r['eligible'])}\n")
        f.write("\nStudents eligible for no job yet\n")
        for s in students:
            if s["roll"] not in placed:
                f.write(f"  {s['roll']}  {s['name']}\n")


def main(jobs_file="jobs.csv", students_file="students.csv"):
    jobs = load_jobs(jobs_file)
    students, skipped = load_students(students_file)
    if skipped:
        print("Skipped bad student rows:", ", ".join(skipped))
    results = []
    for job in jobs:
        print(f"Processing {job['id']} ({job['company']})...")
        results.append(process_job(job, students))
    write_reports(results, students)
    print("\nDRAFT lists written to the output/ folder. The placement officer must check them before sharing.")
    for r in results:
        print(f"  {r['job']['id']}  {r['status']:<13}{len(r['eligible'])} eligible")


if __name__ == "__main__":
    main()
