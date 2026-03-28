---
name: skill-search
description: Search the local skill library (6000+ skills) to find relevant existing skills before writing new code. Use this whenever a task might already be solved by an existing skill.
---

# Local Skill Library Search

Search 6000+ skills in `/Users/administruter/Desktop/AGI_PROJECT/skills/` using the PCM skill router.

## When to Use
- Before implementing any new functionality
- When looking for reusable code patterns
- When the user asks about capabilities

## How to Search

```python
import sys
sys.path.insert(0, '/Users/administruter/Desktop/AGI_PROJECT/scripts')
from pcm_skill_router import route_skills

results = route_skills("your search query", top_k=5)
for r in results:
    print(f"{r['name']} (score={r['score']}): {r['description'][:100]}")
```

## CLI Search
```bash
python3 -c "
import sys; sys.path.insert(0, '/Users/administruter/Desktop/AGI_PROJECT/scripts')
from pcm_skill_router import route_skills
for r in route_skills('搜索词', top_k=5):
    print(f\"{r['name']} ({r['score']}): {r['description'][:80]}\")
"
```

## Skill Categories
- **openclaw**: 5982 community skills (code/deploy/search/security/data)
- **gstack**: 29 engineering workflow skills (review/qa/deploy/security)
- **custom**: User-generated skills from growth engine

## After Finding Skills
1. Read the skill's full content if score > 5.0
2. Adapt or compose multiple skills for complex tasks
3. If no good match, proceed with new implementation
