# Placement Eligibility Checker

Console tool for the placement cell. It reads job posts, uses an LLM to pull out each post's eligibility criteria, checks those criteria against the post text in Python, and matches them against the student list. **Every list is a draft. The placement officer checks it before it is shared.**

## Key rules
- **Student records never go to the LLM.** Only one post's text is sent per call.
- The LLM reply is **checked every time** (`is_valid`), **retried once**, and replaced by an empty **fallback** if it still fails. Only five fields are copied from any reply.
- Python **fact-checks** the reply against the post: branches must be named, `ALL` needs "any/all branches", CGPA and batch must be written in the post. A percentage is never converted to a CGPA.
- A post with no branches or no CGPA after the fact check is `needs_review`. Otherwise it is `matched`.
- The API key comes from an environment variable. It is never in the code or the repo.

## Setup
```
pip install anthropic
export ANTHROPIC_API_KEY="your-key"      # Windows PowerShell: $env:ANTHROPIC_API_KEY="your-key"
```
The call is isolated in `call_llm()`. If your Week 12 API is a different provider, replace only that function's body (and the model name).

## Run
```
python placement_checker.py              # reads jobs.csv and students.csv, writes output/
python eval_harness.py                   # 5 test posts + 3 red-team posts, real LLM
python eval_harness.py --mock            # same harness with scripted replies, no key needed
```

## Files
| File | Purpose |
|---|---|
| `placement_checker.py` | the program |
| `system_prompt.txt` | LLM prompt (Authority, Exemplar, Constraint, Rubric, Metadata) |
| `jobs.csv`, `students.csv` | inputs (10 posts, 24 students) |
| `output/job_summary.csv` | each post's criteria, status and eligible count |
| `output/eligible.csv` | one row per eligible student per job |
| `output/review.csv` | posts the officer must read, with the reason |
| `output/summary.txt` | eligible count per job, and students eligible for no job |
| `eval_harness.py`, `eval_results.csv` | tests and results |
| `docs/` | Judgment Framework, cost and latency note |

## Known limits
- The fact check proves a branch is *named* in the post, not that it is the branch *rule*. A post like "IT services company, CSE only" would make IT look named. The officer review is the safety net.
- A post with no batch stated treats all batches as eligible (for example 2026 students are included). This is the spec's "if stated" rule.
- I added one check beyond the spec: a backlog limit is removed if the post never mentions backlogs or arrears.
- Percentage rules are flagged, not applied, because `students.csv` has no percentage column.
