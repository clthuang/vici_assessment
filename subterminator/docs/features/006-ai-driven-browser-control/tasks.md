# Tasks: AI-Driven Browser Control

**Feature ID**: 006
**Created**: 2026-02-05

## Summary

- **Total Tasks**: 48
- **Phases**: 5
- **Parallel Groups**: 8

---

## Phase 1: Data Structures

**File**: `src/subterminator/core/protocols.py`
**Dependencies**: None

### Parallel Group 1A: Test File Setup

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 1.1 | Create `/Users/terry/projects/vici_assessment/tests/unit/test_dataclasses.py` with imports: `import pytest`, `from subterminator.core.protocols import ActionRecord, ErrorRecord, TargetStrategy, ActionPlan, AgentContext, ExecutionResult, ValidationResult, State`. No fixtures needed. Note: State is defined in protocols.py, not states.py. | 5m | [ ] | - |

### Parallel Group 1B: Write Failing Tests (RED)

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 1.2 | Write `test_action_record_creation()`: create ActionRecord("click", "Cancel button", True, "2026-02-05T12:00:00Z"), assert action_type=="click". Write `test_action_record_to_dict()`: assert to_dict() returns {"action": "click", "target": "Cancel button", "success": True, "time": "2026-02-05T12:00:00Z"}. Note: timestamp is str type, no format validation required. | 5m | [ ] | 1.1 |
| 1.3 | Write `test_error_record_creation()`: create ErrorRecord("click", "ElementNotFound", "Selector not found", "css", "2026-02-05T12:00:00Z"), assert error_type=="ElementNotFound". Write `test_error_record_to_dict()`: assert to_dict()["strategy"]=="css". | 5m | [ ] | 1.1 |
| 1.4 | Write `test_target_strategy_css_requires_selector()`: `with pytest.raises(ValueError): TargetStrategy(method="css")`. Also test valid: `TargetStrategy(method="css", css_selector="#btn")`. | 5m | [ ] | 1.1 |
| 1.5 | Write `test_target_strategy_aria_requires_role()`: `with pytest.raises(ValueError): TargetStrategy(method="aria")`. Write `test_target_strategy_aria_name_optional()`: valid with only aria_role, assert aria_name is None. | 5m | [ ] | 1.1 |
| 1.6 | Write `test_target_strategy_text_requires_content()`: raises ValueError if method="text" without text_content. Write `test_target_strategy_coordinates_requires_tuple()`: raises ValueError if method="coordinates" without coordinates. Write `test_target_strategy_describe()`: assert describe() returns "CSS: #btn" for css, "ARIA: role=button name='Submit'" for aria (with quoted name), "Text: Click here" for text, "Coordinates: (100, 200)" for coordinates. | 5m | [ ] | 1.1 |
| 1.7 | Write `test_action_plan_max_fallbacks()`: create with 4 fallbacks, expect ValueError (max 3). Write `test_action_plan_confidence_range()`: confidence=1.5 raises ValueError. | 5m | [ ] | 1.1 |
| 1.8 | Write `test_action_plan_fill_requires_value()`: action_type="fill" without value raises ValueError. Write `test_action_plan_all_targets()`: verify returns [primary] + fallbacks. | 5m | [ ] | 1.1 |
| 1.9 | Write `test_agent_context_to_prompt_context()`: create AgentContext with mock data, assert output contains sections: "URL:", "Viewport:", "Scroll:", "ACCESSIBILITY TREE:", "HTML SNIPPET:", "PREVIOUS ACTIONS:", "ERRORS:" per design.md lines 1255-1270. | 5m | [ ] | 1.1 |

### Sequential Group 1C: Implement (GREEN)

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 1.10 | In `protocols.py`, add after existing imports (line ~10): `from dataclasses import dataclass, field`. Add `@dataclass(frozen=True) class ActionRecord` with fields: action_type:str, target_description:str, success:bool, timestamp:str. Add `def to_dict(self)->dict` returning {"action": self.action_type, "target": self.target_description, "success": self.success, "time": self.timestamp}. | 5m | [ ] | 1.2 |
| 1.11 | In `protocols.py`, add `@dataclass(frozen=True) class ErrorRecord` with fields: action_type:str, error_type:str, error_message:str, strategy_attempted:str, timestamp:str. Add `def to_dict(self)->dict` returning {"action": self.action_type, "error": self.error_type, "message": self.error_message, "strategy": self.strategy_attempted, "time": self.timestamp}. | 5m | [ ] | 1.3 |
| 1.12 | In `protocols.py`, add `@dataclass class TargetStrategy` with: method:Literal["css","aria","text","coordinates"], css_selector:str\|None=None, aria_role:str\|None=None, aria_name:str\|None=None, text_content:str\|None=None, coordinates:tuple[int,int]\|None=None. Add `__post_init__` validation: if method=="css" and not css_selector: raise ValueError; if method=="aria" and not aria_role: raise ValueError; if method=="text" and not text_content: raise ValueError; if method=="coordinates" and not coordinates: raise ValueError. Add `def describe(self)->str`: return f"CSS: {self.css_selector}" for css, f"ARIA: role={self.aria_role} name='{self.aria_name}'" for aria (with quoted name), f"Text: {self.text_content}" for text, f"Coordinates: {self.coordinates}" for coordinates. | 10m | [ ] | 1.4, 1.5, 1.6 |
| 1.13 | In `protocols.py`, add `@dataclass class ActionPlan` with: action_type:Literal["click","fill","select"], primary_target:TargetStrategy, fallback_targets:list[TargetStrategy]=field(default_factory=list), value:str\|None=None, reasoning:str="", confidence:float=0.0, expected_state:State\|None=None. Add `__post_init__` validation: if len(fallback_targets)>3: raise ValueError("max 3 fallbacks"); if not 0<=confidence<=1: raise ValueError; if action_type in ("fill","select") and not value: raise ValueError. Add `def all_targets(self)->list[TargetStrategy]: return [self.primary_target] + self.fallback_targets`. | 10m | [ ] | 1.7, 1.8, 1.12 |
| 1.14 | In `protocols.py`, add `@dataclass class AgentContext` with: screenshot:bytes, accessibility_tree:str, html_snippet:str, url:str, visible_text:str, previous_actions:list[ActionRecord], error_history:list[ErrorRecord], viewport_size:tuple[int,int], scroll_position:tuple[int,int]. Add `def to_prompt_context(self)->str` returning formatted string with sections: URL:, Viewport:, Scroll:, ACCESSIBILITY TREE:, HTML SNIPPET:, PREVIOUS ACTIONS:, ERRORS: matching design.md lines 1255-1270. | 10m | [ ] | 1.9, 1.10, 1.11 |
| 1.15 | In `protocols.py`, add `@dataclass class ExecutionResult` (success:bool, action_plan:ActionPlan, strategy_used:TargetStrategy\|None=None, error:str\|None=None, screenshot_after:bytes\|None=None, elapsed_ms:int=0). Add `@dataclass class ValidationResult` (success:bool, expected_state:State, actual_state:State, confidence:float, message:str). | 5m | [ ] | 1.13 |
| 1.16 | Update `protocols.py` `__all__` list to include: ActionRecord, ErrorRecord, TargetStrategy, ActionPlan, AgentContext, ExecutionResult, ValidationResult. In `src/subterminator/core/__init__.py`, add import: `from subterminator.core.protocols import (ActionRecord, ErrorRecord, TargetStrategy, ActionPlan, AgentContext, ExecutionResult, ValidationResult)` after existing protocol imports and add these to the `__all__` list. | 5m | [ ] | 1.15 |
| 1.17 | Run `uv run pytest tests/unit/test_dataclasses.py -v`. Expect 12+ tests to pass. If any fail, debug before proceeding. Also run `uv run pytest tests/unit/test_protocols.py -v` to verify existing tests still pass. | 5m | [ ] | 1.16 |

