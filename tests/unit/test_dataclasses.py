"""Unit tests for AI-driven browser control dataclasses.

Tests cover:
- ActionType enum values and auto-numbering
- BrowserElement dataclass with describe() method
- BrowserAction dataclass for browser commands
- PlannedAction dataclass for AI-planned actions
"""

import pytest

from subterminator.core.protocols import State


class TestActionType:
    """Tests for ActionType enum (Task 1.2)."""

    def test_action_type_has_click(self) -> None:
        """ActionType should have CLICK value."""
        from subterminator.core.protocols import ActionType

        assert hasattr(ActionType, "CLICK")
        assert ActionType.CLICK.name == "CLICK"

    def test_action_type_has_fill(self) -> None:
        """ActionType should have FILL value."""
        from subterminator.core.protocols import ActionType

        assert hasattr(ActionType, "FILL")

    def test_action_type_has_select(self) -> None:
        """ActionType should have SELECT value."""
        from subterminator.core.protocols import ActionType

        assert hasattr(ActionType, "SELECT")

    def test_action_type_has_navigate(self) -> None:
        """ActionType should have NAVIGATE value."""
        from subterminator.core.protocols import ActionType

        assert hasattr(ActionType, "NAVIGATE")

    def test_action_type_has_wait(self) -> None:
        """ActionType should have WAIT value."""
        from subterminator.core.protocols import ActionType

        assert hasattr(ActionType, "WAIT")

    def test_action_type_has_screenshot(self) -> None:
        """ActionType should have SCREENSHOT value."""
        from subterminator.core.protocols import ActionType

        assert hasattr(ActionType, "SCREENSHOT")

    def test_action_type_values_are_unique(self) -> None:
        """All ActionType values should be unique."""
        from subterminator.core.protocols import ActionType

        values = [member.value for member in ActionType]
        assert len(values) == len(set(values))


class TestBrowserElement:
    """Tests for BrowserElement dataclass (Task 1.3-1.4)."""

    def test_browser_element_has_role(self) -> None:
        """BrowserElement should have role field."""
        from subterminator.core.protocols import BrowserElement

        elem = BrowserElement(role="button", name="Submit", selector="#btn")
        assert elem.role == "button"

    def test_browser_element_has_name(self) -> None:
        """BrowserElement should have name field."""
        from subterminator.core.protocols import BrowserElement

        elem = BrowserElement(role="button", name="Submit", selector="#btn")
        assert elem.name == "Submit"

    def test_browser_element_has_selector(self) -> None:
        """BrowserElement should have selector field."""
        from subterminator.core.protocols import BrowserElement

        elem = BrowserElement(role="button", name="Submit", selector="#btn")
        assert elem.selector == "#btn"

    def test_browser_element_has_optional_value(self) -> None:
        """BrowserElement should have optional value field."""
        from subterminator.core.protocols import BrowserElement

        elem = BrowserElement(role="textbox", name="Email", selector="#email", value="test@example.com")
        assert elem.value == "test@example.com"

    def test_browser_element_value_defaults_to_none(self) -> None:
        """BrowserElement value should default to None."""
        from subterminator.core.protocols import BrowserElement

        elem = BrowserElement(role="button", name="Submit", selector="#btn")
        assert elem.value is None

    def test_browser_element_describe_returns_aria_format(self) -> None:
        """describe() should return ARIA format string."""
        from subterminator.core.protocols import BrowserElement

        elem = BrowserElement(role="button", name="Submit", selector="#btn")
        # Format: "ARIA: role=button name='Submit'"
        assert elem.describe() == "ARIA: role=button name='Submit'"

    def test_browser_element_describe_with_link_role(self) -> None:
        """describe() should work with link role."""
        from subterminator.core.protocols import BrowserElement

        elem = BrowserElement(role="link", name="Cancel Membership", selector=".cancel-link")
        assert elem.describe() == "ARIA: role=link name='Cancel Membership'"

    def test_browser_element_describe_with_textbox_role(self) -> None:
        """describe() should work with textbox role."""
        from subterminator.core.protocols import BrowserElement

        elem = BrowserElement(role="textbox", name="Search", selector="#search")
        assert elem.describe() == "ARIA: role=textbox name='Search'"


