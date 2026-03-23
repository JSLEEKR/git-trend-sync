Analyze the current project against the latest AI agent trend data and generate actionable design documents for relevant trending tools.

## Steps

1. **Scan this project**: Read README.md, requirements.txt/package.json/pyproject.toml, and directory structure to understand the tech stack, architecture, and purpose.

2. **Load trend data**: Read the latest `data/YYYY-MM-DD/trending.json` from the ai-trend project (located at the path configured in ai-trend.yaml, or default `~/OneDrive/Documents/git-ai-trend/`).

3. **Match and filter**: For each trending repo:
   - Does the tech stack match this project?
   - Does it solve a problem this project actually has?
   - Could it replace or complement a current dependency?
   - Is it relevant to the project's declared interests (if ai-trend.yaml exists)?

4. **Decision gate**:
   - If NO relevant trending repos found: Report "No actionable trends today for this project." with a brief explanation of why nothing matched. Stop here.
   - If relevant repos found: Continue to step 5.

5. **For each relevant trending repo, generate a design document** saved to `docs/trend-apply/YYYY-MM-DD-<repo-name>.md`:

```
# Integration Design: <repo-name> → <project-name>

## Why This Matters
- What the trending repo does
- Why it's trending now (velocity data)
- Why it's relevant to THIS project specifically

## Current State
- Which files/modules in this project are affected
- Current implementation approach
- Current dependencies that overlap

## Proposed Changes
- What to add/replace/modify
- Architecture diagram (text-based)
- New dependencies required

## Migration Path
1. Step-by-step integration guide
2. Code examples (before → after) for key files
3. Configuration changes needed

## Risks & Trade-offs
- Breaking changes
- Performance implications
- Learning curve

## Effort Estimate
- small (< 1 day) / medium (1-3 days) / large (3+ days)
- Breakdown by component

## Verdict
- YES: Adopt now — clear benefit, low risk
- WAIT: Monitor for 1-2 weeks — promising but too early
- NO: Not worth it — explain why
```

6. **Summary**: Print a concise summary of what was found and what design docs were generated.

## Important
- Be specific to THIS project's actual code and dependencies
- Don't force irrelevant recommendations
- Read actual source files before making claims about "affected modules"
- If a trending repo is interesting but the project has no use for it, say so honestly