---

## Phase 2: BrowserProtocol Extensions

**Files**: `src/subterminator/core/browser.py`, `src/subterminator/core/protocols.py`
**Dependencies**: Phase 1 complete

### Sequential Group 2A: Baseline Verification

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 2.1 | Run `uv run pytest tests/unit/test_browser.py tests/unit/test_protocols.py -v`. Record test count. All must pass before proceeding. | 5m | [ ] | 1.17 |

### Parallel Group 2B: Write Failing Tests (RED) - Using Mocks

**Note:** All tests use mocks consistent with existing test_browser.py patterns. No real browser launches.

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 2.2 | In `test_browser.py`, write `test_browser_evaluate()`: create PlaywrightBrowser, set `browser._page = AsyncMock()`, configure `mock_page.evaluate = AsyncMock(return_value="hello")`, call `await browser.evaluate("document.getElementById('test').textContent")`, assert result=="hello", assert mock_page.evaluate.called_once_with the script string. | 10m | [ ] | 2.1 |
| 2.3 | Write `test_browser_accessibility_tree()`: set `browser._page = AsyncMock()`. Set up accessibility mock: `mock_accessibility = MagicMock(); mock_accessibility.snapshot = AsyncMock(return_value={"role": "button", "name": "Click me"}); mock_page.accessibility = mock_accessibility`. Call `await browser.accessibility_tree()`, assert "button" in tree.lower(). Tree should be JSON string. | 10m | [ ] | 2.1 |
| 2.4 | Write `test_browser_accessibility_tree_null()`: set `browser._page = AsyncMock()`. Set up accessibility mock: `mock_accessibility = MagicMock(); mock_accessibility.snapshot = AsyncMock(return_value=None); mock_page.accessibility = mock_accessibility`. Verify accessibility_tree() returns "{}" (empty) not crash. Tests D5 null handling. | 5m | [ ] | 2.1 |
| 2.5 | Write `test_browser_click_coordinates_negative_raises()`: create PlaywrightBrowser, set `browser._page = AsyncMock()`, call `with pytest.raises(ValueError): await browser.click_coordinates(-1, -1)`. | 5m | [ ] | 2.1 |
| 2.6 | Write `test_browser_click_by_role()`: add `from playwright.async_api import TimeoutError as PlaywrightTimeoutError` to test imports. Set `browser._page = AsyncMock()`, create `mock_locator = AsyncMock()`, set `mock_page.get_by_role = MagicMock(return_value=mock_locator)`, call `await browser.click_by_role("button", "Submit")`, assert mock_page.get_by_role.called_with("button", name="Submit"). For ElementNotFound case: make `mock_locator.click = AsyncMock(side_effect=PlaywrightTimeoutError("timeout"))`, expect ElementNotFound raised. | 10m | [ ] | 2.1 |
| 2.7 | Write `test_browser_click_by_text()`: set `browser._page = AsyncMock()`, create `mock_locator = AsyncMock()`, set `mock_page.get_by_text = MagicMock(return_value=mock_locator)`, call `await browser.click_by_text("Cancel Membership")`, should not raise. | 5m | [ ] | 2.1 |
| 2.8 | Write `test_browser_viewport_size()`: set `browser._page = AsyncMock()`, set `mock_page.viewport_size = {"width": 1280, "height": 720}`, call `await browser.viewport_size()`, assert result == (1280, 720). | 5m | [ ] | 2.1 |
| 2.9 | Write `test_browser_scroll_position()`: set `browser._page = AsyncMock()`, set `mock_page.evaluate = AsyncMock(return_value=[0, 0])`, call `await browser.scroll_position()`, assert result == (0, 0). | 5m | [ ] | 2.1 |
| 2.10 | Write `test_browser_scroll_to()`: set `browser._page = AsyncMock()`, set `mock_page.evaluate = AsyncMock()`, call `await browser.scroll_to(0, 100)`, assert mock_page.evaluate.called_once_with("window.scrollTo(0, 100)"). | 5m | [ ] | 2.1 |
| 2.11 | Write `test_playwright_browser_supports_methods()`: no launch needed, create PlaywrightBrowser(), assert `browser.supports_accessibility_tree()==True`, `supports_coordinate_clicking()==True`, `supports_text_clicking()==True`. | 5m | [ ] | 2.1 |

