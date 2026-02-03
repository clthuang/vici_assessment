# PRD: Bring Your Own Model (BYOM) - LLM Abstraction Layer

**Status:** Brainstorm
**Created:** 2026-02-03
**Author:** Claude (Brainstorm Agent)

---

## Problem Statement

SubTerminator currently uses a hardcoded Claude Vision API integration for AI-powered page detection. This creates several limitations:

1. **Cost** - Claude API calls cost money, even for simple page detection
2. **Privacy** - Screenshots are sent to Anthropic's servers
3. **Offline** - Cannot work without internet connection
4. **Lock-in** - No way to use alternative models (OpenAI, Gemini, local Ollama)
5. **Experimentation** - Cannot easily test which model works best for page detection

## Proposed Solution

Implement a **model-agnostic LLM abstraction layer** that allows users to:

1. **Choose their provider** - OpenAI, Anthropic, Google Gemini, Ollama (local)
2. **Configure via environment/config** - Simple provider switching
3. **Use local models for privacy** - Ollama for sensitive data
4. **Fallback handling** - Automatic failover between providers
5. **Cost optimization** - Use cheaper/local models when sufficient

---

## User Stories

### US-1: Use Local Ollama Model
**As a** privacy-conscious user
**I want** to use a local Ollama model for page detection
**So that** my screenshots never leave my machine

**Acceptance Criteria:**
- Can configure `SUBTERMINATOR_LLM_PROVIDER=ollama`
- Ollama vision model (llama3.2-vision) is used for detection
- No external API calls when using Ollama
- Clear error if Ollama not running

### US-2: Use OpenAI Instead of Claude
**As a** developer with OpenAI credits
**I want** to use GPT-4 Vision for page detection
**So that** I can use my existing API quota

**Acceptance Criteria:**
- Can configure `SUBTERMINATOR_LLM_PROVIDER=openai`
- GPT-4 Vision is used with identical detection logic
- Same prompt template works across providers
- API key configured via `OPENAI_API_KEY`

### US-3: Automatic Fallback
**As a** user
**I want** automatic fallback to heuristics if my LLM is unavailable
**So that** the tool still works when my API is down

**Acceptance Criteria:**
- If configured LLM fails, fall back to heuristic detection
- User is warned about fallback
- No crash or error on LLM unavailability

### US-4: Model Selection Per-Task
**As a** power user
**I want** to configure different models for different scenarios
**So that** I can optimize cost vs accuracy

**Acceptance Criteria:**
- Can configure primary and fallback models
- Can specify model for "simple" vs "complex" detection
- Configuration via YAML file or environment variables

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SubTerminator                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────┐    ┌──────────────────────────┐   │
│  │ HeuristicInter- │    │   LLMInterpreter         │   │
│  │ preter          │    │   (New Abstraction)      │   │
│  └────────┬────────┘    └────────────┬─────────────┘   │
│           │                          │                  │
│           │              ┌───────────┴───────────┐     │
│           │              │      LiteLLM          │     │
│           │              │   (Provider Router)   │     │
│           │              └───────────┬───────────┘     │
│           │                          │                  │
│           │          ┌───────────────┼───────────────┐ │
│           │          │               │               │  │
│           ▼          ▼               ▼               ▼  │
│      ┌────────┐ ┌────────┐    ┌──────────┐   ┌───────┐ │
│      │ Rules  │ │Anthropic│   │  OpenAI  │   │Ollama │ │
│      │(Fast)  │ │ Claude  │   │  GPT-4V  │   │(Local)│ │
│      └────────┘ └────────┘    └──────────┘   └───────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. LiteLLM Integration

