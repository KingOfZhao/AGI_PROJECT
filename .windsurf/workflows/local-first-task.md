---
description: Execute a task using Local-First strategy - search skills, delegate to local models, verify results
---

# Local-First Task Execution

## Step 1: Search existing skills
Search the local skill library (6000+ skills) for relevant existing solutions:
```python
python3 -c "
import sys; sys.path.insert(0, '/Users/administruter/Desktop/AGI_PROJECT/scripts')
from pcm_skill_router import route_skills
for r in route_skills('TASK_DESCRIPTION', top_k=5):
    print(f\"{r['name']} ({r['score']}): {r['description'][:100]}\")
"
```
If score > 5.0, read and reuse that skill. If not, proceed to Step 2.

## Step 2: Delegate to local 7-step chain
Run the task through the local AI chain processor:
```python
python3 /Users/administruter/Desktop/AGI_PROJECT/.windsurf/skills/local-chain/invoke_chain.py "TASK_DESCRIPTION"
```
Review the chain output for quality.

## Step 3: Verify results
Check if the local chain output is satisfactory:
- Is the answer accurate and complete?
- Is the code syntactically correct and runnable?
- Are there any hallucination warnings?
- Are risk scan results acceptable?

If YES → Use the result, skip to Step 5.
If NO → Proceed to Step 4 (Claude verification).

## Step 4: Claude verification (only if Step 3 failed)
Explain WHY local models failed and what specific improvement is needed.
After Claude produces the fix, create a skill to capture the improvement:
- Save to `skills/skill_{topic}_{timestamp}.py`
- Include docstring, type hints, error handling

## Step 5: Post-processing
- Extract knowledge nodes (Step A)
- Generate reusable skill file (Step B)
- Record to CRM system (Step C)