### Sequential Group 2C: Implement (GREEN)

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 2.12 | In `browser.py` PlaywrightBrowser class, add: `async def evaluate(self, script: str) -> Any: if not self._page: raise RuntimeError("Browser not launched"); return await self._page.evaluate(script)`. The import `from typing import Any` already exists at line 11. | 5m | [ ] | 2.2 |
| 2.13 | In `browser.py`, add `def _prune_a11y_tree(self, node: dict | None, depth: int = 0, max_depth: int = 5) -> dict | None`. Implementation: return None if depth>max_depth or node is None; create pruned = {"role": node.get("role", ""), "name": node.get("name", "")[:100]}; if "children" in node: pruned["children"] = [self._prune_a11y_tree(c, depth+1, max_depth) for c in node["children"] if c]; filter None from children list; return pruned. | 10m | [ ] | 2.3 |
| 2.14 | In `browser.py`, add `import json` after line 10 (from pathlib import Path). Add `async def accessibility_tree(self) -> str`. Implementation per D5: if not self._page: raise RuntimeError("Browser not launched"); snapshot = await self._page.accessibility.snapshot(); if snapshot is None: return "{}"; pruned = self._prune_a11y_tree(snapshot, max_depth=5); return json.dumps(pruned, indent=2). | 5m | [ ] | 2.3, 2.4, 2.13 |
| 2.15 | In `browser.py`, add `async def click_coordinates(self, x: int, y: int) -> None`. Check self._page, raise ValueError if x<0 or y<0 with message f"Coordinates must be non-negative: ({x}, {y})", call `await self._page.mouse.click(x, y)`. | 5m | [ ] | 2.5 |
| 2.16 | In `browser.py`, add `from typing import cast` to imports at line 11 (combine with existing Any import: `from typing import Any, cast`). Add `from playwright.async_api import TimeoutError as PlaywrightTimeoutError` to imports. Add `async def click_by_role(self, role: str, name: str | None = None) -> None`. Check self._page, try: `locator = self._page.get_by_role(cast(Any, role), name=name); await locator.click(timeout=3000)`. Except PlaywrightTimeoutError: raise ElementNotFound(f"No element with role={role} name='{name}'"). | 5m | [ ] | 2.6 |
| 2.17 | In `browser.py`, add `async def click_by_text(self, text: str, exact: bool = False) -> None`. Same pattern as click_by_role: check self._page, try: `locator = self._page.get_by_text(text, exact=exact); await locator.click(timeout=3000)`. Except PlaywrightTimeoutError: raise ElementNotFound(f"No element with text '{text}'"). | 5m | [ ] | 2.7 |
| 2.18 | In `browser.py`, add `async def viewport_size(self) -> tuple[int, int]`. Check self._page, return `(self._page.viewport_size["width"], self._page.viewport_size["height"]) if self._page.viewport_size else (1280, 720)`. | 5m | [ ] | 2.8 |
| 2.19 | In `browser.py`, add `async def scroll_position(self) -> tuple[int, int]`. Check self._page, call `pos = await self._page.evaluate("[window.scrollX, window.scrollY]")`, return `(int(pos[0]), int(pos[1]))`. | 5m | [ ] | 2.9 |
| 2.20 | In `browser.py`, add `async def scroll_to(self, x: int, y: int) -> None`. Check self._page, call `await self._page.evaluate(f"window.scrollTo({x}, {y})")`. | 5m | [ ] | 2.10 |
| 2.21 | In `browser.py`, add `def supports_accessibility_tree(self) -> bool: return True`, `def supports_coordinate_clicking(self) -> bool: return True`, `def supports_text_clicking(self) -> bool: return True`. | 5m | [ ] | 2.11 |
| 2.22 | In `protocols.py` BrowserProtocol class, add type hints for new methods as documentation. These are optional - Protocol uses duck typing. Include docstrings per design.md Section 7.2 lines 1371-1475. Methods: evaluate, accessibility_tree, click_coordinates, click_by_role, click_by_text, viewport_size, scroll_position, scroll_to, supports_accessibility_tree, supports_coordinate_clicking, supports_text_clicking. | 5m | [ ] | 2.21 |
| 2.23 | Run `uv run pytest tests/unit/test_browser.py -v`. Expect all new tests + existing tests to pass (count from 2.1 + ~10 new). | 5m | [ ] | 2.22 |

---

## Phase 3: ClaudeActionPlanner

**File**: `src/subterminator/core/ai.py`
**Dependencies**: Phase 1 complete (can run in parallel with Phase 2)

### Sequential Group 3A: Test Fixtures

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 3.1 | In `tests/unit/test_ai.py`, add imports: `from unittest.mock import Mock, AsyncMock, MagicMock`. Add helper: `def create_mock_tool_response(data: dict = None, confidence: float = 0.9) -> MagicMock`. Default data if None: {"state": "ACCOUNT_ACTIVE", "action_type": "click", "targets": [{"method": "css", "css": "#btn"}], "reasoning": "test", "expected_next_state": "RETENTION_OFFER"}. Create block with explicit attributes: `block = MagicMock(); block.type = "tool_use"; block.name = "browser_action"; block.input = {**data, "confidence": confidence}`. Return MagicMock with `content=[block]`. | 10m | [ ] | 1.17 |
| 3.2 | Add helper: `def create_test_context() -> AgentContext`. Add import `from subterminator.core.protocols import AgentContext`. Return AgentContext(screenshot=b"PNG", accessibility_tree="{}", html_snippet="<button>Test</button>", url="https://test.com", visible_text="Test", previous_actions=[], error_history=[], viewport_size=(1280,720), scroll_position=(0,0)). | 5m | [ ] | 1.17 |

