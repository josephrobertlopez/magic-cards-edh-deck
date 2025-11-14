# Audit and Remediate Workflow

**Type**: Spec-Driven Development Workflow
**Purpose**: Validate implementation claims against spec success criteria, then remediate critical gaps
**Input**: Feature directory with spec.md, plan.md, tasks.md, and implementation code
**Output**: Validated feature with critical gaps fixed or documented

## Workflow Steps

### Phase 1: Load Context (Progressive Disclosure)

```bash
# Get feature artifacts
FEATURE_DIR=$(pwd)/specs/[feature-id]
SPEC=$FEATURE_DIR/spec.md
PLAN=$FEATURE_DIR/plan.md
TASKS=$FEATURE_DIR/tasks.md
```

**Extract from spec.md:**
- Success Criteria (SC-001, SC-002, etc.)
- Functional Requirements (FR-001, FR-002, etc.)
- User Stories with acceptance scenarios

**Extract from plan.md:**
- Validation claims (✅ assertions about what works)
- Implementation summary

### Phase 2: Adversarial Audit (Evidence-Based)

For each Success Criterion, determine status:
- **VALIDATED**: Direct evidence supports claim
- **PARTIALLY VALIDATED**: Some evidence, but gaps remain
- **UNVALIDATED**: No concrete evidence found
- **CONTRADICTED**: Evidence contradicts claim

**Audit Techniques:**
1. **Execute workflows** - Do they complete without errors?
2. **Check outputs** - Are claimed files actually created?
3. **Run tests** - Do test results match claims?
4. **Review code** - Does implementation match requirements?
5. **Measure performance** - Do benchmarks support claims?

### Phase 3: Categorize Gaps by Severity

**CRITICAL**: Functional blocker - feature doesn't work for core use case
**HIGH**: Quality issue - feature works but unreliably or incompletely
**MEDIUM**: Validation gap - feature works but not proven
**LOW**: Documentation or polish issue

### Phase 4: Reasoning - Decide Next Action

**Question 1**: What is the CORE VALUE of this feature?
**Question 2**: Are the gaps ESSENTIAL to that core value?
**Question 3**: What is MINIMUM work for production-ready?
**Question 4**: Remediate now or defer?

**Decision Matrix:**
- CRITICAL gaps → Must fix before claiming complete
- HIGH gaps → Fix if <2 hours, else document
- MEDIUM gaps → Document and defer
- LOW gaps → Defer to polish phase

### Phase 5: Execute Remediation

**If fixing gaps:**
1. Create todo list for gap remediation
2. Debug root cause
3. Implement fix
4. Re-validate success criteria
5. Update plan.md with corrected status

**If deferring gaps:**
1. Document known limitations in spec.md
2. Update plan.md validation claims to be accurate
3. Add TODO for future work if needed
4. Mark feature as "Complete with known gaps"

### Phase 6: Final Validation

Run `/speckit.analyze` one more time to confirm:
- All CRITICAL gaps resolved
- All claims accurate
- Known gaps documented

## Example Usage

```bash
# Audit feature 009
cd /path/to/repo
python3 a2a_orchestrator/orchestrator.py workflows/proxy_pipeline_composed.yaml decklist_path=decklists/frog_tribal.txt

# Check outputs
ls -lh outputs/  # Are claimed outputs present?

# Run tests
pytest tests/ -v  # Do results match claims?

# Debate remediation strategy
# Use planner-reasoner agent to evaluate options

# Fix critical gaps
# (implementation)

# Re-validate
pytest tests/ -v
python3 a2a_orchestrator/orchestrator.py workflows/test.yaml

# Update docs
vim specs/009-fix-async-skill-execution/plan.md
```

## Integration with /speckit Commands

This workflow bridges `/speckit.implement` → next feature:

```
/speckit.specify   → Create spec.md
/speckit.clarify   → Resolve ambiguities
/speckit.plan      → Generate plan.md
/speckit.tasks     → Generate tasks.md
/speckit.implement → Execute implementation
[THIS SKILL]       → Validate and remediate gaps
/speckit.analyze   → Final cross-artifact check
→ Commit or proceed to next feature
```

## Success Indicators

✅ All CRITICAL success criteria validated
✅ Validation claims in plan.md match reality
✅ Known gaps documented in spec.md
✅ Feature delivers core value reliably
✅ Ready for commit or next feature

## Anti-Patterns to Avoid

❌ Claiming "complete" without testing
❌ Deferring CRITICAL functional gaps
❌ Creating skills/meta-tooling before fixing bugs
❌ Over-validating MEDIUM/LOW gaps (diminishing returns)
❌ Ignoring contradictory evidence

## Skill Composition

This skill can be decomposed into:
1. `audit-success-criteria.md` - Evidence collection
2. `adversarial-review.md` - Skeptical validation
3. `gap-prioritization.md` - Severity assessment
4. `remediation-planning.md` - Decision logic
5. `fix-and-revalidate.md` - Implementation loop

Use as a monolithic workflow or compose sub-skills as needed.