**Why LiteLLM:**
- 100+ provider support with OpenAI-compatible API
- Built-in vision/multimodal support
- Automatic error mapping
- Low latency overhead (claimed 8ms P95 per [LiteLLM benchmarks](https://docs.litellm.ai/docs/proxy/benchmarks))
- Excellent Ollama integration

**Installation:**
```toml
# pyproject.toml
dependencies = [
    "litellm>=1.40",
    # ... existing deps
]
```

#### 2. New LLMInterpreter Class

```python
# src/subterminator/core/llm.py

from litellm import completion, supports_vision
import base64
import json
import re
import logging
from typing import Optional
from .protocols import AIInterpretation, State
from .ai import HeuristicInterpreter  # For fallback

logger = logging.getLogger(__name__)

class LLMInterpreter:
    """Provider-agnostic LLM interpreter using LiteLLM."""

    # Prompt template - ASSUMPTION: needs validation across providers
    # Known to work: Claude. Needs testing: GPT-4V, Gemini, Ollama vision models
    PROMPT_TEMPLATE = """Analyze this screenshot of a subscription cancellation flow.

Determine which state this page represents:
- LOGIN_REQUIRED: Login form is shown
- ACCOUNT_ACTIVE: Account page with active subscription
- ACCOUNT_CANCELLED: Subscription already cancelled
- THIRD_PARTY_BILLING: Billed through Apple/Google/other
- RETENTION_OFFER: Discount or "stay with us" offer
- EXIT_SURVEY: "Why are you leaving?" survey
- FINAL_CONFIRMATION: Final "Finish Cancellation" button
- COMPLETE: Cancellation confirmed
- FAILED: Error page
- UNKNOWN: Cannot determine

Respond in JSON format only (no markdown, no explanation):
{"state": "<STATE>", "confidence": <0.0-1.0>, "reasoning": "...", "actions": [...]}
"""

    def __init__(
        self,
        model: str = "anthropic/claude-sonnet-4-20250514",
        fallback_model: Optional[str] = None,
        heuristic_fallback: Optional[HeuristicInterpreter] = None,
        api_base: Optional[str] = None,
    ):
        self.model = model
        self.fallback_model = fallback_model
        self.heuristic_fallback = heuristic_fallback
        self.api_base = api_base

        # Validate model supports vision
        if not supports_vision(model):
            raise ValueError(f"Model {model} does not support vision")

    async def interpret(self, screenshot: bytes, url: str = "", text: str = "") -> AIInterpretation:
        """Interpret page state from screenshot.

        Args:
            screenshot: PNG image bytes
            url: Current page URL (for heuristic fallback)
            text: Page text content (for heuristic fallback)
        """
        image_b64 = base64.b64encode(screenshot).decode("utf-8")

        try:
            response = await self._call_model(self.model, image_b64)
            return self._parse_response(response)
        except Exception as e:
            logger.warning(f"Primary model {self.model} failed: {e}")

            # Try fallback model
            if self.fallback_model:
                try:
                    response = await self._call_model(self.fallback_model, image_b64)
                    return self._parse_response(response)
                except Exception as e2:
                    logger.warning(f"Fallback model {self.fallback_model} failed: {e2}")

            # Fall back to heuristics
            if self.heuristic_fallback:
                logger.info("Falling back to heuristic detection")
                return self.heuristic_fallback.interpret(url, text)

            raise

    async def _call_model(self, model: str, image_b64: str) -> str:
        """Call LLM with vision content."""
        response = completion(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": self.PROMPT_TEMPLATE},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        }
                    }
                ]
            }],
            max_tokens=500,
            api_base=self.api_base,
        )
        return response.choices[0].message.content

    def _parse_response(self, response: str) -> AIInterpretation:
        """Parse JSON response into AIInterpretation.

        Handles common LLM output variations:
        - Raw JSON
        - JSON wrapped in ```json ... ``` markdown
        - JSON with extra text before/after
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
        else:
            # Try to find raw JSON object
            json_match = re.search(r'\{[^{}]*"state"[^{}]*\}', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)

        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response[:200]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

        return AIInterpretation(
            state=State[data["state"]],
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            actions=data.get("actions", [])
        )
```

#### 3. Configuration

**Environment Variables:**
```bash
# Provider selection (default: anthropic)
SUBTERMINATOR_LLM_PROVIDER=ollama

# Model override (optional)
SUBTERMINATOR_LLM_MODEL=ollama/llama3.2-vision

# Ollama-specific
OLLAMA_API_BASE=http://localhost:11434

# Provider API keys (standard names)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

**YAML Config (Advanced):**
```yaml
# ~/.subterminator/config.yaml
llm:
  primary:
    provider: ollama
    model: llama3.2-vision
    api_base: http://localhost:11434

  fallback:
    provider: anthropic
    model: claude-sonnet-4-20250514

  # Use cheaper model for simple detection
  simple_detection:
    provider: ollama
    model: llama3.2:1b
```

#### 4. Provider Model Mapping

| Provider | Model ID (LiteLLM format) | Vision Support | Page Detection Tested |
|----------|---------------------------|----------------|----------------------|
| Anthropic | `anthropic/claude-sonnet-4-20250514` | Yes | **Yes** (current implementation) |
| OpenAI | `openai/gpt-4-vision-preview` | Yes | **NEEDS VALIDATION** |
| Google | `gemini/gemini-1.5-flash` | Yes | **NEEDS VALIDATION** |
| Ollama | `ollama/llama3.2-vision` | Yes | **NEEDS VALIDATION** |
| Ollama | `ollama/llava:13b` | Yes | **NEEDS VALIDATION** |

> **IMPORTANT:** Only Claude has been validated for the page detection task. Before shipping multi-provider support, we must test each provider against a set of sample screenshots to verify:
> 1. Prompt compatibility (same prompt produces usable output)
> 2. JSON output reliability (consistent formatting)
> 3. Detection accuracy (correct state identification)

#### 4.1 Validation Plan (Pre-Implementation Requirement)

Before implementing BYOM, create a validation script:

```python
# scripts/validate_llm_providers.py
"""
Test each provider against known page screenshots.
Run: uv run python scripts/validate_llm_providers.py
"""
import asyncio
from pathlib import Path

SAMPLE_SCREENSHOTS = {
    "login": "tests/fixtures/screenshots/login_page.png",
    "account_active": "tests/fixtures/screenshots/account_active.png",
    "retention_offer": "tests/fixtures/screenshots/retention_offer.png",
    # ... more samples
}

PROVIDERS_TO_TEST = [
    "anthropic/claude-sonnet-4-20250514",
    "openai/gpt-4-vision-preview",
    "gemini/gemini-1.5-flash",
    "ollama/llama3.2-vision",
]

async def main():
    for provider in PROVIDERS_TO_TEST:
        print(f"\n=== Testing {provider} ===")
        for expected_state, screenshot_path in SAMPLE_SCREENSHOTS.items():
            result = await test_provider(provider, screenshot_path)
            match = "PASS" if result.state.name.lower() == expected_state else "FAIL"
            print(f"  {expected_state}: {match} (got {result.state.name}, conf={result.confidence})")
```

#### 5. Factory Function

```python
# src/subterminator/core/ai.py

def create_interpreter(config: Config) -> AIInterpreterProtocol:
    """Create appropriate interpreter based on config."""
    provider = config.llm_provider

    if provider == "none" or not config.has_llm_config:
        return None  # Heuristics only

    model_map = {
        "anthropic": "anthropic/claude-sonnet-4-20250514",
        "openai": "openai/gpt-4-vision-preview",
        "gemini": "gemini/gemini-1.5-flash",
        "ollama": "ollama/llama3.2-vision",
    }

    model = config.llm_model or model_map.get(provider)

    return LLMInterpreter(
        model=model,
        fallback_model=config.llm_fallback_model,
        api_base=config.llm_api_base,
    )
```

### Migration Path

1. **Phase 1:** Run validation script against all target providers
2. **Phase 2:** Add LiteLLM as optional dependency
3. **Phase 3:** Implement `LLMInterpreter` alongside existing `ClaudeInterpreter`
4. **Phase 4:** Update config to support provider selection (feature flag: `SUBTERMINATOR_USE_LITELLM=1`)
5. **Phase 5:** Validate in production with Claude via LiteLLM (same behavior, different path)
6. **Phase 6:** Enable other providers based on validation results
7. **Phase 7:** Deprecate `ClaudeInterpreter`, migrate to `LLMInterpreter`
8. **Phase 8:** Remove direct anthropic SDK dependency (optional)

**Rollback Strategy:**
- Feature flag `SUBTERMINATOR_USE_LITELLM=0` reverts to ClaudeInterpreter
- Keep ClaudeInterpreter code until Phase 7 is validated in production
- Monitor error rates and detection accuracy during rollout

---

## Dependencies

### New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `litellm` | `>=1.40` | Multi-provider LLM abstraction |

### Optional Dependencies (User's Machine)

| Software | Purpose |
|----------|---------|
| Ollama | Local model execution |
| llama3.2-vision | Local vision model |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Supported providers | 1 (Claude) | 4+ (Claude, GPT, Gemini, Ollama) |
| Local model support | No | Yes (Ollama) |
| Config complexity | Hardcoded | Env vars + YAML |
| API cost for tests | ~$0.01/call | $0 (Ollama) |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LiteLLM adds latency | Low | Claimed 8ms overhead - verify in testing |
| Model accuracy varies | **High** | **Run validation script before enabling provider** |
| Ollama setup complexity | Medium | Document: requires 8GB+ RAM, model pull (~4GB), clear error on missing Ollama |
| LiteLLM maintenance | Low | Well-maintained, 8k+ stars |
| Prompt incompatibility | Medium | Test prompt with each provider; may need provider-specific prompts |
| JSON output varies | Medium | Robust parser with regex extraction and retry logic |

### Ollama Hardware Requirements

Users choosing Ollama should be aware:
- **RAM:** 8GB minimum for llama3.2-vision (16GB recommended)
- **Disk:** ~4GB per vision model
- **CPU/GPU:** GPU optional but dramatically faster
- **First run:** Model download required (~4GB)

Error messages will detect and report:
- Ollama not running: "Cannot connect to Ollama at localhost:11434. Is Ollama running?"
- Model not pulled: "Model 'llama3.2-vision' not found. Run: ollama pull llama3.2-vision"
- OOM: "Ollama ran out of memory. Try a smaller model or increase RAM."

---

## Decisions (Resolved from Open Questions)

1. **Model routing by complexity:** Not in v1. Start simple, add later if needed.
2. **Response caching:** Not in v1. Screenshots are ephemeral, caching adds complexity.
3. **Custom prompts per provider:** Design for it (prompt template configurable), but use same prompt initially. Add provider-specific prompts only if validation shows need.
4. **Minimum Ollama model:** Determined by validation script. llama3.2-vision is the default, but llava:7b may work for simpler pages.

## Open Questions (Remaining)

1. Should we expose model selection in CLI (`--model`) or only via config?
2. Should we log which model was used for debugging/cost tracking?

---

## References

- [LiteLLM GitHub](https://github.com/BerriAI/litellm)
- [LiteLLM Vision Docs](https://docs.litellm.ai/docs/completion/vision)
- [LiteLLM Ollama Integration](https://docs.litellm.ai/docs/providers/ollama)
- [Ollama Vision Models](https://ollama.ai/library?q=vision)
- [LiteLLM Model Fallbacks](https://docs.litellm.ai/docs/tutorials/model_fallbacks)