### Parallel Group 3B: Write Failing Tests (RED)

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 3.3 | Write `test_tool_schema_has_required_fields()`: assert ClaudeActionPlanner.TOOL_SCHEMA["name"]=="browser_action", assert "state", "action_type", "targets" in schema["input_schema"]["properties"]. | 5m | [ ] | 3.1 |
| 3.4 | Write `test_parse_tool_response_valid_single_target()`: create planner with api_key="test-key", call _parse_tool_response with mock having 1 target (create_mock_tool_response with targets=[{"method":"css","css":"#btn"}]), assert plan.primary_target.method=="css", assert len(plan.fallback_targets)==0. | 5m | [ ] | 3.1 |
| 3.5 | Write `test_parse_tool_response_multiple_targets()`: mock with 3 targets [{"method":"css","css":"#btn"},{"method":"text","text":"Click"},{"method":"aria","aria_role":"button"}], assert primary_target is first, assert len(fallback_targets)==2. | 5m | [ ] | 3.1 |
| 3.6 | Write `test_plan_action_retries_on_low_confidence(mocker)`: patch `anthropic.Anthropic` to return mock client, patch client.messages.create with side_effect=[create_mock_tool_response(confidence=0.4), create_mock_tool_response(confidence=0.8)], call plan_action, assert client.messages.create.call_count==2, assert final plan.confidence>=0.6. | 10m | [ ] | 3.1, 3.2 |
| 3.7 | Write `test_plan_action_raises_on_persistent_low_confidence(mocker)`: patch client.messages.create with side_effect=[create_mock_tool_response(confidence=0.3), create_mock_tool_response(confidence=0.4)], expect `pytest.raises(StateDetectionError)` from `subterminator.utils.exceptions`. | 5m | [ ] | 3.1, 3.2 |

### Sequential Group 3C: Implement (GREEN)

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 3.8 | In `ai.py`, add class constant `TOOL_SCHEMA: dict[str, Any]` to ClaudeActionPlanner as a class attribute at top of class definition. Copy verbatim from design.md Section 4.4 lines 611-671. Ensure "targets" is an array of objects with properties: method, css, aria_role, aria_name, text, coordinates. Add `from typing import Any` to imports. | 10m | [ ] | 3.3 |
| 3.9 | Add class constant `SYSTEM_PROMPT: str` from design.md Section 7.4 lines 1762-1779. | 5m | [ ] | 3.8 |
| 3.10 | Add class constant `SELF_CORRECT_PROMPT: str` from design.md Section 3.4 lines 387-408 and Section 7.4 lines 1781-1797. | 5m | [ ] | 3.9 |
| 3.11 | Add `def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514", timeout: int = 30)`. Add `import anthropic` to imports. Create self.client = anthropic.Anthropic(api_key=api_key), self.model = model, self.timeout = timeout. | 5m | [ ] | 3.10 |
| 3.12 | Add `def _build_messages(self, context: AgentContext, goal: str, error_context: str | None) -> list[dict]`. Add `import base64` to imports. Build: messages = [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(context.screenshot).decode()}}, {"type": "text", "text": context.to_prompt_context() + "\n\nGOAL: " + goal + ("\n\nPREVIOUS ERROR: " + error_context if error_context else "")}]}]. Return messages. | 10m | [ ] | 3.11 |
| 3.13 | Add `def _parse_tool_response(self, response) -> ActionPlan`. Add import `from subterminator.core.protocols import TargetStrategy, ActionPlan, State` and `from subterminator.utils.exceptions import StateDetectionError`. Note: State is in protocols.py. Find tool_use block: `tool_block = next((b for b in response.content if b.type == "tool_use" and b.name == "browser_action"), None)`; if not tool_block: raise StateDetectionError("No valid tool_use"); data = tool_block.input; Parse targets: for each t in data["targets"]: create TargetStrategy(method=t["method"], css_selector=t.get("css"), aria_role=t.get("aria_role"), aria_name=t.get("aria_name"), text_content=t.get("text"), coordinates=tuple(t["coordinates"]) if t.get("coordinates") else None). For expected_state: `state_name = data.get("expected_next_state"); expected_state = State[state_name] if state_name else None` (wrapped in try/except KeyError to fallback to None). Return ActionPlan(action_type=data["action_type"], primary_target=targets[0], fallback_targets=targets[1:4], reasoning=data.get("reasoning",""), confidence=data.get("confidence",0.0), expected_state=expected_state). | 15m | [ ] | 3.4, 3.5, 3.12 |
| 3.14 | Add `def _call_claude_sync(self, context: AgentContext, goal: str, error_context: str | None, require_high_confidence: bool) -> ActionPlan`. Build messages via _build_messages. If require_high_confidence: append to last text content: "\n\nIMPORTANT: You MUST provide confidence >= 0.6 or explain why impossible.". Call response = self.client.messages.create(model=self.model, max_tokens=1024, system=self.SYSTEM_PROMPT, messages=messages, tools=[self.TOOL_SCHEMA], tool_choice={"type":"tool","name":"browser_action"}). Return self._parse_tool_response(response). | 10m | [ ] | 3.13 |
| 3.15 | Add `import asyncio` to imports. Add `async def plan_action(self, context: AgentContext, goal: str, error_context: str | None = None) -> ActionPlan`. Implementation per design.md Section 4.5 lines 725-786: plan = await asyncio.to_thread(self._call_claude_sync, context, goal, error_context, False); if plan.confidence >= 0.6: return plan; plan = await asyncio.to_thread(self._call_claude_sync, context, goal, error_context, True); if plan.confidence < 0.6: raise StateDetectionError(f"Persistent low confidence: {plan.confidence}"); return plan. | 10m | [ ] | 3.6, 3.7, 3.14 |
| 3.16 | Run `uv run pytest tests/unit/test_ai.py -v -k ClaudeActionPlanner`. Expect 5+ tests to pass. | 5m | [ ] | 3.15 |

