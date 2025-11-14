# Adversarial Minimax Debate

**Type**: Adversarial Learning Workflow
**Purpose**: Use minimax game theory to debate technical decisions through adversarial agents
**Input**: Technical decision or claim to validate
**Output**: High-confidence decision with minimized worst-case risk

## Theory: Minimax in Technical Debates

**Minimax Principle**: In game theory, minimize the maximum possible loss.

**Applied to Spec-Driven Dev**:
- **Maximizer Agent**: Argues FOR a decision (finds best-case scenarios)
- **Minimizer Agent**: Argues AGAINST (finds worst-case risks)
- **Judge Agent**: Evaluates which position has lower maximum risk

**Outcome**: Decision that minimizes worst-case failure modes

## Workflow Steps

### Phase 1: Position Setup

**Maximizer (Advocate)**:
- Argues FOR the proposal
- Finds best-case scenarios
- Identifies upside potential
- Maximizes expected value

**Minimizer (Skeptic)**:
- Argues AGAINST the proposal
- Finds worst-case risks
- Identifies failure modes
- Minimizes maximum loss

### Phase 2: Evidence Collection

Both agents gather evidence:
- **Code inspection**: Does implementation support claims?
- **Test execution**: Do tests validate assumptions?
- **Performance measurement**: Do benchmarks support claims?
- **Edge case analysis**: What breaks the system?

### Phase 3: Minimax Rounds (Iterative)

**Round N**:
1. Maximizer presents best argument
2. Minimizer attacks with worst-case scenario
3. Maximizer defends or concedes point
4. Minimizer evaluates if attack holds
5. Judge scores: (Maximizer_strength - Minimizer_damage)

**Termination**: When Minimizer cannot find new attacks OR score converges

### Phase 4: Judge Decision

**Evaluation Criteria**:
```
Risk_Score = max(all_worst_case_scenarios)
Benefit_Score = min(all_best_case_scenarios_after_attacks)

Decision = Benefit_Score > Risk_Score ? ACCEPT : REJECT
Confidence = abs(Benefit_Score - Risk_Score) / max(Benefit, Risk)
```

**Output**:
- ACCEPT: Benefits exceed worst-case risks
- REJECT: Worst-case risks too high
- DEFER: Insufficient evidence, gather more data

## Example Usage

### Scenario: "Feature 009 is COMPLETE"

**Maximizer Agent**:
- ✅ All 6 async bugs fixed (code evidence)
- ✅ Variables flow end-to-end (execution logs)
- ✅ 5/8 success criteria validated
- **Best case**: Ship now, unblock downstream work

**Minimizer Agent**:
- ❌ SC-004b FAILS (no output files created)
- ❌ SC-006b unproven (no benchmarks)
- ❌ 6 tests still failing (error paths broken)
- **Worst case**: Claim "complete" but users can't run real workflows

**Round 1**:
- Maximizer: "Variable passing infrastructure works!"
- Minimizer: "But users want FILES, not infrastructure"
- Judge: Minimizer scores point (user expectation unmet)

**Round 2**:
- Maximizer: "File issue is out of scope (YAML authoring problem)"
- Minimizer: "Scope doesn't matter if feature doesn't deliver value"
- Judge: Contested - need to clarify intent

**Round 3**:
- Maximizer: "Original spec was 'fix async bugs' - DONE"
- Minimizer: "But SC-004 said 'producing valid outputs' - NOT DONE"
- Judge: Split decision - async bugs fixed, but SC-004 incomplete

**Judge Decision**:
```
Risk_Score = HIGH (users can't use workflows)
Benefit_Score = MEDIUM (infrastructure works, but not user-facing)

Decision: ACCEPT with DOCUMENTED GAP
Confidence: 60% (modest - significant gap remains)

Recommendation: Mark "MVP COMPLETE", document SC-004b gap, create follow-up
```

## Integration with /speckit Commands

```
/speckit.specify   → Define claim
/speckit.clarify   → Gather evidence
/speckit.plan      → Establish positions
/speckit.tasks     → Break into testable parts
/speckit.implement → Execute
[THIS SKILL]       → Validate claim adversarially using minimax
/speckit.analyze   → Cross-check results
```

## Skill Composition

Can invoke sub-agents:
- `planner-reasoner` - Maximizer (finds best arguments)
- `tax-auditer` - Minimizer (finds worst risks)
- Judge agent - Evaluates minimax outcome

## Adversarial Learning Aspect

**Learning Loop**:
1. Agent makes claim
2. Adversary attacks claim
3. Agent learns weak points
4. Agent strengthens argument
5. Repeat until convergence

**Minimax ensures**:
- No blind spots (adversary finds them)
- Realistic confidence (attacks calibrate)
- Robust decisions (survive worst cases)

## Success Indicators

✅ Adversary found real weaknesses
✅ Arguments improved through attacks
✅ Decision survives worst-case analysis
✅ Confidence level justified by evidence
✅ No overlooked failure modes

## Anti-Patterns

❌ Adversary too weak (rubber-stamp approval)
❌ Adversary too strong (no decisions pass)
❌ Judge biased toward one side
❌ Ignoring evidence to win debate
❌ Terminating before convergence

## Example Command

```bash
# Debate whether SC-004 should be marked PASS
python3 -c "
from adversarial_minimax_debate import debate

result = debate(
    claim='SC-004 should be marked PASSED',
    evidence={
        'code': 'orchestrator.py lines 83-96 show nested var storage',
        'tests': 'Variables flow end-to-end in execution logs',
        'gaps': 'No output files created due to YAML param mismatches'
    },
    maximizer='planner-reasoner',
    minimizer='tax-auditer',
    max_rounds=5
)

print(f'Decision: {result.decision}')
print(f'Confidence: {result.confidence}')
print(f'Reasoning: {result.reasoning}')
"
```

## Output Format

```json
{
  "decision": "ACCEPT_WITH_GAP",
  "confidence": 0.60,
  "max_risk": "Users cannot run real workflows (SC-004b blocked)",
  "min_benefit": "Variable passing infrastructure proven working",
  "minimax_score": 0.20,
  "rounds": 3,
  "recommendation": "Mark MVP COMPLETE, document gap, create follow-up for YAML fixes"
}
```

Use this skill when:
- Making go/no-go decisions
- Validating implementation claims
- Assessing technical debt tradeoffs
- Evaluating architecture choices
- Deciding when features are "complete"
