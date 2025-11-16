# Feature 013: Update Presentation Materials - Complete Specification

**Branch**: `013-update-presentations`
**Created**: 2025-11-16
**Status**: Clarified - Ready for Planning
**Repository**: magic-cards-edh-deck

---

## Executive Summary

This feature updates the ../docs presentation materials to:
1. **Clarify terminology**: Distinguish GitHub's Spec-Kit from our custom /speckit.* workflow
2. **Add evidence**: Include Feature 012 (Hellcube Proxy Generator) as a real-world case study
3. **Update classification**: Move our workflow from "Tier 3: Experimental" to "Tier 2: Emerging Standard"
4. **Build toolchain**: Create 3 new Claude skills for presentation work (Marp conversion, Mermaid diagrams, UX validation)

---

## Critical Design Decisions (from Clarification Session)

### 1. Cross-Repo Workflow Strategy
**Question**: How to handle modifications across two separate git repositories (magic-cards-edh-deck vs ../docs)?

**Decision**: Copy ../docs presentation files to `specs/013-update-presentations/` in this repo, modify them here within the feature branch, then provide manual PR instructions for applying changes to ../docs repo.

**Rationale**: Keeps all work in one feature branch with full version control and testing before pushing to ../docs.

---

### 2. Output Format Support
**Question**: What presentation formats are needed?

**Decision**: Markdown + PPT/PDF exports (Option B)

**Deliverables**:
- Primary: Markdown source files (SESSION-1, SESSION-2, WORKSHOP-OVERVIEW)
- Secondary: PPT/PDF exports for offline workshop distribution

**Rationale**: Maintains existing MD infrastructure while adding distribution formats for workshops without internet access.

---

### 3. Visual/Diagram Generation
**Question**: What types of visuals should be generated?

**Decision**: Mermaid diagrams only (flowcharts, sequence diagrams) - Option A

**Scope**:
- Flowcharts: Speckit command workflow (specify → plan → clarify → tasks → implement)
- Sequence diagrams: Feature lifecycle, cross-repo interactions
- Architecture diagrams: Feature 012 MCTS+VLM structure

**Rationale**: Lightweight, Markdown-native, renders in GitHub/exports, no external image dependencies.

---

### 4. UX Validation Approach
**Question**: How to validate understandability and avoid information overload?

**Decision**: Human-in-loop skill prompts for UX feedback (Option C)

**Implementation**:
- Build `validate-ux.md` skill that prompts for feedback during editing
- Check: slide complexity, jargon density, narrative flow, technical depth
- Target audience: Mid-level developers without ML/research background (NFR-002)

**Rationale**: Automated metrics can't assess contextual understanding; human feedback ensures accessible content.

---

### 5. Conversion Tooling
**Question**: Which tools for Markdown→PPT/PDF conversion?

**Decision**: Marp (Markdown Presentation Ecosystem) - Option B

