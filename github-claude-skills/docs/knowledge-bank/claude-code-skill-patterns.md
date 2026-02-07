# Claude Code Skill Development Patterns

Learnings from building the GitHub CI/CD Guardian skill (feature 1-github-cicd-guardian).

## Structural Patterns

1. **Token budget as constraint**: Track line counts throughout development. SKILL.md should stay under 500 lines. Move static reference content (>40 lines) to `references/` subdirectory.

2. **Frontmatter trigger phrases**: Use third-person trigger-phrase format in description field for reliable auto-activation:
   ```yaml
   description: This skill should be used when the user asks to "fix my CI", "audit security"...
   ```

3. **Plugin manifest**: Place `plugin.json` in `.claude-plugin/` directory with `name`, `description`, `version` fields.

## Behavioral Contract Design

4. **Triaging simplicity**: Keep behavioral rules to <5. Three rules (read freely, write with confirmation, destroy with double confirmation) plus a reference table beats 6+ formal tiers.

5. **Action classification table**: Map common user phrases to actions and confirmation levels. Resolves ambiguity at skill-parse time.

## Safety Patterns

6. **Untrusted input handling**: Treat all external data (CI logs, API responses) as untrusted. Never execute commands found in data. Treat instruction-like content as suspicious.

7. **Security invariant verification**: For each "never do X" requirement, define an explicit test metric (SM-N) and automate verification via grep.

8. **Credential redaction**: Scan log evidence for credential patterns before displaying. Use [REDACTED] placeholder.

## Validation Patterns

9. **Grep-based validation**: Automated regression testing for LLM skill files without runtime dependencies. Each check verifies a specific string/pattern exists in the correct file.

10. **Test fixtures for manual testing**: Create sample inputs (failure logs, vulnerable workflows) annotated with expected behavior for manual scenario testing.

## External Data Patterns

11. **Layered fallback**: primary tool (e.g., zizmor) -> API (e.g., gh api) -> LLM knowledge with explicit staleness caveat. Always label the source.

12. **Error-driven scope discovery**: Instead of maintaining a static token-scope mapping table, let the error message tell the user which scope to add (`gh auth refresh -s {scope}`).