class TestBrowserAction:
    """Tests for BrowserAction dataclass (Task 1.5-1.6)."""

    def test_browser_action_has_action_type(self) -> None:
        """BrowserAction should have action_type field."""
        from subterminator.core.protocols import ActionType, BrowserAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        assert action.action_type == ActionType.CLICK

    def test_browser_action_has_selector(self) -> None:
        """BrowserAction should have selector field."""
        from subterminator.core.protocols import ActionType, BrowserAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        assert action.selector == "#btn"

    def test_browser_action_has_optional_value(self) -> None:
        """BrowserAction should have optional value field."""
        from subterminator.core.protocols import ActionType, BrowserAction

        action = BrowserAction(action_type=ActionType.FILL, selector="#email", value="test@example.com")
        assert action.value == "test@example.com"

    def test_browser_action_value_defaults_to_none(self) -> None:
        """BrowserAction value should default to None."""
        from subterminator.core.protocols import ActionType, BrowserAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        assert action.value is None

    def test_browser_action_has_optional_timeout(self) -> None:
        """BrowserAction should have optional timeout field."""
        from subterminator.core.protocols import ActionType, BrowserAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn", timeout=10000)
        assert action.timeout == 10000

    def test_browser_action_timeout_defaults_to_none(self) -> None:
        """BrowserAction timeout should default to None."""
        from subterminator.core.protocols import ActionType, BrowserAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        assert action.timeout is None

    def test_browser_action_has_optional_fallback_role(self) -> None:
        """BrowserAction should have optional fallback_role field."""
        from subterminator.core.protocols import ActionType, BrowserAction

        action = BrowserAction(
            action_type=ActionType.CLICK,
            selector="#btn",
            fallback_role=("button", "Submit")
        )
        assert action.fallback_role == ("button", "Submit")

    def test_browser_action_fallback_role_defaults_to_none(self) -> None:
        """BrowserAction fallback_role should default to None."""
        from subterminator.core.protocols import ActionType, BrowserAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        assert action.fallback_role is None


class TestPlannedAction:
    """Tests for PlannedAction dataclass (Task 1.7-1.8)."""

    def test_planned_action_has_state(self) -> None:
        """PlannedAction should have state field."""
        from subterminator.core.protocols import ActionType, BrowserAction, PlannedAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        planned = PlannedAction(state=State.ACCOUNT_ACTIVE, action=action, reasoning="Click cancel")
        assert planned.state == State.ACCOUNT_ACTIVE

    def test_planned_action_has_action(self) -> None:
        """PlannedAction should have action field (BrowserAction)."""
        from subterminator.core.protocols import ActionType, BrowserAction, PlannedAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        planned = PlannedAction(state=State.ACCOUNT_ACTIVE, action=action, reasoning="Click cancel")
        assert planned.action == action

    def test_planned_action_has_reasoning(self) -> None:
        """PlannedAction should have reasoning field."""
        from subterminator.core.protocols import ActionType, BrowserAction, PlannedAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        planned = PlannedAction(state=State.ACCOUNT_ACTIVE, action=action, reasoning="Click cancel button")
        assert planned.reasoning == "Click cancel button"

    def test_planned_action_has_optional_confidence(self) -> None:
        """PlannedAction should have optional confidence field."""
        from subterminator.core.protocols import ActionType, BrowserAction, PlannedAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        planned = PlannedAction(
            state=State.ACCOUNT_ACTIVE,
            action=action,
            reasoning="Click cancel",
            confidence=0.95
        )
        assert planned.confidence == 0.95

    def test_planned_action_confidence_defaults_to_one(self) -> None:
        """PlannedAction confidence should default to 1.0."""
        from subterminator.core.protocols import ActionType, BrowserAction, PlannedAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")
        planned = PlannedAction(state=State.ACCOUNT_ACTIVE, action=action, reasoning="Click cancel")
        assert planned.confidence == 1.0

    def test_planned_action_validates_confidence_range(self) -> None:
        """PlannedAction should validate confidence is between 0.0 and 1.0."""
        from subterminator.core.protocols import ActionType, BrowserAction, PlannedAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")

        with pytest.raises(ValueError, match="confidence must be between"):
            PlannedAction(
                state=State.ACCOUNT_ACTIVE,
                action=action,
                reasoning="Test",
                confidence=1.5
            )

    def test_planned_action_validates_confidence_negative(self) -> None:
        """PlannedAction should reject negative confidence."""
        from subterminator.core.protocols import ActionType, BrowserAction, PlannedAction

        action = BrowserAction(action_type=ActionType.CLICK, selector="#btn")

        with pytest.raises(ValueError, match="confidence must be between"):
            PlannedAction(
                state=State.ACCOUNT_ACTIVE,
                action=action,
                reasoning="Test",
                confidence=-0.1
            )


