# PRD: AI Browser Orchestration via Existing MCP Tools

## Executive Summary

**Pivot from building to orchestrating**: Instead of implementing custom browser control tools from scratch, leverage existing battle-tested MCP (Model Context Protocol) servers (Playwright MCP, browser-use, Chrome DevTools) and focus on building a thin orchestration layer that:

1. Connects MCP servers to AI models programmatically
2. Adds service-specific logic (checkpoints, completion verification)
3. Provides a simple CLI for end users

### Key Insight

The original PRD (Feature 007) proposed building 7 custom browser tools, element registries, snapshot factories, and action executors. **This is unnecessary** when:
- [Playwright MCP](https://github.com/microsoft/playwright-mcp) already provides `browser_snapshot`, `browser_click`, `browser_type`, etc.
- [browser-use](https://docs.browser-use.com/customize/integrations/mcp-server) provides a complete browser automation MCP server
- [mcp-use](https://github.com/mcp-use/mcp-use) connects MCP servers to any LLM in 6 lines of code

**Our value-add**: Service-specific orchestration, human checkpoints, model-agnostic design.

### Assumptions Requiring Validation (Phase 1 POC)

| Assumption | Risk if Wrong | Validation Method |
|------------|---------------|-------------------|
| mcp-use works reliably with Playwright MCP | Medium - fallback to official SDK | POC: Run 5 test scenarios |
| Playwright MCP snapshot format is parseable for checkpoints | High - checkpoint logic fails | POC: Log actual snapshot output, adapt code |
| LangChain tool format conversion works for both Claude/GPT | Medium - model lock-in | POC: Test with both APIs |
| Node.js/npx available or easily installable | Low - add install instructions | POC: Test on fresh machine |

**Honest acknowledgment**: The "6-line integration" claim for mcp-use is marketing copy. Real integration will require error handling, retries, and format adaptation. Time estimates include 50% buffer for integration debugging.

---

## Problem Statement

### What the Original PRD Got Right
- AI should orchestrate (decide which actions to take)
- Server should execute and return state
- Human checkpoints are needed for irreversible actions
- Single tool per turn is the right pattern

### What the Original PRD Got Wrong
- **Building browser tools from scratch** - Playwright MCP already has these
- **Custom element reference system** - Playwright MCP's `ref` system works fine
- **Custom snapshot format** - Use existing formats
- **52 implementation tasks** - Massive over-engineering

### Target User
Developer or technical user comfortable with:
- Command-line interfaces
- Environment variables for API keys
- Python package installation (pip/pipx)

Non-technical end users are out of scope for v1.

### Real Requirements
1. **Standalone service**: Users install, provide API key, run
2. **No Claude Code dependency**: Works as a CLI tool
3. **Model-agnostic**: Should work with Claude, GPT-4, or other models
4. **Service-specific logic**: Netflix cancellation needs specific checkpoints

### Non-Goals (Explicitly Out of Scope)
| Non-Goal | Rationale |
|----------|-----------|
| Building custom browser tools | Playwright MCP already provides these |
| Custom element reference system | Playwright MCP's `ref` system works |
| Custom snapshot format | Use Playwright MCP's accessibility tree |
| Automated 2FA / CAPTCHA solving | Requires specialized services; use checkpoint for human |
| Multi-service in single task | Complexity; defer to v2 |
| GUI interface | CLI-first for v1; GUI can wrap CLI later |
| Persistent conversation across sessions | Fresh start each task; state recovery is v2 |

### Relationship to Existing Implementation

The current codebase has substantial infrastructure in `src/subterminator/core/`:

| Existing Code | Lines | Decision |
|---------------|-------|----------|
| `agent.py` - AIBrowserAgent | ~870 | **Deprecate** - tied to perceive/plan/execute pattern |
| `engine.py` - CancellationEngine | ~400 | **Deprecate** - state machine approach doesn't fit |
| `browser.py` - PlaywrightBrowser | ~800 | **Keep** - can be used alongside MCP or as fallback |
| `ai.py` - AIClient | ~300 | **Refactor** - extract model-agnostic parts |
| `protocols.py` - State, ActionPlan | ~400 | **Partial keep** - reuse useful dataclasses |

**Rationale for deprecation**: The existing agent uses a perceive → plan → execute loop where WE orchestrate. The new approach lets the AI orchestrate via tool calls. These are fundamentally different patterns that can't easily merge.

**Migration path**:
1. New orchestration code lives in `src/subterminator/mcp_orchestrator/` (new package)
2. CLI adds `--experimental-mcp` flag initially
3. Old code path remains available for comparison
4. After validation (>80% success rate), MCP becomes default

---

## Research Findings

### Available MCP Browser Solutions (2025-2026)

| Solution | Type | Maturity | Model Support | Key Features |
|----------|------|----------|---------------|--------------|
| [Playwright MCP](https://github.com/microsoft/playwright-mcp) | MCP Server | Production | Any MCP client | Microsoft-backed, snapshot+refs, accessibility-first |
| [browser-use](https://docs.browser-use.com) | Library + MCP | Production | LangChain models | High-level tasks, cloud profiles |
| [Chrome DevTools MCP](https://developer.chrome.com/blog/chrome-devtools-mcp) | MCP Server | Production | Any MCP client | Google-backed, DevTools integration |
| [mcp-use](https://github.com/mcp-use/mcp-use) | MCP Client | Stable | LangChain (any LLM) | 6-line integration |
| [Official MCP SDK](https://github.com/modelcontextprotocol/python-sdk) | Client/Server | Stable | Protocol-level | Full control, more code |

### Key Research Sources
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Official client library
- [Build an MCP Client](https://modelcontextprotocol.io/docs/develop/build-client) - Official docs
- [Playwright MCP Guide](https://testdino.com/blog/playwright-mcp/) - Comprehensive setup guide
- [Browser Automation MCP Servers Guide](https://www.skyvern.com/blog/browser-automation-mcp-servers-guide/) - 2025 comparison

---

## Proposed Solution

### Architecture: Orchestration Layer

```
┌────────────────────────────────────────────────────────────────┐
│                    subterminator CLI                            │
│                                                                 │
│  $ subterminator cancel --service netflix                       │
│  $ ANTHROPIC_API_KEY=xxx subterminator cancel netflix           │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                          │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ MCPClientManager │  │ LLMClient        │  │ ServiceConfig │  │
│  │ - Connect to     │  │ - Claude API     │  │ - Checkpoints │  │
│  │   MCP servers    │  │ - OpenAI API     │  │ - Completion  │  │
│  │ - Get tool list  │  │ - Tool dispatch  │  │   criteria    │  │
│  │ - Execute calls  │  │                  │  │               │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Task Runner                                               │  │
│  │ - Single-tool-per-turn loop                               │  │
│  │ - Human checkpoint enforcement                            │  │
│  │ - Completion verification                                 │  │
│  │ - Error recovery                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│              MCP Server (Playwright MCP / browser-use)          │
│                                                                 │
│  Existing tools (we don't build these):                         │
│  - browser_snapshot  - browser_click  - browser_type            │
│  - browser_navigate  - browser_select_option  - etc.            │
└────────────────────────────────────────────────────────────────┘
```

### What We Build vs What We Reuse

| Component | Build or Reuse | Notes |
|-----------|----------------|-------|
| Browser control tools | **REUSE** | Playwright MCP provides all 15+ tools |
| Element reference system | **REUSE** | Playwright MCP's `ref` system |
| Snapshot format | **REUSE** | Accessibility tree from MCP |
| MCP client connection | **REUSE** | mcp-use or official SDK |
| LLM abstraction | **REUSE** | LangChain or direct API |
| **Orchestration loop** | **BUILD** | Our value-add |
| **Human checkpoints** | **BUILD** | Service-specific |
| **Completion verification** | **BUILD** | Service-specific |
| **CLI interface** | **BUILD** | User-facing |
| **Service configs** | **BUILD** | Netflix, etc. |

---

## Feature Requirements

### FR1: MCP Server Integration

**Description**: Connect to existing MCP browser servers as a client.

**Supported Servers** (in priority order):
1. **Playwright MCP** (primary) - Most complete tool set
2. **browser-use** (alternative) - Higher-level abstractions
3. **Chrome DevTools MCP** (fallback) - If others unavailable

**Implementation Options**:

Option A: Using mcp-use (simplest)
```python
from langchain_anthropic import ChatAnthropic
from mcp_use import MCPAgent, MCPClient

config = {
    "mcpServers": {
        "playwright": {
            "command": "npx",
            "args": ["@playwright/mcp@latest"]
        }
    }
}

client = MCPClient.from_dict(config)
llm = ChatAnthropic(model="claude-sonnet-4-20250514")
agent = MCPAgent(llm=llm, client=client)
```

Option B: Using official MCP SDK (more control)
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="npx",
    args=["@playwright/mcp@latest"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        # Now we have tool schemas to send to LLM
```

**Acceptance Criteria**:
- [ ] Can connect to Playwright MCP server
- [ ] Can list available tools
- [ ] Can execute tool calls and get results
- [ ] Handles server connection errors gracefully

### FR2: Model-Agnostic LLM Integration

**Description**: Support multiple AI models without code changes.

**Supported Models**:
- Claude (Anthropic) - Primary
- GPT-4 (OpenAI) - Secondary
- Local models via Ollama - Future

**Configuration**:
```bash
# Environment variables
ANTHROPIC_API_KEY=sk-ant-...  # For Claude
OPENAI_API_KEY=sk-...         # For GPT-4
SUBTERMINATOR_MODEL=claude-sonnet-4-20250514  # Model selection
```

**Implementation**:
```python
from langchain_core.language_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

def get_llm(model_name: str) -> BaseChatModel:
    if model_name.startswith("claude"):
        return ChatAnthropic(model=model_name)
    elif model_name.startswith("gpt"):
        return ChatOpenAI(model=model_name)
    else:
        raise ValueError(f"Unsupported model: {model_name}")
```

**Acceptance Criteria**:
- [ ] Works with Claude API
- [ ] Works with OpenAI API
- [ ] Model selection via environment variable
- [ ] Clear error messages for missing API keys

### FR3: Task Orchestration Loop

**Description**: Single-tool-per-turn execution loop with state management.

**Virtual Tools**: Our orchestration layer injects two virtual tools that Playwright MCP doesn't provide:
- `complete_task(status, reason)` - Signals task completion (success/failure)
- `request_human_approval(action, reason)` - Explicitly requests human intervention

These are merged with Playwright MCP's tools when sending to the LLM.

**Loop Logic**:
```python
async def run_task(goal: str, service: str, max_turns: int = 20) -> TaskResult:
    config = get_service_config(service)

    # Get initial snapshot
    snapshot = await mcp_client.call_tool("browser_snapshot", {})

    messages = [
        {"role": "system", "content": build_system_prompt(config)},
        {"role": "user", "content": f"Goal: {goal}\n\nCurrent page:\n{snapshot}"}
    ]

    for turn in range(max_turns):
        response = await llm.invoke(messages, tools=mcp_tools)

        if not response.tool_calls:
            messages.append({"role": "user", "content": "Call a tool or complete_task."})
            continue

        tool_call = response.tool_calls[0]  # Single tool per turn

        # Check for human checkpoint BEFORE execution
        if config.requires_checkpoint(tool_call, snapshot):
            approved = await request_human_approval(tool_call, snapshot)
            if not approved:
                return TaskResult(success=False, reason="human_rejected")

        # Execute via MCP
        result = await mcp_client.call_tool(tool_call.name, tool_call.args)

        # Add to conversation
        messages.append({"role": "assistant", "tool_calls": [tool_call]})
        messages.append({"role": "tool", "content": result})

        # Check completion
        if tool_call.name == "complete_task":
            verified = config.verify_completion(result)
            return TaskResult(success=verified, turns=turn + 1)

    return TaskResult(success=False, reason="max_turns_exceeded")
```

**Acceptance Criteria**:
- [ ] Executes single tool per turn
- [ ] Maintains conversation history
- [ ] Enforces max turns limit
- [ ] Returns structured TaskResult

### FR4: Human Checkpoint System

**Description**: Server-enforced approval for irreversible actions.

**Checkpoint Triggers** (service-specific):

> **Note**: The code below is **pseudocode**. Actual implementation will adapt to Playwright MCP's snapshot format once verified in Phase 1 POC. The snapshot format will be logged and parsed during POC.

```python
# Pseudocode - actual format TBD based on Playwright MCP output
CHECKPOINT_CONDITIONS = {
    "netflix": [
        # Before clicking final cancel button
        # Approach: Search snapshot text/elements for "finish cancel" keywords
        lambda tool, snapshot: (
            tool.name == "browser_click" and
            contains_text(snapshot, "finish cancel")
        ),
        # Before any "confirm" action on cancel page
        # Approach: Check URL contains "cancel" and action targets "confirm"
        lambda tool, snapshot: (
            contains_text(snapshot, "cancel", field="url") and
            "confirm" in tool.args.get("element", "").lower()
        ),
    ]
}
```

**User Interaction**:
```
⚠️  Human approval required

About to: Click "Finish Cancellation" button
Page: https://www.netflix.com/cancelplan/confirm
Screenshot: [displayed inline or saved to file]

Approve? [y/N]:
```

**Acceptance Criteria**:
- [ ] Checkpoints trigger before sensitive actions
- [ ] User sees screenshot and action description
- [ ] Rejection stops the task gracefully
- [ ] Checkpoints are configurable per service

### FR5: Service Configuration

**Description**: Per-service settings for checkpoints and completion.

**Netflix Configuration**:
```python
@dataclass
class ServiceConfig:
    name: str
    initial_url: str
    goal_template: str
    checkpoint_conditions: list[Callable]
    success_indicators: list[Callable]
    failure_indicators: list[Callable]
    system_prompt_addition: str = ""

NETFLIX_CONFIG = ServiceConfig(
    name="netflix",
    initial_url="https://www.netflix.com/account",
    goal_template="Cancel the Netflix subscription. Navigate to cancellation, complete the flow, confirm when you see the cancellation confirmed page.",
    checkpoint_conditions=[
        lambda tool, snap: "finish cancel" in str(snap).lower(),
    ],
    success_indicators=[
        lambda snap: "cancelled" in snap.get("page", {}).get("title", "").lower(),
    ],
    failure_indicators=[
        lambda snap: "error" in snap.get("page", {}).get("url", ""),
    ],
    system_prompt_addition="Netflix may show retention offers. Decline them and proceed with cancellation.",
)
```

**Acceptance Criteria**:
- [ ] Netflix service config complete
- [ ] Configs are easy to add for new services
- [ ] Configs are testable in isolation

### FR6: Authentication Handling

**Description**: Handle service login before automation begins.

**Strategy**: Browser launches with persistent user profile (not incognito). User's saved credentials/sessions are available.

**Options**:
1. **Pre-logged-in profile** (recommended): User logs into service manually once. Browser profile saves session. Subsequent runs reuse session.
2. **Login checkpoint**: If login page detected, automation pauses for human to complete login manually, then resumes.

**Playwright MCP Profile Mode**:
```bash
# Run with persistent profile (default in Playwright MCP)
npx @playwright/mcp@latest
# Profile stored in ~/.playwright-mcp/
```

**Edge Cases** (handled via checkpoint):
- 2FA prompts → Checkpoint pauses for human to complete
- CAPTCHA challenges → Checkpoint pauses for human to solve
- Session expiry mid-task → Checkpoint for re-authentication

**Acceptance Criteria**:
- [ ] Browser uses persistent profile by default
- [ ] Login checkpoint pauses if auth page detected
- [ ] 2FA/CAPTCHA triggers checkpoint (not automated)
- [ ] Session persists across runs

### FR7: CLI Interface

**Description**: Simple command-line interface for end users.

**Commands**:
```bash
# Basic usage
subterminator cancel netflix

# With explicit API key
ANTHROPIC_API_KEY=sk-ant-... subterminator cancel netflix

# With model selection
subterminator cancel netflix --model gpt-4o

# Dry run (show what would happen)
subterminator cancel netflix --dry-run

# Verbose mode
subterminator cancel netflix -v
```

**Acceptance Criteria**:
- [ ] Single command to run cancellation
- [ ] Clear error messages for missing dependencies
- [ ] Progress feedback during execution
- [ ] Final success/failure summary

---

## Non-Functional Requirements

### NFR1: Minimal Dependencies
- Python 3.10+
- mcp-use or mcp SDK (MCP client)
- langchain-anthropic or langchain-openai (LLM)
- Node.js (for npx to run Playwright MCP)

### NFR2: Installation Simplicity
```bash
pip install subterminator
# OR
pipx install subterminator

# Playwright MCP installed automatically on first run via npx
```

### NFR3: Error Messages
- Clear message if API key missing
- Clear message if Playwright MCP fails to start
- Actionable suggestions for common errors

### NFR4: Testability
- Service configs testable without browser
- Orchestration loop testable with mock MCP client
- Integration tests with real MCP server

---

## Implementation Approach

### Phase 1: Proof of Concept (3-5 hours)
1. Connect to Playwright MCP using mcp-use (or official SDK if issues)
2. Run a simple navigation task with Claude
3. Log and document actual snapshot format
4. Verify tool execution works end-to-end

**Go/No-Go Criteria**: POC succeeds if within 5 hours we can:
1. Connect to Playwright MCP and list available tools
2. Execute `browser_snapshot` and get valid output
3. Execute `browser_navigate` + `browser_click` sequence

If ANY of these fail after 5 hours:
- Switch to official MCP SDK (if mcp-use issue)
- Try browser-use instead (if Playwright MCP issue)
- Revisit approach entirely (if fundamental blockers)

### Phase 2: Core Orchestration (5-8 hours)
1. Build task runner with single-tool loop
2. Implement virtual tools (complete_task, request_human_approval)
3. Add human checkpoint system
4. Add completion verification
5. Handle errors gracefully

### Phase 3: Service Integration (3-4 hours)
1. Netflix service config with real checkpoint conditions
2. CLI interface with progress feedback
3. Authentication/profile handling
4. Error messages and recovery

### Phase 4: Polish (2-3 hours)
1. Documentation
2. Installation instructions
3. Edge case handling

**Total: 13-20 hours** (vs 50+ hours for original PRD)

**Note**: Estimates include 50% buffer for integration debugging. If mcp-use works smoothly, closer to 13 hours. If SDK fallback needed, closer to 20 hours.

---

## Comparison: Original vs Revised Approach

| Aspect | Original PRD (Feature 007) | Revised Approach |
|--------|---------------------------|------------------|
| Tasks | 52 implementation tasks | ~15 tasks |
| Browser tools | Build 7 custom tools | Reuse Playwright MCP's 15+ tools |
| Element refs | Custom registry | Use Playwright's ref system |
| Snapshots | Custom format + pruning | Use Playwright's accessibility tree |
| MCP protocol | Direct API (not MCP) | Full MCP client |
| Model support | Claude only | Any LangChain model |
| Code to write | ~3000 LOC | ~500 LOC |
| Dependencies | Custom everything | Leverage existing libraries |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Playwright MCP doesn't meet needs | Low | High | browser-use and DevTools MCP as fallbacks |
| mcp-use has bugs | Medium | Medium | Can use official SDK directly |
| LangChain abstraction too heavy | Low | Low | Direct API calls as fallback |
| npx/Node.js requirement annoying | Medium | Low | Document clearly, consider bundling |

---

## Success Metrics

| Metric | Target | Definition | Measurement |
|--------|--------|------------|-------------|
| Netflix cancel success rate | >80% | Task ends with AI calling `complete_task(success)` AND user confirms account shows "cancelled" | 10 manual test runs on real Netflix accounts |
| Time to implement | <20 hours | Phase 1-4 complete with working CLI | Calendar time tracking |
| Lines of new code | <1000 | Excluding tests and configs | `wc -l src/subterminator/mcp_orchestrator/*.py` |
| User setup time | <10 minutes | Fresh machine, Python installed, to first successful run | Timed on test machine |

**Baseline**: No current baseline for MCP approach. Existing agent.py implementation has unknown success rate (not systematically measured).

---

## References

- [Playwright MCP](https://github.com/microsoft/playwright-mcp) - Microsoft's browser MCP
- [mcp-use](https://github.com/mcp-use/mcp-use) - MCP client library
- [browser-use](https://docs.browser-use.com) - Browser automation library
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Official client
- [Build an MCP Client](https://modelcontextprotocol.io/docs/develop/build-client) - Official docs
