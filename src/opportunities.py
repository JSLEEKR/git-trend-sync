"""
opportunities.py — cross gap data with trending signals to produce opportunity reports.

Loads trending.json and gaps.json for a given date, computes opportunity scores,
detects cross-category patterns, classifies opportunities, and generates
a markdown report.
"""

import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def normalize_scores(values: list[float]) -> list[float]:
    """Min-max normalize values to 0-10 scale.

    - Empty list -> []
    - Single value -> [10.0]
    - All same -> [5.0, 5.0, ...]
    """
    if not values:
        return []
    if len(values) == 1:
        return [10.0]
    lo = min(values)
    hi = max(values)
    if lo == hi:
        return [5.0] * len(values)
    return [round((v - lo) / (hi - lo) * 10, 4) for v in values]


def compute_opportunity_score(
    gap_demand: float,
    trend_score: float,
    category_avg_surge: float,
) -> float:
    """Compute opportunity score as average of three 0-10 inputs."""
    return round((gap_demand + trend_score + category_avg_surge) / 3, 1)


# ---------------------------------------------------------------------------
# Cross-category pattern detection
# ---------------------------------------------------------------------------

def detect_cross_category_patterns(gaps: dict) -> list[dict]:
    """Find keywords appearing in 3+ categories.

    Parameters
    ----------
    gaps : dict
        Mapping of category name -> list of gap dicts.
        Each gap dict should have a "keywords" list.

    Returns
    -------
    list[dict]
        [{"keyword": str, "categories": list[str], "total_count": int}, ...]
        sorted by total_count descending.
    """
    # keyword -> {category -> count}
    keyword_cats: dict[str, dict[str, int]] = {}

    for category, cat_data in gaps.items():
        if isinstance(cat_data, dict):
            gap_list = cat_data.get("top_gaps", [])
        elif isinstance(cat_data, list):
            gap_list = cat_data
        else:
            continue
        for gap in gap_list:
            for kw in gap.get("keywords", []):
                kw_lower = kw.lower()
                if kw_lower not in keyword_cats:
                    keyword_cats[kw_lower] = {}
                keyword_cats[kw_lower][category] = (
                    keyword_cats[kw_lower].get(category, 0) + 1
                )

    results = []
    for kw, cat_counts in keyword_cats.items():
        if len(cat_counts) >= 3:
            results.append({
                "keyword": kw,
                "categories": sorted(cat_counts.keys()),
                "total_count": sum(cat_counts.values()),
            })

    results.sort(key=lambda x: x["total_count"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_opportunity(opp: dict) -> str:
    """Classify an opportunity dict.

    Rules (evaluated in order):
    - "hot" if trend_score >= 6 AND demand_normalized >= 6
    - "rising" if source repo signal_type == "newcomer"
    - "high_demand" if demand_normalized >= 8
    - "standard" otherwise
    """
    trend = opp.get("trend_score", 0)
    demand = opp.get("demand_normalized", 0)
    signal = opp.get("signal_type", "")

    if trend >= 6 and demand >= 6:
        return "hot"
    if signal == "newcomer":
        return "rising"
    if demand >= 8:
        return "high_demand"
    return "standard"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_opportunity_report(
    date: str,
    opportunities: list[dict],
    cross_patterns: list[dict],
    portfolio: list[str],
) -> str:
    """Generate a markdown opportunity report.

    Sections:
    - Hot Opportunities
    - Rising Opportunities
    - Cross-Category Patterns
    - High-Demand Gaps
    - Already Covered
    """
    lines: list[str] = [
        f"# Opportunity Report — {date}",
        "",
    ]

    portfolio_lower = {p.lower() for p in portfolio}

    hot = [o for o in opportunities if o.get("opportunity_type") == "hot"]
    rising = [o for o in opportunities if o.get("opportunity_type") == "rising"]
    high_demand = [o for o in opportunities if o.get("opportunity_type") == "high_demand"]
    covered = [o for o in opportunities if o.get("already_covered")]

    # --- Hot Opportunities ---
    lines.append("## Hot Opportunities (trending + tool demand)")
    lines.append("")
    if hot:
        lines.append("| Category | Gap | Score | Trend | Demand |")
        lines.append("|----------|-----|-------|-------|--------|")
        for o in hot:
            lines.append(
                f"| {o.get('category', '')} "
                f"| {o.get('gap_title', '')} "
                f"| {o.get('opportunity_score', '')} "
                f"| {o.get('trend_score', '')} "
                f"| {o.get('demand_normalized', '')} |"
            )
    else:
        lines.append("No hot opportunities found.")
    lines.append("")

    # --- Rising Opportunities ---
    lines.append("## Rising Opportunities (new ecosystems)")
    lines.append("")
    if rising:
        lines.append("| Category | Gap | Score | Source |")
        lines.append("|----------|-----|-------|--------|")
        for o in rising:
            lines.append(
                f"| {o.get('category', '')} "
                f"| {o.get('gap_title', '')} "
                f"| {o.get('opportunity_score', '')} "
                f"| {o.get('source_repo', '')} |"
            )
    else:
        lines.append("No rising opportunities found.")
    lines.append("")

    # --- Cross-Category Patterns ---
    lines.append("## Cross-Category Patterns")
    lines.append("")
    if cross_patterns:
        lines.append("| Keyword | Categories | Count |")
        lines.append("|---------|------------|-------|")
        for p in cross_patterns:
            cats = ", ".join(p.get("categories", []))
            lines.append(
                f"| {p.get('keyword', '')} "
                f"| {cats} "
                f"| {p.get('total_count', '')} |"
            )
    else:
        lines.append("No cross-category patterns found.")
    lines.append("")

    # --- High-Demand Gaps ---
    lines.append("## High-Demand Gaps (by reactions)")
    lines.append("")
    if high_demand:
        lines.append("| Category | Gap | Demand | Score |")
        lines.append("|----------|-----|--------|-------|")
        for o in high_demand:
            lines.append(
                f"| {o.get('category', '')} "
                f"| {o.get('gap_title', '')} "
                f"| {o.get('demand_normalized', '')} "
                f"| {o.get('opportunity_score', '')} |"
            )
    else:
        lines.append("No high-demand gaps found.")
    lines.append("")

    # --- Already Covered ---
    lines.append("## Already Covered (portfolio overlap)")
    lines.append("")
    if covered:
        lines.append("| Category | Gap | Covered By |")
        lines.append("|----------|-----|------------|")
        for o in covered:
            matched = [
                kw for kw in o.get("keywords", [])
                if kw.lower() in portfolio_lower
            ]
            lines.append(
                f"| {o.get('category', '')} "
                f"| {o.get('gap_title', '')} "
                f"| {', '.join(matched)} |"
            )
    else:
        lines.append("No portfolio overlaps found.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_opportunities(
    date: str = None,
    portfolio: list[str] = None,
) -> dict:
    """Run the full opportunities pipeline.

    1. Load trending.json and gaps.json for date
    2. Compute category_avg_surge from trending data
    3. Compute opportunity scores per gap
    4. Detect cross-category patterns
    5. Classify & filter
    6. Save report + JSON
    7. Return opportunities dict
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    if portfolio is None:
        portfolio = []

    portfolio_lower = {p.lower() for p in portfolio}
    data_dir = BASE_DIR / "data" / date

    # 1. Load data
    with open(data_dir / "trending.json", "r", encoding="utf-8") as f:
        trending = json.load(f)
    with open(data_dir / "gaps.json", "r", encoding="utf-8") as f:
        gaps = json.load(f)

    # 2. Compute category_avg_surge from trending
    category_surges: dict[str, float] = {}
    categories = trending.get("categories", {})
    for cat, repos in categories.items():
        surges = [
            r.get("surge_score", 0) or 0
            for r in repos
        ]
        if surges:
            category_surges[cat] = sum(surges) / len(surges)
        else:
            category_surges[cat] = 0.0

    # Normalize surges to 0-10
    surge_vals = list(category_surges.values())
    surge_norm = normalize_scores(surge_vals)
    surge_keys = list(category_surges.keys())
    cat_surge_normalized = {
        surge_keys[i]: surge_norm[i] for i in range(len(surge_keys))
    }

    # 3. Build opportunities from gaps
    all_opps: list[dict] = []
    gap_categories = gaps.get("categories", gaps)
    # If gaps is {"categories": {...}} or just {cat: [gaps]}
    if isinstance(gap_categories, dict) and "categories" not in gap_categories:
        gap_categories = gap_categories
    elif isinstance(gap_categories, dict) and "categories" in gap_categories:
        gap_categories = gap_categories["categories"]

    # Collect all demand scores for normalization
    all_demands: list[float] = []
    gap_entries: list[tuple[str, dict]] = []
    for cat, cat_data in gap_categories.items():
        # Support both {"top_gaps": [...]} and plain list formats
        if isinstance(cat_data, dict):
            gap_list = cat_data.get("top_gaps", [])
        elif isinstance(cat_data, list):
            gap_list = cat_data
        else:
            continue
        for gap in gap_list:
            demand = float(gap.get("demand_score", 0))
            all_demands.append(demand)
            gap_entries.append((cat, gap))

    demand_normalized = normalize_scores(all_demands)

    for i, (cat, gap) in enumerate(gap_entries):
        demand_norm = demand_normalized[i] if i < len(demand_normalized) else 0
        cat_surge = cat_surge_normalized.get(cat, 0)

        # Find best matching trending repo for trend_score
        trend_score = 0.0
        signal_type = ""
        source_repo = ""
        cat_repos = categories.get(cat, [])
        if cat_repos:
            best = max(cat_repos, key=lambda r: r.get("trend_score", 0) or 0)
            trend_score = float(best.get("trend_score", 0) or 0)
            signal_type = best.get("signal_type", "")
            source_repo = best.get("full_name", "")

        # Normalize trend_score (already 0-10 in trending data typically)
        opp_score = compute_opportunity_score(demand_norm, trend_score, cat_surge)

        keywords = gap.get("keywords", [])
        already_covered = any(kw.lower() in portfolio_lower for kw in keywords)

        opp = {
            "category": cat,
            "gap_title": gap.get("title", gap.get("gap_title", "")),
            "gap_type": gap.get("type", gap.get("gap_type", "")),
            "source_repo": source_repo,
            "issue_url": gap.get("issue_url", ""),
            "demand_score": float(gap.get("demand_score", 0)),
            "demand_normalized": round(demand_norm, 1),
            "trend_score": round(trend_score, 1),
            "category_avg_surge": round(cat_surge, 1),
            "opportunity_score": opp_score,
            "opportunity_type": "",  # filled below
            "keywords": keywords,
            "already_covered": already_covered,
            "signal_type": signal_type,
        }
        opp["opportunity_type"] = classify_opportunity(opp)
        all_opps.append(opp)

    # Sort by opportunity_score descending
    all_opps.sort(key=lambda x: x["opportunity_score"], reverse=True)

    # 4. Cross-category patterns
    cross_patterns = detect_cross_category_patterns(gap_categories)

    # 5. Generate report
    report_md = generate_opportunity_report(date, all_opps, cross_patterns, portfolio)

    # 6. Save outputs
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{date}-opportunities.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    output = {
        "date": date,
        "opportunities": all_opps,
        "cross_category_patterns": cross_patterns,
    }

    out_path = data_dir / "opportunities.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    portfolio_arg = sys.argv[2:] if len(sys.argv) > 2 else None
    result = run_opportunities(date_arg, portfolio_arg)
    print(f"Done: {len(result['opportunities'])} opportunities found")