class TestModuleExports:
    """Tests for module exports (Task 1.9)."""

    def test_action_type_importable_from_protocols(self) -> None:
        """ActionType should be importable from protocols."""
        from subterminator.core.protocols import ActionType

        assert ActionType is not None

    def test_browser_element_importable_from_protocols(self) -> None:
        """BrowserElement should be importable from protocols."""
        from subterminator.core.protocols import BrowserElement

        assert BrowserElement is not None

    def test_browser_action_importable_from_protocols(self) -> None:
        """BrowserAction should be importable from protocols."""
        from subterminator.core.protocols import BrowserAction

        assert BrowserAction is not None

    def test_planned_action_importable_from_protocols(self) -> None:
        """PlannedAction should be importable from protocols."""
        from subterminator.core.protocols import PlannedAction

        assert PlannedAction is not None

    def test_action_type_importable_from_core(self) -> None:
        """ActionType should be importable from subterminator.core."""
        from subterminator.core import ActionType

        assert ActionType is not None

    def test_browser_element_importable_from_core(self) -> None:
        """BrowserElement should be importable from subterminator.core."""
        from subterminator.core import BrowserElement

        assert BrowserElement is not None

    def test_browser_action_importable_from_core(self) -> None:
        """BrowserAction should be importable from subterminator.core."""
        from subterminator.core import BrowserAction

        assert BrowserAction is not None

    def test_planned_action_importable_from_core(self) -> None:
        """PlannedAction should be importable from subterminator.core."""
        from subterminator.core import PlannedAction

        assert PlannedAction is not None


# =============================================================================
# Tests for Spec-Required Dataclasses (Tasks 1.10-1.16)
# =============================================================================


class TestActionRecord:
    """Tests for ActionRecord dataclass (Task 1.10)."""

    def test_action_record_is_frozen(self) -> None:
        """ActionRecord should be immutable (frozen)."""
        from subterminator.core.protocols import ActionRecord

        record = ActionRecord(
            action_type="click",
            target_description="Submit button",
            success=True,
            timestamp="2024-01-01T12:00:00Z",
        )
        with pytest.raises(AttributeError):
            record.action_type = "fill"  # type: ignore[misc]

    def test_action_record_has_action_type(self) -> None:
        """ActionRecord should have action_type field."""
        from subterminator.core.protocols import ActionRecord

        record = ActionRecord(
            action_type="click",
            target_description="Submit button",
            success=True,
            timestamp="2024-01-01T12:00:00Z",
        )
        assert record.action_type == "click"

    def test_action_record_has_target_description(self) -> None:
        """ActionRecord should have target_description field."""
        from subterminator.core.protocols import ActionRecord

        record = ActionRecord(
            action_type="click",
            target_description="Submit button",
            success=True,
            timestamp="2024-01-01T12:00:00Z",
        )
        assert record.target_description == "Submit button"

    def test_action_record_has_success(self) -> None:
        """ActionRecord should have success field."""
        from subterminator.core.protocols import ActionRecord

        record = ActionRecord(
            action_type="click",
            target_description="Submit button",
            success=True,
            timestamp="2024-01-01T12:00:00Z",
        )
        assert record.success is True

    def test_action_record_has_timestamp(self) -> None:
        """ActionRecord should have timestamp field."""
        from subterminator.core.protocols import ActionRecord

        record = ActionRecord(
            action_type="click",
            target_description="Submit button",
            success=True,
            timestamp="2024-01-01T12:00:00Z",
        )
        assert record.timestamp == "2024-01-01T12:00:00Z"

    def test_action_record_to_dict(self) -> None:
        """ActionRecord.to_dict() should return correct dictionary."""
        from subterminator.core.protocols import ActionRecord

        record = ActionRecord(
            action_type="click",
            target_description="Submit button",
            success=True,
            timestamp="2024-01-01T12:00:00Z",
        )
        expected = {
            "action": "click",
            "target": "Submit button",
            "success": True,
            "time": "2024-01-01T12:00:00Z",
        }
        assert record.to_dict() == expected

    def test_action_record_to_dict_failed_action(self) -> None:
        """ActionRecord.to_dict() should work for failed actions."""
        from subterminator.core.protocols import ActionRecord

        record = ActionRecord(
            action_type="fill",
            target_description="Email input",
            success=False,
            timestamp="2024-01-01T12:01:00Z",
        )
        result = record.to_dict()
        assert result["success"] is False
        assert result["action"] == "fill"