---

## Phase 4: AIBrowserAgent

**File**: `src/subterminator/core/agent.py` (NEW)
**Dependencies**: Phase 2 and Phase 3 complete

### Sequential Group 4A: Test File Setup

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 4.1 | Create `tests/unit/test_agent.py` with imports: `import pytest`, `from unittest.mock import Mock, AsyncMock, MagicMock`, `from subterminator.core.agent import AIBrowserAgent`, `from subterminator.core.protocols import AgentContext, ActionPlan, TargetStrategy, ExecutionResult, ValidationResult, State, AIInterpretation`, `from subterminator.utils.exceptions import ElementNotFound`. Note: State is in protocols.py, not states.py. Add helper functions: (1) `def create_mock_browser() -> AsyncMock`: return browser with click=AsyncMock(), screenshot=AsyncMock(return_value=b"PNG"), url=AsyncMock(return_value="https://test.com"), text_content=AsyncMock(return_value="Test"), evaluate=AsyncMock(return_value=[]), accessibility_tree=AsyncMock(return_value="{}"), click_by_role=AsyncMock(), click_by_text=AsyncMock(), click_coordinates=AsyncMock(), viewport_size=AsyncMock(return_value=(1280,720)), scroll_position=AsyncMock(return_value=(0,0)), supports_accessibility_tree=Mock(return_value=True). (2) `def create_mock_planner(plan=None) -> Mock`: return Mock with plan_action=AsyncMock(return_value=plan). (3) `def create_mock_heuristic(state: State) -> Mock`: return Mock with interpret=Mock(return_value=AIInterpretation(state=state, confidence=0.9, reasoning="test", actions=[])). (4) `def create_test_plan() -> ActionPlan`: return ActionPlan(action_type="click", primary_target=TargetStrategy(method="css", css_selector="#btn"), fallback_targets=[], confidence=0.9, expected_state=State.RETENTION_OFFER). | 10m | [ ] | 2.23, 3.16 |

### Parallel Group 4B: Write Failing Tests (RED)

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 4.2 | Write `test_agent_init_validates_max_retries()`: `with pytest.raises(ValueError): AIBrowserAgent(create_mock_browser(), create_mock_planner(), create_mock_heuristic(State.UNKNOWN), max_retries=0)`. Also test max_retries=1 works (no exception). | 5m | [ ] | 4.1 |
| 4.3 | Write `test_agent_perceive_returns_context()`: create agent with mocks, call `context = await agent.perceive()`, assert isinstance(context, AgentContext), assert context.screenshot == b"PNG", assert context.url == "https://test.com". | 10m | [ ] | 4.1 |
| 4.4 | Write `test_agent_perceive_handles_a11y_failure()`: mock_browser = create_mock_browser(); mock_browser.supports_accessibility_tree = Mock(return_value=False); create agent, call perceive(), assert context.accessibility_tree == "{}". | 5m | [ ] | 4.1 |
| 4.5 | Write `test_agent_extract_html_snippet()`: mock_browser = create_mock_browser(); mock_browser.evaluate = AsyncMock(return_value=["<button>Click</button>"]); create agent, call `snippet = await agent._extract_html_snippet()`, assert "<button>" in snippet. | 5m | [ ] | 4.1 |
| 4.6 | Write `test_agent_execute_tries_fallbacks()`: mock_browser = create_mock_browser(); mock_browser.click = AsyncMock(side_effect=ElementNotFound("not found")); mock_browser.click_by_text = AsyncMock(); plan = ActionPlan(action_type="click", primary_target=TargetStrategy(method="css", css_selector="#btn"), fallback_targets=[TargetStrategy(method="text", text_content="Button")], confidence=0.9); create agent, call `result = await agent.execute(plan)`, assert result.success==True, assert result.strategy_used.method=="text". | 10m | [ ] | 4.1 |
| 4.7 | Write `test_agent_execute_uses_click_by_role_for_aria()`: mock_browser = create_mock_browser(); plan = ActionPlan(action_type="click", primary_target=TargetStrategy(method="aria", aria_role="button", aria_name="Submit"), fallback_targets=[], confidence=0.9, expected_state=State.RETENTION_OFFER); create agent, call execute(plan); `mock_browser.click_by_role.assert_called_with("button", "Submit")`. | 5m | [ ] | 4.1 |
| 4.8 | Write `test_agent_validate_success()`: mock_heuristic = create_mock_heuristic(State.RETENTION_OFFER); create agent; plan = create_test_plan(); plan.expected_state = State.RETENTION_OFFER; result = ExecutionResult(success=True, action_plan=plan); validation = await agent.validate(result); assert validation.success==True; assert validation.actual_state==State.RETENTION_OFFER. | 5m | [ ] | 4.1 |
| 4.9 | Write `test_agent_validate_accepts_state_progression()`: mock_heuristic = create_mock_heuristic(State.EXIT_SURVEY); create agent; plan = create_test_plan(); plan.expected_state = State.RETENTION_OFFER; result = ExecutionResult(success=True, action_plan=plan); validation = await agent.validate(result); assert validation.success==True (acceptable skip - EXIT_SURVEY is valid progression from RETENTION_OFFER). | 5m | [ ] | 4.1 |
| 4.10 | Write `test_agent_handle_state_full_loop()`: mock_browser = create_mock_browser(); mock_planner = create_mock_planner(plan=create_test_plan()); mock_heuristic = create_mock_heuristic(State.RETENTION_OFFER); agent = AIBrowserAgent(mock_browser, mock_planner, mock_heuristic); next_state = await agent.handle_state(State.ACCOUNT_ACTIVE); assert next_state == State.RETENTION_OFFER; assert mock_planner.plan_action.called. | 10m | [ ] | 4.1 |
| 4.11 | Write `test_agent_self_corrects_on_failure()`: mock_browser = create_mock_browser(); mock_browser.click = AsyncMock(side_effect=[ElementNotFound(""), ElementNotFound(""), None]); mock_planner = create_mock_planner(plan=create_test_plan()); mock_heuristic = create_mock_heuristic(State.RETENTION_OFFER); agent = AIBrowserAgent(mock_browser, mock_planner, mock_heuristic, max_retries=3); await agent.handle_state(State.ACCOUNT_ACTIVE); assert mock_planner.plan_action.call_count >= 2. | 10m | [ ] | 4.1 |
| 4.12 | Write `test_agent_returns_unknown_after_max_retries()`: mock_browser = create_mock_browser(); mock_browser.click = AsyncMock(side_effect=ElementNotFound("always fails")); mock_browser.click_by_text = AsyncMock(side_effect=ElementNotFound("always fails")); mock_browser.click_by_role = AsyncMock(side_effect=ElementNotFound("always fails")); mock_browser.click_coordinates = AsyncMock(side_effect=ElementNotFound("always fails")); plan with all strategies; mock_planner returns plan; agent = AIBrowserAgent(..., max_retries=3); result = await agent.handle_state(State.ACCOUNT_ACTIVE); assert result == State.UNKNOWN. | 5m | [ ] | 4.1 |

