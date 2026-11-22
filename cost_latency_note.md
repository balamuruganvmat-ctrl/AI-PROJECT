# Cost and Latency Note

## 1. Overview
The Placement Eligibility Checker runs criteria extraction only on incoming job post text. **Student records are never transmitted over the API**, keeping token consumption minimal, predictable, and fully independent of student cohort size.

---

## 2. API Calls Per Day
- The placement cell receives several posts per week. In a typical active cycle, assume **10 posts per day**.
- **Normal Case:** 1 call per post = **10 API calls / day**.
- **Worst Case (Every call fails validation once and is retried):** 2 calls per post = **20 API calls / day**.

---

## 3. Latency Profile
- **Single Request Latency:** 
  - Using `gemini-3.5-flash-lite`, round-trip latency ranges between **0.6 to 1.5 seconds** per post.
- **Batch Processing Time (10 Posts):**
  - Sequential execution: ~**8 to 15 seconds** total runtime.
  - Worst case with 10 retries: ~**20 to 30 seconds**.
- **Local Deterministic Matching:** Python fact-checking, candidate matching, and CSV generation take **< 0.05 seconds** total.

---

## 4. Cost Analysis

### Pricing Rates (Google Gemini 3.5 Flash-Lite / Flash API):
- **Free Tier:** 15 RPM (Requests Per Minute) / 1,500 RPD (Requests Per Day) at **$0.00** (Free).
- **Pay-as-you-go Rates:**
  - Input tokens: **$0.075 per 1,000,000 tokens** ($0.000075 / 1K tokens)
  - Output tokens: **$0.30 per 1,000,000 tokens** ($0.00030 / 1K tokens)

### Token Estimates Per Call:
- **Input Tokens:** 
  - System prompt (`system_prompt.txt`): ~650 tokens
  - Job post text (`<post> ... </post>`): ~50 tokens
  - *Total Input per call:* **~700 tokens**
- **Output Tokens:** 
  - Structured JSON response: **~75 tokens**

### Daily Cost Calculation:
$$\text{Cost} = \text{Calls} \times (\text{Input Tokens} \times \text{Input Price} + \text{Output Tokens} \times \text{Output Price})$$

| Scenario | Daily Calls | Input Tokens | Output Tokens | Estimated Cost (USD) | Estimated Cost (INR) |
|---|---|---|---|---|---|
| **Normal Day (10 posts)** | 10 | 7,000 | 750 | **$0.00075** | ~₹0.06 |
| **Worst-Case Day (20 calls)** | 20 | 14,000 | 1,500 | **$0.00150** | ~₹0.13 |
| **Monthly Operation (~250 posts)**| 250 | 175,000 | 18,750 | **$0.0187** | ~₹1.60 |

### Conclusion
Even on a commercial paid tier, operating the Placement Eligibility Checker costs less than **2 cents per month**. Because student records remain local, financial cost is completely decoupled from student enrollment numbers.
