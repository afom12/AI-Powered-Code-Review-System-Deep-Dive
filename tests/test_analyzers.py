"""Tests for analyzers"""

import pytest
from datetime import datetime
from src.models.review import CodeReviewRequest, Repository, FileDiff
from src.analyzers import PatternMatcher, SecurityScanner


@pytest.fixture
def sample_review_request():
    """Create a sample review request for testing"""
    return CodeReviewRequest(
        pr_id="123",
        pr_number=1,
        title="Test PR",
        repo=Repository(
            owner="test",
            name="test-repo",
            full_name="test/test-repo"
        ),
        base_branch="main",
        head_branch="feature/test",
        author="testuser",
        diff=[
            FileDiff(
                file_path="src/test.py",
                additions=10,
                deletions=5,
                changes=15,
                diff="""
+def test_function():
+    password = "hardcoded123"
+    try:
+        do_something()
+    except:
+        pass
+    print("debug info")
+""",
                status="modified",
                language="python"
            )
        ],
        created_at=datetime.now()
    )


@pytest.mark.asyncio
async def test_pattern_matcher(sample_review_request):
    """Test PatternMatcher analyzer"""
    matcher = PatternMatcher()
    results = await matcher.analyze(sample_review_request)
    
    assert len(results) > 0
    # Should detect hardcoded password
    assert any("hardcoded" in r.title.lower() or "secret" in r.title.lower() for r in results)
    # Should detect empty except
    assert any("except" in r.title.lower() or "catch" in r.title.lower() for r in results)


@pytest.mark.asyncio
async def test_security_scanner(sample_review_request):
    """Test SecurityScanner analyzer"""
    scanner = SecurityScanner()
    results = await scanner.analyze(sample_review_request)
    
    # Should detect security issues
    security_results = [r for r in results if r.category.value == "security"]
    assert len(security_results) > 0


@pytest.mark.asyncio
async def test_confidence_filtering(sample_review_request):
    """Test that low confidence results are filtered"""
    matcher = PatternMatcher()
    results = await matcher.analyze(sample_review_request)
    
    # All results should have confidence >= 0.5 (default filter)
    filtered_results = matcher._filter_by_confidence(results, min_confidence=0.5)
    assert all(r.confidence >= 0.5 for r in filtered_results)