### Sequential Group 4C: Implement (GREEN)

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 4.13 | Create `/Users/terry/projects/vici_assessment/src/subterminator/core/agent.py`. Add imports: `import asyncio`, `import time`, `import logging`, `from typing import Any`, `from subterminator.core.protocols import State, AgentContext, ActionPlan, TargetStrategy, ExecutionResult, ValidationResult, ActionRecord, ErrorRecord`, `from subterminator.utils.exceptions import ElementNotFound`. Note: State is in protocols.py, not states.py. Add logger = logging.getLogger(__name__). Add STATE_TRANSITIONS dict as module constant: `STATE_TRANSITIONS: dict[State, tuple[str, State | None]] = {State.ACCOUNT_ACTIVE: ("Click the cancel membership link", State.RETENTION_OFFER), State.RETENTION_OFFER: ("Decline the retention offer", State.EXIT_SURVEY), State.EXIT_SURVEY: ("Complete or skip the exit survey", State.FINAL_CONFIRMATION), State.FINAL_CONFIRMATION: ("Confirm the cancellation", State.COMPLETE), State.THIRD_PARTY_BILLING: ("Identify third-party billing provider", None), State.ACCOUNT_CANCELLED: ("Verify cancellation status", State.COMPLETE), State.UNKNOWN: ("Analyze page and take appropriate action", None)}`. | 10m | [ ] | 4.2 |
| 4.14 | Add `class AIBrowserAgent` with `def __init__(self, browser, planner, heuristic, max_retries: int = 3)`. Validate: if max_retries < 1: raise ValueError("max_retries must be >= 1"). Store self.browser = browser, self.planner = planner, self.heuristic = heuristic, self.max_retries = max_retries. Init self._action_history: list[ActionRecord] = [], self._error_history: list[ErrorRecord] = []. | 5m | [ ] | 4.13 |
| 4.15 | Add `async def _gather_accessibility_tree(self) -> str`. Implementation: if not self.browser.supports_accessibility_tree(): return "{}". Try: return await self.browser.accessibility_tree(). Except (NotImplementedError, AttributeError, Exception) as e: logger.warning(f"accessibility_tree failed: {e}"); return "{}". | 5m | [ ] | 4.3, 4.4, 4.14 |
| 4.16 | Add `async def _extract_html_snippet(self) -> str`. JavaScript implementation (full script from design.md Section 4.3 lines 559-591): `script = """() => { const vw = window.innerWidth; const vh = window.innerHeight; const selectors = 'button, a, input, select, [role="button"], [role="link"], [role="checkbox"], [role="textbox"]'; const elements = document.querySelectorAll(selectors); const results = []; for (const el of elements) { const rect = el.getBoundingClientRect(); if (rect.bottom > 0 && rect.top < vh && rect.right > 0 && rect.left < vw && rect.width > 0 && rect.height > 0) { let html = el.outerHTML; if (html.length > 500) { const tag = el.tagName.toLowerCase(); const attrs = []; for (const attr of ['id', 'class', 'name', 'type', 'role', 'aria-label', 'href']) { if (el.hasAttribute(attr)) { attrs.push(attr + '="' + el.getAttribute(attr) + '"'); } } html = '<' + tag + ' ' + attrs.join(' ') + '>' + (el.textContent?.slice(0, 100) || '') + '...truncated</' + tag + '>'; } results.push(html); } } return results.slice(0, 50); }"""`. Wrap in try: elements = await self.browser.evaluate(script); snippet = "\n".join(elements); return snippet[:5000] if len(snippet) > 5000 else snippet. Except Exception as e: logger.warning(f"HTML snippet extraction failed: {e}"); return "". | 10m | [ ] | 4.5, 4.15 |
| 4.17 | Add `async def perceive(self) -> AgentContext`. Implementation: try: screenshot = await self.browser.screenshot(); a11y_tree = await self._gather_accessibility_tree(); html_snippet = await self._extract_html_snippet(); url = await self.browser.url(); visible_text = await self.browser.text_content(); viewport = await self.browser.viewport_size(); scroll = await self.browser.scroll_position(); return AgentContext(screenshot=screenshot, accessibility_tree=a11y_tree, html_snippet=html_snippet, url=url, visible_text=visible_text, previous_actions=list(self._action_history), error_history=list(self._error_history), viewport_size=viewport, scroll_position=scroll). Except Exception as e: logger.error(f"perceive failed: {e}"); return AgentContext(screenshot=b"", accessibility_tree="{}", html_snippet="", url="", visible_text="", previous_actions=[], error_history=[], viewport_size=(0,0), scroll_position=(0,0)). | 10m | [ ] | 4.16 |
| 4.18 | Add `async def plan(self, context: AgentContext, goal: str) -> ActionPlan`. Return `await self.planner.plan_action(context, goal)`. | 5m | [ ] | 4.17 |
| 4.19 | Add `async def _try_target_strategy(self, strategy: TargetStrategy, action_type: str, value: str | None) -> bool`. Implementation: try: if strategy.method == "css": await self.browser.click(strategy.css_selector); elif strategy.method == "aria": await self.browser.click_by_role(strategy.aria_role, strategy.aria_name); elif strategy.method == "text": await self.browser.click_by_text(strategy.text_content); elif strategy.method == "coordinates": await self.browser.click_coordinates(*strategy.coordinates). If action_type == "fill": await self.browser.fill(strategy.css_selector, value). Return True. Except ElementNotFound as e: logger.debug(f"Strategy {strategy.describe()} failed: {e}"); return False. Except Exception as e: logger.warning(f"Unexpected error with {strategy.describe()}: {e}"); return False. | 15m | [ ] | 4.6, 4.7, 4.18 |
| 4.20 | Add `async def execute(self, plan: ActionPlan) -> ExecutionResult`. Implementation: start_time = time.time(); for strategy in plan.all_targets(): success = await self._try_target_strategy(strategy, plan.action_type, plan.value); if success: await asyncio.sleep(1); screenshot = await self.browser.screenshot(); elapsed = int((time.time() - start_time) * 1000); self._record_action(ActionRecord(plan.action_type, strategy.describe(), True, time.strftime("%Y-%m-%dT%H:%M:%SZ"))); return ExecutionResult(success=True, action_plan=plan, strategy_used=strategy, screenshot_after=screenshot, elapsed_ms=elapsed). elapsed = int((time.time() - start_time) * 1000); self._record_error(ErrorRecord(plan.action_type, "AllStrategiesFailed", "All targeting strategies failed", "all", time.strftime("%Y-%m-%dT%H:%M:%SZ"))); return ExecutionResult(success=False, action_plan=plan, error="All strategies failed", elapsed_ms=elapsed). | 10m | [ ] | 4.19 |
| 4.21 | Add `VALID_PROGRESSIONS: dict[State, set[State]] = {State.RETENTION_OFFER: {State.EXIT_SURVEY, State.FINAL_CONFIRMATION}, State.EXIT_SURVEY: {State.FINAL_CONFIRMATION, State.COMPLETE}, State.FINAL_CONFIRMATION: {State.COMPLETE}}` as class constant. Add `def _is_valid_state_progression(self, expected: State, actual: State) -> bool`. Implementation: if expected == actual: return True; if expected in self.VALID_PROGRESSIONS: return actual in self.VALID_PROGRESSIONS[expected]; return False. | 5m | [ ] | 4.8, 4.9 |
| 4.22 | Add `async def validate(self, result: ExecutionResult) -> ValidationResult`. Implementation: url = await self.browser.url(); text = await self.browser.text_content(); interpretation = self.heuristic.interpret(url, text); actual_state = interpretation.state; expected_state = result.action_plan.expected_state or State.UNKNOWN; success = self._is_valid_state_progression(expected_state, actual_state); message = f"Expected {expected_state.name}, got {actual_state.name}" + (" (valid progression)" if success and expected_state != actual_state else ""); return ValidationResult(success=success, expected_state=expected_state, actual_state=actual_state, confidence=interpretation.confidence, message=message). | 10m | [ ] | 4.21 |
| 4.23 | Add `async def self_correct(self, context: AgentContext, failure: ValidationResult, attempt: int) -> ActionPlan`. Implementation: error_context = f"Attempt {attempt} failed. Expected state: {failure.expected_state.name}, Actual state: {failure.actual_state.name}. Message: {failure.message}. You MUST try a DIFFERENT approach this time."; goal, _ = STATE_TRANSITIONS.get(failure.expected_state, ("Recover from error", None)); return await self.planner.plan_action(context, goal, error_context). | 10m | [ ] | 4.11, 4.22 |
| 4.24 | Add `async def handle_state(self, state: State) -> State`. Implementation: goal, expected_next = STATE_TRANSITIONS.get(state, ("Analyze and act", None)); for attempt in range(1, self.max_retries + 1): context = await self.perceive(); if attempt == 1: plan = await self.plan(context, goal); else: plan = await self.self_correct(context, validation, attempt); result = await self.execute(plan); if not result.success: continue; validation = await self.validate(result); if validation.success: return validation.actual_state. logger.warning(f"Max retries ({self.max_retries}) exceeded for state {state.name}"); return State.UNKNOWN. | 15m | [ ] | 4.10, 4.23 |
| 4.25 | Add `def clear_history(self) -> None`: self._action_history.clear(); self._error_history.clear(). Add `def _record_action(self, action: ActionRecord) -> None`: self._action_history.append(action). Add `def _record_error(self, error: ErrorRecord) -> None`: self._error_history.append(error). | 5m | [ ] | 4.24 |
| 4.26 | Run `uv run pytest tests/unit/test_agent.py -v`. Expect 12+ tests to pass. | 5m | [ ] | 4.25 |

