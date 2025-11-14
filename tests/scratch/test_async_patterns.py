"""
Scratch test file to validate async/await patterns work correctly.

This file tests the exact pattern that will be used in the fix:
- Calling async functions and awaiting them
- Accessing attributes on awaited results
- Verifying coroutines are properly resolved
"""

import pytest
import asyncio
from typing import Dict, Any


class MockSkill:
    """Mock skill that returns async response (mimics real skill behavior)."""

    async def execute(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Async method that returns message with attributes."""
        await asyncio.sleep(0.001)  # Simulate async work
        return {
            "message_id": "test-123",
            "status": "success",
            "result": {"data": "test_result"},
            "context": message.get("context", {})
        }


class MockOrchestrator:
    """Mock orchestrator demonstrating correct async pattern."""

    async def execute_skill_correct(self, skill: MockSkill, message: Dict[str, Any]) -> Dict[str, Any]:
        """CORRECT: Await skill.execute() before accessing attributes."""
        response_coro = skill.execute(message)
        response = await response_coro  # ← Await coroutine first

        # Now safe to access attributes
        assert "message_id" in response
        return response

    async def execute_skill_broken(self, skill: MockSkill, message: Dict[str, Any]) -> Dict[str, Any]:
        """BROKEN: Try to access attributes on coroutine (will fail)."""
        response = skill.execute(message)  # Returns coroutine, not dict

        # This will crash with AttributeError
        return response["message_id"]  # ERROR: coroutine has no __getitem__


@pytest.mark.asyncio
async def test_correct_async_pattern():
    """Verify correct pattern: await before attribute access."""
    skill = MockSkill()
    orchestrator = MockOrchestrator()
    message = {"inputs": {"test": "data"}, "context": {}}

    result = await orchestrator.execute_skill_correct(skill, message)

    assert result["message_id"] == "test-123"
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_broken_pattern_fails():
    """Verify broken pattern raises error."""
    skill = MockSkill()
    orchestrator = MockOrchestrator()
    message = {"inputs": {"test": "data"}, "context": {}}

    with pytest.raises(TypeError, match="'coroutine' object is not subscriptable"):
        await orchestrator.execute_skill_broken(skill, message)


@pytest.mark.asyncio
async def test_await_resolves_coroutine():
    """Verify await resolves coroutine to actual value."""
    skill = MockSkill()
    message = {"inputs": {"test": "data"}}

    # Without await - returns coroutine
    coro = skill.execute(message)
    assert asyncio.iscoroutine(coro)

    # With await - resolves to dict
    result = await coro
    assert isinstance(result, dict)
    assert "message_id" in result


if __name__ == "__main__":
    # Quick validation that async patterns work
    async def main():
        print("Testing correct async pattern...")
        await test_correct_async_pattern()
        print("✅ Correct pattern works")

        print("\nTesting broken pattern...")
        await test_broken_pattern_fails()
        print("✅ Broken pattern fails as expected")

        print("\nTesting coroutine resolution...")
        await test_await_resolves_coroutine()
        print("✅ Await properly resolves coroutines")

        print("\n🎯 All async patterns validated!")

    asyncio.run(main())
