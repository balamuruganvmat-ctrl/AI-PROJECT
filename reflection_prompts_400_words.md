# 400-Word Reflection

**CIT AI-Native Engineering Programme · Semester 1 · Assessment 5**
**Student Reflection: Placement Eligibility Checker**

Building the Placement Eligibility Checker offered profound insights into real-world AI-native software architecture, particularly where probabilistic models interface with deterministic business logic.

The most challenging engineering hurdle was configuring environment dependencies and diagnosing runtime API failures across SDK versions. When the program initially flagged every job as `needs_review`, it was easy to suspect flawed regex checks. Digging through log traces revealed that the live model endpoint (`gemini-2.0-flash-lite`) had been deprecated by the provider for new API keys, causing `call_llm()` to raise an exception caught by our fallback handler. Diagnosing the issue by isolating the API call in an independent script, updating the model target to `gemini-3.5-flash-lite`, and verifying package paths in PowerShell restored clean end-to-end execution.

The moment that best illustrated why AI output cannot be trusted blindly occurred when testing percentage cut-offs and prompt injections. When given Kovai Motors’ requirement of *"70 percent in all semesters"*, generative models often attempt to "help" by converting 70% to a 7.0 CGPA. Our system prompt explicitly forbade this, and our Python `check_facts()` function served as an unyielding second line of defense: checking whether the extracted number physically existed in the post text as a standalone figure rather than a percentage. When the fact check stripped the hallucinated CGPA, the post automatically fell back to `needs_review`. The machine was prevented from making an unauthorized policy decision.

Keeping student records strictly within Python—never passing them to the LLM—is the core design pillar of this system. PII and student records must remain confidential. Sending candidate lists to cloud APIs creates major privacy liabilities, multiplies token consumption, and introduces non-deterministic filtering errors. Passing only the job post to the LLM while evaluating candidate records in Python guarantees both absolute privacy and mathematical accuracy.

Given two more weeks, I would expand the tool with a lightweight local web dashboard where the placement officer can view `review.csv`, click a job post to inspect the LLM’s reasoning, and assign manual overrides or verified percentage-to-CGPA conversion formulas.

Three key learnings I take into the showcase presentation are:
1. **Defense in depth:** An LLM prompt is never enough; deterministic Python validators and fact-checkers are essential.
2. **Graceful degradation:** Building structured fallbacks prevents application crashes when external APIs fail.
3. **The Human Checkpoint:** In AI-assisted governance, automation should generate verified drafts, leaving high-stakes decisions to human officers.