class TestErrorRecord:
    """Tests for ErrorRecord dataclass (Task 1.11)."""

    def test_error_record_is_frozen(self) -> None:
        """ErrorRecord should be immutable (frozen)."""
        from subterminator.core.protocols import ErrorRecord

        record = ErrorRecord(
            action_type="click",
            error_type="ElementNotFound",
            error_message="Could not find element",
            strategy_attempted="CSS: #submit-btn",
            timestamp="2024-01-01T12:00:00Z",
        )
        with pytest.raises(AttributeError):
            record.error_type = "Timeout"  # type: ignore[misc]

    def test_error_record_has_action_type(self) -> None:
        """ErrorRecord should have action_type field."""
        from subterminator.core.protocols import ErrorRecord

        record = ErrorRecord(
            action_type="click",
            error_type="ElementNotFound",
            error_message="Could not find element",
            strategy_attempted="CSS: #submit-btn",
            timestamp="2024-01-01T12:00:00Z",
        )
        assert record.action_type == "click"

    def test_error_record_has_error_type(self) -> None:
        """ErrorRecord should have error_type field."""
        from subterminator.core.protocols import ErrorRecord

        record = ErrorRecord(
            action_type="click",
            error_type="ElementNotFound",
            error_message="Could not find element",
            strategy_attempted="CSS: #submit-btn",
            timestamp="2024-01-01T12:00:00Z",
        )
        assert record.error_type == "ElementNotFound"

    def test_error_record_has_error_message(self) -> None:
        """ErrorRecord should have error_message field."""
        from subterminator.core.protocols import ErrorRecord

        record = ErrorRecord(
            action_type="click",
            error_type="ElementNotFound",
            error_message="Could not find element",
            strategy_attempted="CSS: #submit-btn",
            timestamp="2024-01-01T12:00:00Z",
        )
        assert record.error_message == "Could not find element"

    def test_error_record_has_strategy_attempted(self) -> None:
        """ErrorRecord should have strategy_attempted field."""
        from subterminator.core.protocols import ErrorRecord

        record = ErrorRecord(
            action_type="click",
            error_type="ElementNotFound",
            error_message="Could not find element",
            strategy_attempted="CSS: #submit-btn",
            timestamp="2024-01-01T12:00:00Z",
        )
        assert record.strategy_attempted == "CSS: #submit-btn"

    def test_error_record_has_timestamp(self) -> None:
        """ErrorRecord should have timestamp field."""
        from subterminator.core.protocols import ErrorRecord

        record = ErrorRecord(
            action_type="click",
            error_type="ElementNotFound",
            error_message="Could not find element",
            strategy_attempted="CSS: #submit-btn",
            timestamp="2024-01-01T12:00:00Z",
        )
        assert record.timestamp == "2024-01-01T12:00:00Z"

    def test_error_record_to_dict(self) -> None:
        """ErrorRecord.to_dict() should return correct dictionary."""
        from subterminator.core.protocols import ErrorRecord

        record = ErrorRecord(
            action_type="click",
            error_type="ElementNotFound",
            error_message="Could not find element",
            strategy_attempted="CSS: #submit-btn",
            timestamp="2024-01-01T12:00:00Z",
        )
        expected = {
            "action": "click",
            "error": "ElementNotFound",
            "message": "Could not find element",
            "strategy": "CSS: #submit-btn",
            "time": "2024-01-01T12:00:00Z",
        }
        assert record.to_dict() == expected


