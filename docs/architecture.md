# SubTerminator Architecture

This document provides system design diagrams and component descriptions for the SubTerminator codebase.

---

## High-Level Architecture

![High-Level Architecture](images/architecture-high-level.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart TB
    subgraph CLI["CLI Layer"]
        main["main.py<br/>Command Parser"]
        output["output.py<br/>Formatter"]
        prompts["prompts.py<br/>User Input"]
    end

    subgraph Legacy["Legacy Orchestrator (core/)"]
        engine["CancellationEngine<br/>State Machine Driver"]
        states["StateMachine<br/>12 States"]
        heuristic["HeuristicInterpreter<br/>URL/Text Patterns"]
        claude["ClaudeInterpreter<br/>Vision AI"]
        browser["PlaywrightBrowser<br/>Direct Control"]
    end

    subgraph MCP["MCP Orchestrator (mcp_orchestrator/)"]
        runner["TaskRunner<br/>Main Loop"]
        llm["LLMClient<br/>Claude/GPT-4"]
        mcpc["MCPClient<br/>Server Connection"]
        checkpoint["CheckpointHandler<br/>Human Gates"]
        snapshot["SnapshotParser<br/>Page State"]
    end

    subgraph External["External Services"]
        anthropic["Anthropic API"]
        openai["OpenAI API"]
        mcpserver["Playwright MCP<br/>Server (npx)"]
        chromium["Chromium Browser"]
    end

    subgraph Services["Service Configs"]
        netflix["Netflix Config"]
        others["Other Services..."]
    end

    main --> engine
    main --> runner

    engine --> states
    engine --> heuristic
    engine --> claude
    engine --> browser

    runner --> llm
    runner --> mcpc
    runner --> checkpoint
    runner --> snapshot

    heuristic --> netflix
    claude --> anthropic
    browser --> chromium

    llm --> anthropic
    llm --> openai
    mcpc --> mcpserver
    mcpserver --> chromium
    runner --> netflix
```

</details>

---

## MCP Orchestrator Flow

![MCP Orchestrator Flow](images/mcp-orchestrator-flow.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart TD
    Start([Start]) --> Connect["Connect to MCP Server"]
    Connect --> Navigate["Navigate to Initial URL"]
    Navigate --> Snapshot["Get Page Snapshot"]

    Snapshot --> LLM["LLM: Analyze snapshot<br/>Select next tool"]

    LLM --> ToolCheck{Tool called?}

    ToolCheck -->|No| NoActionCount["Increment no_action_count"]
    NoActionCount --> MaxNoAction{count >= 3?}
    MaxNoAction -->|Yes| FailNoAction([Fail: LLM no action])
    MaxNoAction -->|No| PromptLLM["Prompt: Call a tool"]
    PromptLLM --> LLM

    ToolCheck -->|Yes| VirtualCheck{Virtual tool?}

    VirtualCheck -->|complete_task| Verify["Verify completion<br/>via indicators"]
    Verify --> VerifyOK{Verified?}
    VerifyOK -->|Yes| Success([Success])
    VerifyOK -->|No| RetryVerify["Return error to LLM"]
    RetryVerify --> LLM

    VirtualCheck -->|request_human_approval| HumanApproval["Show checkpoint UI"]
    HumanApproval --> Approved{Approved?}
    Approved -->|No| Rejected([Fail: Human rejected])
    Approved -->|Yes| ContinueApproval["Return approval to LLM"]
    ContinueApproval --> LLM

    VirtualCheck -->|No| AuthCheck["Check for auth edge case<br/>(login/captcha/mfa)"]

    AuthCheck --> IsAuth{Auth required?}
    IsAuth -->|Yes| WaitAuth["Wait for user to<br/>complete auth"]
    WaitAuth --> AuthDone{Completed?}
    AuthDone -->|No| Rejected
    AuthDone -->|Yes| RefreshSnapshot["Refresh snapshot"]
    RefreshSnapshot --> LLM

    IsAuth -->|No| CheckpointCheck["Check checkpoint_conditions"]

    CheckpointCheck --> NeedsCheckpoint{Checkpoint?}
    NeedsCheckpoint -->|Yes| RequestApproval["Request approval"]
    RequestApproval --> ApprovedCP{Approved?}
    ApprovedCP -->|No| Rejected
    ApprovedCP -->|Yes| Execute

    NeedsCheckpoint -->|No| Execute["Execute MCP tool"]

    Execute --> UpdateMessages["Add result to<br/>message history"]
    UpdateMessages --> TurnCheck{Turn < max?}
    TurnCheck -->|No| MaxTurns([Fail: Max turns])
    TurnCheck -->|Yes| UpdateSnapshot["Update snapshot<br/>(if navigation tool)"]
    UpdateSnapshot --> LLM
```

</details>

---

## Component Descriptions

### CLI Layer

| Component | File | Responsibility |
|-----------|------|----------------|
| Command Parser | `cli/main.py` | Parse CLI arguments, create components, run orchestrator |
| Output Formatter | `cli/output.py` | Format progress messages, success/failure output |
| User Prompts | `cli/prompts.py` | Interactive service selection, confirmation dialogs |
| Accessibility | `cli/accessibility.py` | Plain mode, non-interactive mode support |

### Legacy Orchestrator (core/)

| Component | File | Responsibility |
|-----------|------|----------------|
| CancellationEngine | `core/engine.py` | Main loop, state handling, detection cascade |
| StateMachine | `core/states.py` | 12 states with explicit transitions |
| HeuristicInterpreter | `core/ai.py` | Fast URL/text pattern matching |
| ClaudeInterpreter | `core/ai.py` | Vision-based page analysis |
| PlaywrightBrowser | `core/browser.py` | Direct browser control with stealth |
| Protocols | `core/protocols.py` | Type definitions (State, BrowserProtocol) |

### MCP Orchestrator (mcp_orchestrator/)

| Component | File | Responsibility |
|-----------|------|----------------|
| TaskRunner | `task_runner.py` | Main loop, virtual tools, turn management |
| LLMClient | `llm_client.py` | Claude/GPT-4 via LangChain, retries |
| MCPClient | `mcp_client.py` | Playwright MCP server subprocess |
| CheckpointHandler | `checkpoint.py` | Auth detection, approval UI |
| SnapshotParser | `snapshot.py` | Parse browser_snapshot to structured data |
| Types | `types.py` | TaskResult, ToolCall, NormalizedSnapshot |
| Exceptions | `exceptions.py` | Custom error types |
| ServiceConfig | `services/base.py` | Service configuration dataclass |
| ServiceRegistry | `services/registry.py` | Service lookup by name |

### Services

| Component | File | Responsibility |
|-----------|------|----------------|
| Netflix (Legacy) | `services/netflix.py` | URLs, selectors, text indicators |
| Netflix (MCP) | `mcp_orchestrator/services/netflix.py` | URLs, predicates, LLM hints |
| Service Registry | `services/registry.py` | Service lookup, validation |
| Mock Server | `services/mock.py` | Local testing server |

### Utilities

| Component | File | Responsibility |
|-----------|------|----------------|
| Config | `utils/config.py` | Environment variable handling |
| Exceptions | `utils/exceptions.py` | Shared exception types |
| Session Logger | `utils/session.py` | Screenshot and log capture |

---

## Data Types

### MCP Orchestrator Types

![Data Types](images/data-types.png)

<details>
<summary>Mermaid source</summary>

```mermaid
classDiagram
    class TaskResult {
        +bool success
        +bool verified
        +TaskReason reason
        +int turns
        +str|None final_url
        +str|None error
    }

    class ToolCall {
        +str id
        +str name
        +dict args
    }

    class NormalizedSnapshot {
        +str url
        +str title
        +str content
        +str|None screenshot_path
    }

    class ServiceConfig {
        +str name
        +str initial_url
        +str goal_template
        +list checkpoint_conditions
        +list success_indicators
        +list failure_indicators
        +list auth_edge_case_detectors
        +str system_prompt_addition
    }

    TaskResult --> TaskReason

    class TaskReason {
        <<enumeration>>
        completed
        human_rejected
        max_turns_exceeded
        llm_no_action
        llm_error
        mcp_error
        verification_failed
    }
```

</details>

---

## Checkpoint Flow

![Checkpoint Flow](images/checkpoint-flow.png)

<details>
<summary>Mermaid source</summary>

```mermaid
sequenceDiagram
    participant LLM
    participant TaskRunner
    participant Checkpoint
    participant User
    participant MCP

    LLM->>TaskRunner: tool_call (e.g., browser_click)

    TaskRunner->>Checkpoint: detect_auth_edge_case(snapshot, config)

    alt Auth Page Detected
        Checkpoint-->>TaskRunner: "login" | "captcha" | "mfa"
        TaskRunner->>Checkpoint: wait_for_auth_completion()
        Checkpoint->>User: "Please complete auth in browser"
        User-->>Checkpoint: Press Enter
        Checkpoint-->>TaskRunner: True (completed)
        TaskRunner->>MCP: browser_snapshot
        Note over TaskRunner: Skip tool, refresh snapshot
    else Normal Page
        Checkpoint-->>TaskRunner: None
        TaskRunner->>Checkpoint: should_checkpoint(tool, snapshot, config)

        alt Checkpoint Triggered
            Checkpoint-->>TaskRunner: True
            TaskRunner->>Checkpoint: request_approval(tool, snapshot)
            Checkpoint->>MCP: browser_take_screenshot
            Checkpoint->>User: Show checkpoint UI
            User-->>Checkpoint: y/N
            Checkpoint-->>TaskRunner: approved (bool)

            alt Rejected
                TaskRunner-->>LLM: TaskResult(human_rejected)
            else Approved
                TaskRunner->>MCP: call_tool(name, args)
            end
        else No Checkpoint
            TaskRunner->>MCP: call_tool(name, args)
        end
    end
```

</details>

---

## Tool Execution

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to URL |
| `browser_click` | Click element by ref |
| `browser_type` | Type into input field |
| `browser_snapshot` | Get page accessibility tree |
| `browser_take_screenshot` | Capture screenshot |

### Virtual Tools

| Tool | Description |
|------|-------------|
| `complete_task` | Signal success or failure |
| `request_human_approval` | Request explicit approval |

---

## Message Flow

![Message Flow](images/message-flow.png)

<details>
<summary>Mermaid source</summary>

```mermaid
sequenceDiagram
    participant System as System Prompt
    participant User as User Messages
    participant Assistant as Assistant Messages
    participant Tool as Tool Results

    Note over System: Service goal + rules

    System->>User: Initial snapshot
    User->>Assistant: LLM responds

    loop Each Turn
        Assistant->>Tool: tool_call
        Tool->>User: tool result
        User->>Assistant: (Updated snapshot if nav tool)
    end

    Assistant->>Tool: complete_task(status, reason)
```

</details>

The message history accumulates:
1. System prompt with goal
2. User message with page snapshot
3. Assistant tool_call
4. Tool result
5. (If navigation) User message with updated snapshot
6. Repeat until complete_task