---

## Phase 5: Engine Integration

**File**: `src/subterminator/core/engine.py`
**Dependencies**: Phase 4 complete

### Sequential Group 5A: Baseline Verification

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 5.1 | Run `uv run pytest tests/unit/test_engine.py -v`. Record test count. All must pass. | 5m | [ ] | 4.26 |

### Parallel Group 5B: Write Failing Tests (RED)

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 5.2 | Write `test_engine_without_agent_uses_hardcoded()`: create engine with agent=None, mock service/browser/heuristic, verify existing hardcoded behavior works (state transitions occur). | 10m | [ ] | 5.1 |
| 5.3 | Write `test_engine_with_agent_delegates()`: mock_agent = Mock(); mock_agent.handle_state = AsyncMock(return_value=State.RETENTION_OFFER); mock_agent.clear_history = Mock(); create engine with agent=mock_agent. Call `await engine._handle_state(State.ACCOUNT_ACTIVE)` directly to test. Assert `mock_agent.handle_state.assert_called_with(State.ACCOUNT_ACTIVE)`. | 10m | [ ] | 5.1 |
| 5.4 | Write `test_engine_start_state_ignores_agent()`: mock_agent = Mock(); mock_agent.handle_state = AsyncMock(); create engine with agent=mock_agent. Call `await engine._handle_state(State.START)` directly. Assert `mock_agent.handle_state.assert_not_called()`. | 5m | [ ] | 5.1 |
| 5.5 | Write `test_engine_login_required_ignores_agent()`: mock_agent = Mock(); mock_agent.handle_state = AsyncMock(); create engine with agent=mock_agent. Call `await engine._handle_state(State.LOGIN_REQUIRED)` directly. Assert `mock_agent.handle_state.assert_not_called()`. | 5m | [ ] | 5.1 |
| 5.6 | Write `test_engine_falls_back_on_api_error()`: add `import anthropic` to test file. mock_agent = Mock(); mock_agent.handle_state = AsyncMock(side_effect=anthropic.APIStatusError(message="timeout", response=MagicMock(status_code=500), body=None)). Create engine with agent=mock_agent. Patch `_hardcoded_handle` to track calls. Call `await engine._handle_state(State.ACCOUNT_ACTIVE)`. Assert engine doesn't crash, assert _hardcoded_handle was called as fallback. | 10m | [ ] | 5.1 |
| 5.7 | Write `test_engine_final_confirmation_requires_checkpoint()`: mock_agent = Mock(); mock_agent.handle_state = AsyncMock(return_value=State.COMPLETE); mock_agent.clear_history = Mock(); create engine with agent=mock_agent, dry_run=False; mock _human_checkpoint; trigger FINAL_CONFIRMATION handling; assert _human_checkpoint called before agent.handle_state. | 5m | [ ] | 5.1 |