class TestTargetStrategy:
    """Tests for TargetStrategy dataclass (Task 1.12)."""

    def test_target_strategy_css_method(self) -> None:
        """TargetStrategy with css method should require css_selector."""
        from subterminator.core.protocols import TargetStrategy

        strategy = TargetStrategy(method="css", css_selector="#submit-btn")
        assert strategy.method == "css"
        assert strategy.css_selector == "#submit-btn"

    def test_target_strategy_css_method_missing_selector_raises(self) -> None:
        """TargetStrategy with css method should raise if css_selector missing."""
        from subterminator.core.protocols import TargetStrategy

        with pytest.raises(ValueError, match="css_selector required"):
            TargetStrategy(method="css")

    def test_target_strategy_aria_method(self) -> None:
        """TargetStrategy with aria method should require aria_role."""
        from subterminator.core.protocols import TargetStrategy

        strategy = TargetStrategy(method="aria", aria_role="button", aria_name="Submit")
        assert strategy.method == "aria"
        assert strategy.aria_role == "button"
        assert strategy.aria_name == "Submit"

    def test_target_strategy_aria_method_missing_role_raises(self) -> None:
        """TargetStrategy with aria method should raise if aria_role missing."""
        from subterminator.core.protocols import TargetStrategy

        with pytest.raises(ValueError, match="aria_role required"):
            TargetStrategy(method="aria", aria_name="Submit")

    def test_target_strategy_text_method(self) -> None:
        """TargetStrategy with text method should require text_content."""
        from subterminator.core.protocols import TargetStrategy

        strategy = TargetStrategy(method="text", text_content="Click here")
        assert strategy.method == "text"
        assert strategy.text_content == "Click here"

    def test_target_strategy_text_method_missing_content_raises(self) -> None:
        """TargetStrategy with text method should raise if text_content missing."""
        from subterminator.core.protocols import TargetStrategy

        with pytest.raises(ValueError, match="text_content required"):
            TargetStrategy(method="text")

    def test_target_strategy_coordinates_method(self) -> None:
        """TargetStrategy with coordinates method should require coordinates."""
        from subterminator.core.protocols import TargetStrategy

        strategy = TargetStrategy(method="coordinates", coordinates=(100, 200))
        assert strategy.method == "coordinates"
        assert strategy.coordinates == (100, 200)

    def test_target_strategy_coordinates_method_missing_coords_raises(self) -> None:
        """TargetStrategy with coordinates method should raise if coordinates missing."""
        from subterminator.core.protocols import TargetStrategy

        with pytest.raises(ValueError, match="coordinates required"):
            TargetStrategy(method="coordinates")

    def test_target_strategy_describe_css(self) -> None:
        """describe() should return CSS format for css method."""
        from subterminator.core.protocols import TargetStrategy

        strategy = TargetStrategy(method="css", css_selector="#submit-btn")
        assert strategy.describe() == "CSS: #submit-btn"

    def test_target_strategy_describe_aria(self) -> None:
        """describe() should return ARIA format for aria method."""
        from subterminator.core.protocols import TargetStrategy

        strategy = TargetStrategy(method="aria", aria_role="button", aria_name="Submit")
        assert strategy.describe() == "ARIA: role=button name='Submit'"

    def test_target_strategy_describe_aria_none_name(self) -> None:
        """describe() should handle None aria_name."""
        from subterminator.core.protocols import TargetStrategy

        strategy = TargetStrategy(method="aria", aria_role="button")
        assert strategy.describe() == "ARIA: role=button name='None'"

    def test_target_strategy_describe_text(self) -> None:
        """describe() should return Text format for text method."""
        from subterminator.core.protocols import TargetStrategy

        strategy = TargetStrategy(method="text", text_content="Click here")
        assert strategy.describe() == "Text: Click here"

    def test_target_strategy_describe_coordinates(self) -> None:
        """describe() should return Coordinates format for coordinates method."""
        from subterminator.core.protocols import TargetStrategy

        strategy = TargetStrategy(method="coordinates", coordinates=(100, 200))
        assert strategy.describe() == "Coordinates: (100, 200)"