**Capabilities**:
- Native Mermaid diagram support (aligns with Decision #3)
- PPT/PDF export from Markdown source
- Integrates with existing python-pptx skills from Feature 002

**Rationale**: Purpose-built for MD presentations, supports Mermaid natively, proven ecosystem.

---

### 6. Skill Development Scope
**Question**: Should Feature 013 build new Claude skills or leverage existing ones?

**Decision**: Build complete presentation toolchain (Option C)

**Deliverables** (3 new skills in .claude/skills/):
1. **marp-convert.md**: Markdown→PPT/PDF conversion using Marp
2. **generate-mermaid.md**: Flowchart/sequence diagram generation
3. **validate-ux.md**: Human-in-loop UX feedback prompts

**Rationale**: Creates reusable toolchain for future presentation work; follows domain-agnostic pattern from Feature 009 (fetch-html.md, extract-json.md).

---

## User Stories (Prioritized)

### Priority 1: Clarify Speckit Terminology
**As a** workshop instructor using ../docs presentations
**I want** clear distinction between GitHub's Spec-Kit tool and our /speckit.* workflow
**So that** participants understand they're learning our proven methodology (Features 001-012), not an external experimental tool

**Acceptance Criteria**:
- Zero "GitHub Spec-Kit" references when describing our workflow (SC-001)
- All command examples use `/speckit.specify`, `/speckit.plan` format (SC-004)
- Presentations link to this repo's specs/ directory as proof (SC-005: ≥5 links)

**Why P1**: Current confusion undermines credibility; this repo has 12 features proving our workflow works.

---

### Priority 2: Add Feature 012 Case Study
**As a** workshop participant
**I want** a complete real-world example (Feature 012: Hellcube Proxy Generator)
**So that** I understand how the speckit workflow handles complex projects with actual constraints

**Acceptance Criteria**:
- Feature 012 appears in ≥3 ../docs sections (SC-002)
- Links to spec.md, plan.md, tasks.md from specs/012-hellcube-proxy-generator/ (FR-006)
- MCTS algorithm selection decision used as ReAct/Tree of Thoughts example (FR-008)

**Why P2**: Current examples (Spring Boot) don't show research-grade complexity (MCTS+VLM, 52 tasks, monorepo patterns).

---

### Priority 3: Update Tier Framework Classification
**As a** workshop designer
**I want** our workflow moved from "Tier 3: Experimental" to "Tier 2: Emerging Standard"
**So that** participants understand it's battle-tested with 12 completed features

**Acceptance Criteria**:
- SESSION-1 Slide 2b shows "Tier 2: Emerging Standards" (SC-003)
- Evidence: "12 features at github.com/josephrobertlopez/magic-cards-edh-deck/tree/main/specs"
- Tier comparison table shows "Internal: Heavy use across magic-cards-edh-deck repo"

**Why P3**: Important for credibility but lower priority than fixing terminology (P1) or adding evidence (P2).

---

## Functional Requirements (14 total)

### Content Updates (FR-001 to FR-010)
- **FR-001**: Distinguish "GitHub Spec-Kit" from "/speckit.* commands" with repo links
- **FR-002**: Update SESSION-1 Tier framework: Tier 3 → Tier 2 with 12-feature evidence
- **FR-003**: Include Feature 012 case study with links to specs/012-hellcube-proxy-generator/
- **FR-004**: All commands use `/speckit.*` format (specify, plan, clarify, tasks, analyze, implement, constitution)
- **FR-005**: Remove stale dates, use "As of [actual date]" format
- **FR-006**: Feature 012 docs link to ≥3 artifacts (spec.md, plan.md, tasks.md)
- **FR-007**: Reference "12 features completed" with specs/ directory link
- **FR-008**: SESSION-2 uses Feature 012 clarifications as ReAct/decision examples
- **FR-009**: Consistent terminology across SESSION-1, SESSION-2, WORKSHOP-OVERVIEW
- **FR-010**: All GitHub URLs point to correct paths (github.com/josephrobertlopez/magic-cards-edh-deck/tree/main/specs/...)

### Tooling & Format (FR-011 to FR-014)
- **FR-011**: Support PPT/PDF exports for offline distribution (Markdown remains primary)
- **FR-012**: Include Mermaid diagrams (flowcharts, sequence) for workflow/Feature 012 architecture
- **FR-013**: Validate content via human-in-loop UX prompts (understandability, info overload)
- **FR-014**: Deliver 3 new Claude skills: marp-convert.md, generate-mermaid.md, validate-ux.md

---

## Non-Functional Requirements (5 total)

- **NFR-001**: Presentation updates MUST NOT exceed 120min total (existing: SESSION-1 90min, SESSION-2 90min)
- **NFR-002**: Feature 012 content understandable to mid-level devs without ML background (validated via UX prompts)
- **NFR-003**: All repo links use valid GitHub URLs (https://github.com/josephrobertlopez/magic-cards-edh-deck/tree/main/specs/012-hellcube-proxy-generator/...)
- **NFR-004**: Changes tracked (copy files here for modification, provide ../docs PR instructions)
- **NFR-005**: Marp PPT/PDF exports preserve Mermaid rendering and visual consistency with Markdown

---

## Success Criteria (10 measurable outcomes)

| ID | Metric | Target | Validation Method |
|----|--------|--------|-------------------|
| SC-001 | "GitHub Spec-Kit" refs (our workflow context) | 0 | grep count in ../docs/*.md |
| SC-002 | Feature 012 case study sections | ≥3 | Manual review of SESSION-1/2 |
| SC-003 | Tier classification updated | "Tier 2: Emerging Standard" | Check SESSION-1 Slide 2b |
| SC-004 | Speckit command formatting | All 7 with `/` prefix | grep '/speckit\.' ../docs/*.md |
| SC-005 | Repo links (proof of methodology) | ≥5 distinct | Link counter across presentations |
| SC-006 | GitHub URL validation | 100% resolve | Automated link checker |
| SC-007 | Navigation depth (../docs → Feature 012) | <2 clicks | Manual UX test |
| SC-008 | Session duration maintained | 90min ±10% (slide count) | Count slides vs baseline |
| SC-009 | New Claude skills delivered | 3 (100%): marp-convert, generate-mermaid, validate-ux | ls .claude/skills/ |
| SC-010 | Marp export success rate | 100% (PPT + PDF) | Test conversion on all 3 presentations |

---

## Key Entities & Data Model

### Feature Spec (Existing)
- **Location**: This repo's specs/NNN-feature-name/ directories
- **Structure**: spec.md, plan.md, tasks.md, contracts/, checklists/, research.md, data-model.md
- **Count**: 12 features (001-012 completed)
- **Primary Example**: specs/012-hellcube-proxy-generator/ (MCTS+VLM, 52 tasks, contracts/)

### Speckit Command (Existing)
- **Location**: .claude/commands/
- **Commands**: /speckit.specify, /speckit.plan, /speckit.clarify, /speckit.tasks, /speckit.analyze, /speckit.implement, /speckit.constitution
- **Current Issue**: Confused with external "GitHub Spec-Kit" tool in ../docs presentations

### Presentation Material (Target for Updates)
- **Location**: ../docs/bootcamp-materials/presentations/
- **Files**:
  - SESSION-1-industry-standards.md (90min, Tier framework)
  - SESSION-2-advanced-patterns.md (90min, advanced patterns)
  - WORKSHOP-OVERVIEW.md (overview)
- **Current State**: References "Tier 3: Experimental", uses GitHub Spec-Kit terminology, no Feature 012 examples

### Tier Classification (Framework to Update)
- **Current**: "Tier 3: Experimental"
- **Target**: "Tier 2: Emerging Standard (12 features proven)"
- **Evidence**: Link to github.com/josephrobertlopez/magic-cards-edh-deck/tree/main/specs

### Claude Skill (New Deliverables)
- **Location**: .claude/skills/ directory
- **New Skills for Feature 013**:
  1. **marp-convert.md**: Markdown→PPT/PDF conversion using Marp CLI
  2. **generate-mermaid.md**: Flowchart/sequence diagram generation from spec descriptions
  3. **validate-ux.md**: Human-in-loop UX feedback prompts (understandability, info overload checks)
- **Pattern**: Follows domain-agnostic approach from Feature 009 (fetch-html.md, extract-json.md)

---

## Edge Cases & Handling

### Multi-Repo References
**Scenario**: ../docs references features from multiple repos (magic-cards-edh-deck, agentic-code)
**Handling**: Focus on magic-cards-edh-deck as primary (12 features, well-documented); mention others as supporting evidence without detailed links

### Version Sync
**Scenario**: How to keep ../docs in sync with this repo's evolving specs/?
**Handling**: Add "Last Updated: 2025-11-16" dates; link to specific commit SHAs or branch names (e.g., "main branch as of 2025-11-16")

### Technical Complexity
**Scenario**: Feature 012 MCTS math too technical for workshop audience?
**Handling**: Create simplified excerpts focusing on process (spec→plan→tasks), use screenshots of spec.md structure, highlight user stories (not MCTS equations)

### Cross-Repo Updates
**Scenario**: How to apply changes from this repo to ../docs repo?
**Handling**: Copy files to specs/013-update-presentations/, modify here, test, then provide manual PR instructions with diffs for ../docs repo

---

## Dependencies

### Source Material (This Repo)
- specs/012-hellcube-proxy-generator/spec.md (clarifications from Session 2025-11-16)
- specs/012-hellcube-proxy-generator/plan.md
- specs/012-hellcube-proxy-generator/tasks.md
- specs/012-hellcube-proxy-generator/contracts/mcts_layout.md
- specs/012-hellcube-proxy-generator/contracts/vlm_evaluators.md
- specs/ directory listing (001-012 completed features)

### Target Files (../docs Repo)
- ../docs/bootcamp-materials/presentations/SESSION-1-industry-standards.md
- ../docs/bootcamp-materials/presentations/SESSION-2-advanced-patterns.md
- ../docs/bootcamp-materials/presentations/WORKSHOP-OVERVIEW.md

### Reference Materials (../docs Repo)
- ../docs/bootcamp-materials/references/tier-framework.md
- ../docs/bootcamp-materials/references/spec-folder-guide.md

### External Tools
- **Marp** (Markdown Presentation Ecosystem): MD→PPT/PDF conversion with Mermaid support
- Existing python-pptx skills from Feature 002 (consolidate-codebase)

### Internal Patterns
- Domain-agnostic skill pattern from Feature 009 (fetch-html.md, extract-json.md templates)

---

## Out of Scope (Explicit Exclusions)

### Content Scope
- ❌ Creating new Session 3 in ../docs (only updating existing SESSION-1, SESSION-2, WORKSHOP-OVERVIEW)
- ❌ Removing Spring Boot examples (they remain primary hands-on material)
- ❌ Redesigning tier framework categories (only updating our workflow's placement)
- ❌ Detailed MCTS algorithm deep-dive (case study remains high-level, process-focused)

### Format & Media
- ❌ Creating video recordings or other non-markdown media
- ❌ Translating presentations to other languages
- ❌ Building skills for formats other than Marp/Mermaid (no reveal.js, Beamer, Powerpoint templates)

### Automation & Integration
- ❌ Setting up automated sync between this repo and ../docs
- ❌ Automated readability metrics or linting (using human-in-loop UX validation only)

### Infrastructure
- ❌ Modifying this repo's .claude/commands/ (using existing /speckit.* commands as-is)

---

## Assumptions

1. **Repository Access**: magic-cards-edh-deck is publicly accessible at github.com/josephrobertlopez/magic-cards-edh-deck
2. **Separate Repos**: ../docs is a separate git repository that can be updated independently via PR
3. **Quality Baseline**: Feature 012 (specs/012-hellcube-proxy-generator/) is complete and representative quality for case study
4. **Audience Access**: Workshop participants can access GitHub to follow links from ../docs to this repo
5. **Format Strategy**: Markdown source files remain primary format; PPT/PDF are generated exports for offline distribution
6. **Command Stability**: /speckit.* commands defined in .claude/commands/ are stable and won't change during Feature 013
7. **Evidence Sufficiency**: 12 features in specs/ directory (001-012) provide sufficient evidence for Tier 2 classification

---

## Implementation Phases (High-Level)

### Phase 1: Skill Development
Build 3 new Claude skills following Feature 009 domain-agnostic pattern:
1. marp-convert.md (Marp CLI wrapper)
2. generate-mermaid.md (diagram generation)
3. validate-ux.md (human-in-loop feedback)

### Phase 2: Content Preparation
1. Copy SESSION-1, SESSION-2, WORKSHOP-OVERVIEW from ../docs to specs/013-update-presentations/
2. Generate Mermaid diagrams (speckit workflow, Feature 012 architecture)
3. Extract Feature 012 case study excerpts (process-focused, accessible to mid-level devs)

### Phase 3: Presentation Updates
1. **P1 - Terminology**: Replace "GitHub Spec-Kit" with "/speckit.* commands" + repo links
2. **P2 - Case Study**: Insert Feature 012 examples in SESSION-2 (ReAct/ToT patterns)
3. **P3 - Tier Update**: Move workflow from Tier 3 → Tier 2 in SESSION-1 Slide 2b

### Phase 4: Validation & Export
1. Run validate-ux.md skill for human feedback (understandability, info overload)
2. Validate all GitHub URLs resolve (SC-006: 100%)
3. Generate PPT/PDF exports via marp-convert.md (SC-010: 100% success)

### Phase 5: Cross-Repo PR
1. Test all changes in this repo (link validation, diagram rendering)
2. Generate PR instructions for ../docs repo with diffs
3. Provide manual merge steps for ../docs maintainer

---

## Testing Strategy

### Link Validation (Automated)
```bash
# SC-006: 100% GitHub URL resolution
grep -r "github.com/josephrobertlopez/magic-cards-edh-deck" specs/013-update-presentations/*.md | \
  xargs -I {} curl -s -o /dev/null -w "%{http_code} {}\n" {}
```

### Terminology Check (Automated)
```bash
# SC-001: Zero "GitHub Spec-Kit" refs for our workflow
grep -c "GitHub Spec-Kit" specs/013-update-presentations/SESSION-*.md
# Expected: 0 (or only in comparison context, not describing our workflow)

# SC-004: All 7 speckit commands with `/` prefix
grep -o '/speckit\.\w\+' specs/013-update-presentations/*.md | sort -u | wc -l
# Expected: 7 (specify, plan, clarify, tasks, analyze, implement, constitution)
```

### Case Study Presence (Manual)
- SC-002: Feature 012 in ≥3 sections (grep "Feature 012\|Hellcube\|MCTS" SESSION-2.md)
- FR-006: Links to spec.md, plan.md, tasks.md exist

### UX Validation (Human-in-Loop)
- Run validate-ux.md skill: prompt for feedback on each updated section
- Check: jargon density, technical depth, narrative flow
- Target: understandable to mid-level devs without ML background (NFR-002)

### Export Testing (Automated)
```bash
# SC-010: Marp PPT/PDF generation (100% success)
marp-convert.md SESSION-1-industry-standards.md --output formats=pptx,pdf
# Expected: 2 files generated, Mermaid diagrams preserved
```

---

## Metrics & Monitoring

| Metric | Baseline | Target | Validation |
|--------|----------|--------|------------|
| "GitHub Spec-Kit" refs (our workflow) | 3 | 0 | grep count |
| Feature 012 sections | 0 | ≥3 | manual count |
| Tier classification | Tier 3 | Tier 2 | SESSION-1 Slide 2b |
| Speckit command format | mixed | 7 with `/` | grep pattern |
| Repo links | 0 | ≥5 | link counter |
| GitHub URL resolution | unknown | 100% | curl test |
| Navigation depth | unknown | <2 clicks | UX test |
| Slide count (SESSION-1) | ~X slides | ±10% | slide counter |
| New skills delivered | 0 | 3 | ls .claude/skills/ |
| Marp export success | N/A | 100% | conversion test |

---

## Risk Assessment

### High Risk
- **Cross-repo coordination**: Manual PR to ../docs may introduce errors → Mitigation: Thorough diff review, test links before PR
- **Marp tooling dependency**: If Marp fails, no PPT/PDF exports → Mitigation: Test early, fallback to existing python-pptx skills

### Medium Risk
- **Feature 012 complexity**: MCTS math may still confuse audience → Mitigation: UX validation loops, simplify excerpts
- **Link rot**: GitHub URLs may break if repo structure changes → Mitigation: Use commit SHAs, add "Last Updated" dates

### Low Risk
- **Mermaid rendering**: Diagrams may not export cleanly → Mitigation: Marp natively supports Mermaid, NFR-005 enforces consistency
- **Skill reusability**: New skills may not generalize → Mitigation: Follow Feature 009 domain-agnostic pattern

---

## Next Steps

1. **Run `/speckit.plan`**: Generate implementation plan with task breakdown
2. **Prototype Marp skill**: Validate MD→PPT/PDF conversion early (risk mitigation)
3. **Extract Feature 012 excerpts**: Identify process-focused, accessible content for case study
4. **Generate workflow diagrams**: Create Mermaid flowcharts for speckit command flow
5. **Copy ../docs files**: Set up specs/013-update-presentations/ workspace

---

## Appendix: Related Features

- **Feature 002**: Consolidate codebase (python-pptx skills, LibreOffice integration)
- **Feature 009**: Domain-agnostic skills (fetch-html.md, extract-json.md patterns)
- **Feature 010**: Parallel batch processing (A2A workflow framework)
- **Feature 012**: Hellcube Proxy Generator (MCTS+VLM case study, 52 tasks, contracts/)

---

**Document Status**: Complete - Ready for Planning Phase
**Last Updated**: 2025-11-16
**Clarification Session**: 5 questions answered (cross-repo workflow, formats, visuals, UX validation, tooling, skill scope)
