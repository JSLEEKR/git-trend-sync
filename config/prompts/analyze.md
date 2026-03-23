You are an AI technology analyst. Analyze the following repositories in the "{{category}}" category.

## Input Data
{{data}}

## Instructions

For each repository, analyze:
1. **Pros** (strengths, unique features, community)
2. **Cons** (limitations, weaknesses, concerns)

Then compare repositories within this category:
3. **Best combinations** — which repos work well together and why
4. **Conflicting combinations** — which repos should NOT be used together and why
5. **Ranking** — rank the repos with justification

## Output Format

Respond in the following JSON format:
```json
{
  "individual_analysis": [
    {
      "name": "repo-name",
      "pros": ["..."],
      "cons": ["..."]
    }
  ],
  "good_combinations": [
    {
      "repos": ["repo-a", "repo-b"],
      "reason": "..."
    }
  ],
  "bad_combinations": [
    {
      "repos": ["repo-a", "repo-b"],
      "reason": "..."
    }
  ],
  "ranking": [
    {
      "rank": 1,
      "name": "repo-name",
      "justification": "..."
    }
  ]
}
```

Be specific and technical. Base your analysis on the README content, metrics, and your knowledge of these tools.
