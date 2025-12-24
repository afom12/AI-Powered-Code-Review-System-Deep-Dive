"""Test coverage and quality analyzer"""

from typing import List
from ..models.review import CodeReviewRequest
from ..models.analysis import AnalysisResult, AnalysisCategory, PriorityLevel
from .base import BaseAnalyzer


class TestGapAnalyzer(BaseAnalyzer):
    """
    Analyzes test coverage and identifies gaps.
    Checks if changed code has adequate test coverage.
    """
    
    def __init__(self):
        super().__init__("TestGapAnalyzer")
    
    async def analyze(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Analyze test coverage"""
        results = []
        
        # Check if tests exist for changed files
        results.extend(await self._check_missing_tests(request))
        
        # Check test quality
        results.extend(await self._check_test_quality(request))
        
        return self._filter_by_confidence(results, min_confidence=0.5)
    
    async def _check_missing_tests(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check if changed files have corresponding tests"""
        results = []
        
        changed_files = {diff.file_path for diff in request.diff if diff.status != "removed"}
        test_files = {diff.file_path for diff in request.diff if "test" in diff.file_path.lower()}
        
        # Simple heuristic: check if test files exist
        for file_diff in request.diff:
            if file_diff.status == "removed":
                continue
            
            # Skip test files themselves
            if "test" in file_diff.file_path.lower():
                continue
            
            # Check if corresponding test file exists
            base_name = file_diff.file_path.replace(".py", "").replace(".js", "")
            has_test = any(
                base_name in test_file or test_file.replace("test_", "").replace("_test", "") == base_name
                for test_file in changed_files
            )
            
            if not has_test and file_diff.changes > 10:  # Only flag significant changes
                results.append(AnalysisResult(
                    category=AnalysisCategory.TEST,
                    priority=PriorityLevel.MEDIUM,
                    confidence=0.6,
                    location=self._get_file_location(file_diff.file_path),
                    title="No corresponding test file detected",
                    description=f"Changed file {file_diff.file_path} doesn't appear to have corresponding tests",
                    suggestion="Consider adding tests for the changed functionality",
                    metadata={"file_path": file_diff.file_path, "changes": file_diff.changes}
                ))
        
        return results
    
    async def _check_test_quality(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check quality of test code"""
        results = []
        
        for file_diff in request.diff:
            if "test" not in file_diff.file_path.lower():
                continue
            
            # Check for test quality indicators
            test_content = file_diff.diff.lower()
            
            # Check for assertions
            if "assert" not in test_content and "expect" not in test_content:
                results.append(AnalysisResult(
                    category=AnalysisCategory.TEST,
                    priority=PriorityLevel.MEDIUM,
                    confidence=0.7,
                    location=self._get_file_location(file_diff.file_path),
                    title="Test may lack assertions",
                    description="Test file doesn't appear to have assertions",
                    suggestion="Ensure tests have proper assertions to validate behavior",
                    metadata={"issue_type": "missing_assertions"}
                ))
            
            # Check for mocking (might indicate integration vs unit test)
            if "mock" in test_content or "stub" in test_content:
                # This is actually good, but we could check if mocks are too permissive
                pass
        
        return results
    
    def _get_file_location(self, file_path: str):
        """Create a basic file-level location"""
        from ..models.review import CodeLocation
        return CodeLocation(
            file_path=file_path,
            line_start=1,
            line_end=1
        )



