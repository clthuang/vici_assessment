# Feature 007: AI-Led MCP Browser Control Redesign

## Status: PRD Complete

## Overview

Fundamentally rethink SubTerminator's browser automation to be AI-led with MCP-style tool invocation. The AI model becomes the orchestrator that decides which actions to take, while our system acts as a server providing tools, executing actions, and returning rich feedback.

## Key Design Decisions

1. **AI Orchestrates, We Execute**: No agent-side loops. AI calls tools in sequence.
2. **Single-Tool-Per-Turn**: Each action returns fresh snapshot to avoid stale refs.
3. **Element References**: Use `@e1, @e2` refs valid for exactly ONE action.
4. **Screenshots Always Included**: Visual confirmation prevents AI assumptions.
5. **Server-Enforced Checkpoints**: Human approval is server-triggered, not AI-decided.
6. **Direct API**: Not MCP protocol transport (can wrap later).

## Artifacts

| Artifact | Status | Description |
|----------|--------|-------------|
| `prd.md` | Complete | Product requirements with research findings |
| `spec.md` | Pending | Detailed technical specification |
| `design.md` | Pending | Architecture and interfaces |
| `plan.md` | Pending | Implementation plan |
| `tasks.md` | Pending | Task breakdown |

## Critical Hypothesis

This feature includes a **Phase 0 validation** before full implementation:
- Test if Claude can reliably sequence browser tool calls
- Success threshold: >70% completion in <10 turns
- Abort if <50% success

## Related

- Feature 006: AI-Driven Browser Control (current implementation being replaced)
- Brainstorm: `docs/brainstorms/20260205-ai-mcp-redesign.prd.md`

## Next Steps

Run `/specify` to create detailed technical specification.