class TestActionPlan:
    """Tests for ActionPlan dataclass (Task 1.13)."""

    def test_action_plan_click_action(self) -> None:
        """ActionPlan should work for click actions."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#btn")
        plan = ActionPlan(action_type="click", primary_target=target)
        assert plan.action_type == "click"
        assert plan.primary_target == target

    def test_action_plan_fill_requires_value(self) -> None:
        """ActionPlan fill action should require value."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#email")
        with pytest.raises(ValueError, match="value required"):
            ActionPlan(action_type="fill", primary_target=target)

    def test_action_plan_fill_with_value(self) -> None:
        """ActionPlan fill action should work with value."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#email")
        plan = ActionPlan(action_type="fill", primary_target=target, value="test@example.com")
        assert plan.value == "test@example.com"

    def test_action_plan_select_requires_value(self) -> None:
        """ActionPlan select action should require value."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#dropdown")
        with pytest.raises(ValueError, match="value required"):
            ActionPlan(action_type="select", primary_target=target)

    def test_action_plan_select_with_value(self) -> None:
        """ActionPlan select action should work with value."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#dropdown")
        plan = ActionPlan(action_type="select", primary_target=target, value="option1")
        assert plan.value == "option1"

    def test_action_plan_max_three_fallbacks(self) -> None:
        """ActionPlan should allow max 3 fallback targets."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#btn")
        fallbacks = [
            TargetStrategy(method="css", css_selector="#btn1"),
            TargetStrategy(method="css", css_selector="#btn2"),
            TargetStrategy(method="css", css_selector="#btn3"),
            TargetStrategy(method="css", css_selector="#btn4"),
        ]
        with pytest.raises(ValueError, match="max 3 fallbacks"):
            ActionPlan(action_type="click", primary_target=target, fallback_targets=fallbacks)

    def test_action_plan_three_fallbacks_allowed(self) -> None:
        """ActionPlan should allow exactly 3 fallback targets."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#btn")
        fallbacks = [
            TargetStrategy(method="css", css_selector="#btn1"),
            TargetStrategy(method="css", css_selector="#btn2"),
            TargetStrategy(method="css", css_selector="#btn3"),
        ]
        plan = ActionPlan(action_type="click", primary_target=target, fallback_targets=fallbacks)
        assert len(plan.fallback_targets) == 3

    def test_action_plan_confidence_range_valid(self) -> None:
        """ActionPlan should accept confidence between 0 and 1."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#btn")
        plan = ActionPlan(action_type="click", primary_target=target, confidence=0.95)
        assert plan.confidence == 0.95

    def test_action_plan_confidence_too_high(self) -> None:
        """ActionPlan should reject confidence > 1."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#btn")
        with pytest.raises(ValueError, match="confidence must be between"):
            ActionPlan(action_type="click", primary_target=target, confidence=1.5)

    def test_action_plan_confidence_negative(self) -> None:
        """ActionPlan should reject negative confidence."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#btn")
        with pytest.raises(ValueError, match="confidence must be between"):
            ActionPlan(action_type="click", primary_target=target, confidence=-0.1)

    def test_action_plan_all_targets(self) -> None:
        """all_targets() should return primary + fallback targets."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        primary = TargetStrategy(method="css", css_selector="#btn")
        fallback1 = TargetStrategy(method="aria", aria_role="button", aria_name="Submit")
        fallback2 = TargetStrategy(method="text", text_content="Submit")
        plan = ActionPlan(
            action_type="click",
            primary_target=primary,
            fallback_targets=[fallback1, fallback2],
        )
        all_targets = plan.all_targets()
        assert len(all_targets) == 3
        assert all_targets[0] == primary
        assert all_targets[1] == fallback1
        assert all_targets[2] == fallback2

    def test_action_plan_all_targets_no_fallbacks(self) -> None:
        """all_targets() should return just primary when no fallbacks."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        primary = TargetStrategy(method="css", css_selector="#btn")
        plan = ActionPlan(action_type="click", primary_target=primary)
        all_targets = plan.all_targets()
        assert len(all_targets) == 1
        assert all_targets[0] == primary

    def test_action_plan_expected_state(self) -> None:
        """ActionPlan should accept expected_state."""
        from subterminator.core.protocols import ActionPlan, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#btn")
        plan = ActionPlan(
            action_type="click",
            primary_target=target,
            expected_state=State.RETENTION_OFFER,
        )
        assert plan.expected_state == State.RETENTION_OFFER


