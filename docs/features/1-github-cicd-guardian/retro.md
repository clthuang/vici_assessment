# Retrospective: GitHub CI/CD Guardian

## What Went Well

- Multi-phase review process with dedicated reviewer personas (spec-reviewer, design-reviewer, security-reviewer) caught issues early before they compounded downstream
- All 4 spec blockers resolved in iteration 1 before design phase began, preventing rework
- Security reviewer identified 3 medium-severity issues (prompt injection scope, log fallback exposure, credential redaction) -- all addressed before approval
- 67 automated validation checks provide regression testing without external dependencies
- Disciplined scope management: V2 features (P2-P6) documented but excluded from MVP
- Token budget treated as first-class constraint kept SKILL.md at 238 lines (vs 500-line limit)
- Clear traceability: all P0/P1 spec requirements map to implementation via automated grep-based validation

## What Could Improve

- Initial spec was over-engineered for a markdown prompt file -- UX reviewer feedback required simplification from 6 formal tiers to 3 behavioral rules
- Multiple review cycles spent fixing stale cross-references after structural changes (e.g., tier numbers became invalid after triaging simplification)
- Checkbox UI designed for P0 output before considering terminal context limitations
- Frontmatter description format required correction to trigger-phrase style per Claude Code docs
- Some design decisions (plugin.json location) required correction based on authoritative docs verification

## Learnings Captured

### Patterns
- **Layered review architecture**: Spec -> Design -> Plan -> Tasks -> Implement, each with blockers/warnings/suggestions categorization
- **Error handling enumeration**: Spec lists all conditions, design prescribes messages, validation verifies coverage
- **Layered fallback for external data**: primary tool -> API -> LLM knowledge with explicit staleness caveat
- **Security invariant verification**: Each "never do X" requirement maps to an explicit automated test metric (SM-7, SM-8, SM-9)
- **Grep-based validation**: Enables automated regression testing for LLM skill files without compilation or runtime dependencies

### Anti-Patterns
- Over-engineering markdown prompts with formal tier systems when 3 behavioral rules suffice
- Including V2 placeholder sections in MVP (wastes tokens, adds no value)
- Creating maintenance-heavy reference tables when error-driven discovery works better
- Designing UI patterns without considering deployment context (terminal vs web)
- Allowing stale cross-references to accumulate during structural refactoring

### Heuristics
- Include success metrics (SM-N) section upfront in spec -- missing metrics are a blocker
- Triaging simplicity: reduce behavioral contracts to <5 rules; 3 rules + reference table beats 6 formal tiers
- Reference file threshold: content >40 lines that's static per invocation -> move to references/ directory
- Honest value propositions: explicitly document what tool does NOT deliver
- Use trigger-phrase format in frontmatter descriptions for reliable auto-activation

## Knowledge Bank Updates

- Added `claude-code-skill-patterns.md` to knowledge bank with skill development patterns
