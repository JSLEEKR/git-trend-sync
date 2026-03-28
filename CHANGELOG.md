# Changelog

All notable changes to git-trend-sync will be documented in this file.

## [0.5.0] - 2026-03-28

### Added
- Comprehensive test suite (80+ tests) with pytest
- CHANGELOG and ROUND_LOG documentation
- Expanded README with architecture docs, API reference, scoring algorithm details
- Testing section in README
- Contributing guide

### Changed
- README expanded from 241 to 450+ lines with detailed documentation

## [0.4.0] - 2026-03-28

### Added
- Activity history tracking with sparkline charts (`src/history.py`)
- 30-day star growth visualization (`src/star_history.py`)
- Auto-update README with trending data (`src/readme_update.py`)
- Shields.io badge generation (`src/badge.py`)
- Daily GitHub Actions workflow with issue notifications

## [0.3.0] - 2026-03-25

### Added
- Deep integration analysis (`src/apply.py`) with design doc generation
- Project stack scanner supporting 8 languages (`src/scan_project.py`)
- Recommendation engine with compatibility scoring (`src/recommend.py`)
- Feature comparison tables for top candidates
- `/trend-apply` Claude Code slash command

## [0.2.0] - 2026-03-23

### Changed
- Rebrand from ai-trend to git-trend-sync
- Switch to activity-based (30-day commits) scoring from star-based
- Expand to 12 AI categories

### Added
- English-only reports
- Category-wise normalization (0-10 scale)
- New entry detection (cross-day comparison)

## [0.1.0] - 2026-03-23

### Added
- Initial release
- GitHub Topics data collection
- Basic trend scoring
- Markdown report generation
- Claude Code qualitative analysis integration