class TestAgentContext:
    """Tests for AgentContext dataclass (Task 1.14)."""

    def test_agent_context_has_all_fields(self) -> None:
        """AgentContext should have all required fields."""
        from subterminator.core.protocols import ActionRecord, AgentContext, ErrorRecord

        context = AgentContext(
            screenshot=b"fake_png_data",
            accessibility_tree="button: Submit",
            html_snippet="<button>Submit</button>",
            url="https://example.com",
            visible_text="Submit button text",
            previous_actions=[],
            error_history=[],
            viewport_size=(1920, 1080),
            scroll_position=(0, 100),
        )
        assert context.screenshot == b"fake_png_data"
        assert context.accessibility_tree == "button: Submit"
        assert context.html_snippet == "<button>Submit</button>"
        assert context.url == "https://example.com"
        assert context.visible_text == "Submit button text"
        assert context.previous_actions == []
        assert context.error_history == []
        assert context.viewport_size == (1920, 1080)
        assert context.scroll_position == (0, 100)

    def test_agent_context_to_prompt_context_basic(self) -> None:
        """to_prompt_context() should return formatted string."""
        from subterminator.core.protocols import AgentContext

        context = AgentContext(
            screenshot=b"fake_png_data",
            accessibility_tree="button: Submit",
            html_snippet="<button>Submit</button>",
            url="https://example.com",
            visible_text="Submit button text",
            previous_actions=[],
            error_history=[],
            viewport_size=(1920, 1080),
            scroll_position=(0, 100),
        )
        result = context.to_prompt_context()
        assert "URL: https://example.com" in result
        assert "Viewport: 1920x1080" in result
        assert "Scroll: (0, 100)" in result
        assert "ACCESSIBILITY TREE:\nbutton: Submit" in result
        assert "HTML SNIPPET:\n<button>Submit</button>" in result
        assert "PREVIOUS ACTIONS:\nNone" in result
        assert "ERRORS:\nNone" in result

    def test_agent_context_to_prompt_context_with_actions(self) -> None:
        """to_prompt_context() should include previous actions."""
        from subterminator.core.protocols import ActionRecord, AgentContext

        actions = [
            ActionRecord(
                action_type="click",
                target_description="Cancel button",
                success=True,
                timestamp="2024-01-01T12:00:00Z",
            ),
            ActionRecord(
                action_type="fill",
                target_description="Email input",
                success=False,
                timestamp="2024-01-01T12:01:00Z",
            ),
        ]
        context = AgentContext(
            screenshot=b"fake_png_data",
            accessibility_tree="button: Submit",
            html_snippet="<button>Submit</button>",
            url="https://example.com",
            visible_text="Submit button text",
            previous_actions=actions,
            error_history=[],
            viewport_size=(1920, 1080),
            scroll_position=(0, 100),
        )
        result = context.to_prompt_context()
        assert "click on Cancel button: success" in result
        assert "fill on Email input: failed" in result

    def test_agent_context_to_prompt_context_with_errors(self) -> None:
        """to_prompt_context() should include error history."""
        from subterminator.core.protocols import AgentContext, ErrorRecord

        errors = [
            ErrorRecord(
                action_type="click",
                error_type="ElementNotFound",
                error_message="Could not find button",
                strategy_attempted="CSS: #btn",
                timestamp="2024-01-01T12:00:00Z",
            ),
        ]
        context = AgentContext(
            screenshot=b"fake_png_data",
            accessibility_tree="button: Submit",
            html_snippet="<button>Submit</button>",
            url="https://example.com",
            visible_text="Submit button text",
            previous_actions=[],
            error_history=errors,
            viewport_size=(1920, 1080),
            scroll_position=(0, 100),
        )
        result = context.to_prompt_context()
        assert "click: ElementNotFound - Could not find button" in result


class TestExecutionResult:
    """Tests for ExecutionResult dataclass (Task 1.15)."""

    def test_execution_result_success(self) -> None:
        """ExecutionResult should handle successful execution."""
        from subterminator.core.protocols import ActionPlan, ExecutionResult, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#btn")
        plan = ActionPlan(action_type="click", primary_target=target)
        result = ExecutionResult(
            success=True,
            action_plan=plan,
            strategy_used=target,
            elapsed_ms=150,
        )
        assert result.success is True
        assert result.action_plan == plan
        assert result.strategy_used == target
        assert result.error is None
        assert result.elapsed_ms == 150

    def test_execution_result_failure(self) -> None:
        """ExecutionResult should handle failed execution."""
        from subterminator.core.protocols import ActionPlan, ExecutionResult, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#btn")
        plan = ActionPlan(action_type="click", primary_target=target)
        result = ExecutionResult(
            success=False,
            action_plan=plan,
            error="Element not found",
        )
        assert result.success is False
        assert result.error == "Element not found"
        assert result.strategy_used is None

    def test_execution_result_with_screenshot(self) -> None:
        """ExecutionResult should store screenshot after execution."""
        from subterminator.core.protocols import ActionPlan, ExecutionResult, TargetStrategy

        target = TargetStrategy(method="css", css_selector="#btn")
        plan = ActionPlan(action_type="click", primary_target=target)
        result = ExecutionResult(
            success=True,
            action_plan=plan,
            strategy_used=target,
            screenshot_after=b"png_data",
        )
        assert result.screenshot_after == b"png_data"


