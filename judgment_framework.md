# Judgment Framework

> The spec says "the three questions" from class. I used the three below. **Replace the column headings with the exact wording from your Week notes if they differ.**

## Wrongly left out vs wrongly included
| | Student wrongly left out | Student wrongly included |
|---|---|---|
| What happens | Misses a chance and never knows | Appears on a list sent to a company they do not qualify for |
| Who is harmed | The student (a lost opportunity) | The company's time, the college's credibility, a wrongly raised hope |
| How visible | Silent: nobody sees a missing name | Visible: an ineligible name can be spotted on the list |
| Design choice | Uncertain posts become `needs_review`, so the officer reads the post instead of the tool silently dropping students | Strict fact checks remove anything the post does not support |

The silent harm is the worse one, which is why the tool flags uncertain posts instead of quietly guessing. Both errors are caught at the same checkpoint: **the placement officer checks every list before it is shared.**

## By part of the tool
| Part | What can go wrong? | How bad, and for whom? | What catches it? |
|---|---|---|---|
| Load CSVs | Bad row, CGPA read as text ("10.0" < "7.5") | Wrong comparisons for many students | `float()` / `int()` conversion, bad rows skipped and reported |
| LLM extraction | Guesses a branch, converts 70 percent to 7.0, follows an instruction hidden in the post | Wrong list for a company, or a student missed | Prompt rules, then Python checks below |
| `is_valid` + retry + fallback | Bad JSON, wrong types, values out of range, API error | Crash or garbage criteria | Reply rejected, one retry, then empty fallback means `needs_review`. The program never crashes |
| `check_facts` | A branch only looks named; a number appears only as a percentage | A wrong branch or cut-off slips in | Must be named or written in the post. Percentages never count as CGPA |
| `job_status` | Partial criteria treated as complete | Students listed against an unknown cut-off | No branches or no CGPA means `needs_review`, with no student list |
| `is_eligible` | Boundary error (CGPA exactly at cut-off), wrong comparison | A student wrongly in or out | Floats, `>=` and `<=`, tested by hand-counted eval cases (7.5 exactly passes) |
| `write_reports` | Files overwritten or unlabelled drafts | A draft shared as final | Every output labelled DRAFT. `review.csv` lists what to read |
| Human checkpoint | Officer skips the review | Wrong list goes to a company | Process rule: no list leaves the college unchecked |