### Sequential Group 5C: Implement (GREEN)

| ID | Task | Est | Done | Dependencies |
|----|------|-----|------|--------------|
| 5.8 | In `engine.py`, add TYPE_CHECKING import: `from typing import TYPE_CHECKING`. Add conditional import: `if TYPE_CHECKING: from subterminator.core.agent import AIBrowserAgent`. In CancellationEngine.__init__, add parameter `agent: "AIBrowserAgent | None" = None` at end of parameter list. Store `self.agent = agent`. | 5m | [ ] | 5.2 |
| 5.9 | In __init__, add `self._action_history_cleared = False` after existing attribute initializations. | 5m | [ ] | 5.8 |
| 5.10 | Identify the existing `_handle_state()` method. Extract the match/case block that handles ACCOUNT_ACTIVE, ACCOUNT_CANCELLED, THIRD_PARTY_BILLING, RETENTION_OFFER, EXIT_SURVEY, FINAL_CONFIRMATION, UNKNOWN into a new method `async def _hardcoded_handle(self, state: State) -> State`. Keep START and LOGIN_REQUIRED handling in _handle_state. | 5m | [ ] | 5.9 |
| 5.11 | Rewrite `_handle_state()`: Add `import anthropic` to engine.py imports. if state in (State.START, State.LOGIN_REQUIRED): <use existing handlers>. Else: if self.agent: try: return await self._ai_driven_handle(state); except (anthropic.APIStatusError, anthropic.APIConnectionError) as e: logger.warning(f"AI agent failed, falling back to hardcoded: {e}"). Return await self._hardcoded_handle(state). Note: Use specific exception classes APIStatusError and APIConnectionError, not base APIError. | 10m | [ ] | 5.3, 5.4, 5.5, 5.10 |
| 5.12 | Add `async def _ai_driven_handle(self, state: State) -> State`. Implementation: if state == State.FINAL_CONFIRMATION and not self.dry_run: await self._human_checkpoint("CONFIRM", self.config.confirm_timeout if hasattr(self, 'config') else 30). If not self._action_history_cleared: self.agent.clear_history(); self._action_history_cleared = True. Return await self.agent.handle_state(state). | 10m | [ ] | 5.6, 5.7, 5.11 |
| 5.13 | In `run()` method, add `self._action_history_cleared = False` at the start of the method to reset per run. | 5m | [ ] | 5.12 |
| 5.14 | Run `uv run pytest tests/unit/test_engine.py -v`. Expect all tests (original + 6 new) to pass. | 5m | [ ] | 5.13 |
| 5.15 | Run `uv run pytest tests/ -v`. Expect full test suite to pass. Record final count. | 5m | [ ] | 5.14 |

---

## Dependency Graph

```
Phase 1 ────┬──────> Phase 2 ────────┐
            │                        │
            └──────> Phase 3 ────────┼──> Phase 4 ──> Phase 5
                                     │
                    (parallel)       │
                                     ▼
                                  Phase 4
```

## Acceptance Criteria Summary

| Phase | Success Criteria |
|-------|-----------------|
| 1 | 12+ dataclass tests pass, `__all__` updated in protocols.py and core/__init__.py |
| 2 | All new browser tests pass, baseline tests unchanged |
| 3 | 5+ ClaudeActionPlanner tests pass with mocks |
| 4 | 12+ AIBrowserAgent tests pass with mocks |
| 5 | Engine tests pass (original + 6 new), full suite passes |