class TestValidationResult:
    """Tests for ValidationResult dataclass (Task 1.15)."""

    def test_validation_result_success(self) -> None:
        """ValidationResult should handle successful validation."""
        from subterminator.core.protocols import ValidationResult

        result = ValidationResult(
            success=True,
            expected_state=State.RETENTION_OFFER,
            actual_state=State.RETENTION_OFFER,
            confidence=0.95,
            message="State matches expected",
        )
        assert result.success is True
        assert result.expected_state == State.RETENTION_OFFER
        assert result.actual_state == State.RETENTION_OFFER
        assert result.confidence == 0.95
        assert result.message == "State matches expected"

    def test_validation_result_failure(self) -> None:
        """ValidationResult should handle failed validation."""
        from subterminator.core.protocols import ValidationResult

        result = ValidationResult(
            success=False,
            expected_state=State.RETENTION_OFFER,
            actual_state=State.ACCOUNT_ACTIVE,
            confidence=0.8,
            message="State mismatch: expected RETENTION_OFFER, got ACCOUNT_ACTIVE",
        )
        assert result.success is False
        assert result.expected_state == State.RETENTION_OFFER
        assert result.actual_state == State.ACCOUNT_ACTIVE


class TestSpecRequiredModuleExports:
    """Tests for module exports of spec-required dataclasses (Task 1.16)."""

    def test_action_record_importable_from_protocols(self) -> None:
        """ActionRecord should be importable from protocols."""
        from subterminator.core.protocols import ActionRecord

        assert ActionRecord is not None

    def test_error_record_importable_from_protocols(self) -> None:
        """ErrorRecord should be importable from protocols."""
        from subterminator.core.protocols import ErrorRecord

        assert ErrorRecord is not None

    def test_target_strategy_importable_from_protocols(self) -> None:
        """TargetStrategy should be importable from protocols."""
        from subterminator.core.protocols import TargetStrategy

        assert TargetStrategy is not None

    def test_action_plan_importable_from_protocols(self) -> None:
        """ActionPlan should be importable from protocols."""
        from subterminator.core.protocols import ActionPlan

        assert ActionPlan is not None

    def test_agent_context_importable_from_protocols(self) -> None:
        """AgentContext should be importable from protocols."""
        from subterminator.core.protocols import AgentContext

        assert AgentContext is not None

    def test_execution_result_importable_from_protocols(self) -> None:
        """ExecutionResult should be importable from protocols."""
        from subterminator.core.protocols import ExecutionResult

        assert ExecutionResult is not None

    def test_validation_result_importable_from_protocols(self) -> None:
        """ValidationResult should be importable from protocols."""
        from subterminator.core.protocols import ValidationResult

        assert ValidationResult is not None

    def test_action_record_importable_from_core(self) -> None:
        """ActionRecord should be importable from subterminator.core."""
        from subterminator.core import ActionRecord

        assert ActionRecord is not None

    def test_error_record_importable_from_core(self) -> None:
        """ErrorRecord should be importable from subterminator.core."""
        from subterminator.core import ErrorRecord

        assert ErrorRecord is not None

    def test_target_strategy_importable_from_core(self) -> None:
        """TargetStrategy should be importable from subterminator.core."""
        from subterminator.core import TargetStrategy

        assert TargetStrategy is not None

    def test_action_plan_importable_from_core(self) -> None:
        """ActionPlan should be importable from subterminator.core."""
        from subterminator.core import ActionPlan

        assert ActionPlan is not None

    def test_agent_context_importable_from_core(self) -> None:
        """AgentContext should be importable from subterminator.core."""
        from subterminator.core import AgentContext

        assert AgentContext is not None

    def test_execution_result_importable_from_core(self) -> None:
        """ExecutionResult should be importable from subterminator.core."""
        from subterminator.core import ExecutionResult

        assert ExecutionResult is not None

    def test_validation_result_importable_from_core(self) -> None:
        """ValidationResult should be importable from subterminator.core."""
        from subterminator.core import ValidationResult

        assert ValidationResult is not None
