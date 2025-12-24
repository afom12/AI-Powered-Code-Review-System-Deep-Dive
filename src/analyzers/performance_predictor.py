"""Performance impact predictor"""

from typing import List
from ..models.review import CodeReviewRequest
from ..models.analysis import AnalysisResult, AnalysisCategory, PriorityLevel
from .base import BaseAnalyzer


class PerformancePredictor(BaseAnalyzer):
    """
    Predicts potential performance issues.
    Identifies patterns that may cause performance regressions.
    """
    
    def __init__(self):
        super().__init__("PerformancePredictor")
    
    async def analyze(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Analyze code for performance issues"""
        results = []
        
        # Check for N+1 query patterns
        results.extend(await self._check_n_plus_one(request))
        
        # Check for inefficient loops
        results.extend(await self._check_inefficient_loops(request))
        
        # Check for missing indexes
        results.extend(await self._check_missing_indexes(request))
        
        return self._filter_by_confidence(results, min_confidence=0.5)
    
    async def _check_n_plus_one(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for N+1 query patterns"""
        results = []
        
        for file_diff in request.diff:
            # Look for loops with database queries inside
            if "for" in file_diff.diff.lower() or "while" in file_diff.diff.lower():
                if any(keyword in file_diff.diff.lower() for keyword in ["query", "get_by", "find_by", "select"]):
                    results.append(AnalysisResult(
                        category=AnalysisCategory.PERFORMANCE,
                        priority=PriorityLevel.MEDIUM,
                        confidence=0.6,
                        location=self._get_file_location(file_diff.file_path),
                        title="Potential N+1 query pattern",
                        description="Database query detected inside loop, which may cause N+1 problem",
                        suggestion="Consider using eager loading, batch queries, or data prefetching",
                        metadata={"issue_type": "n_plus_one"}
                    ))
        
        return results
    
    async def _check_inefficient_loops(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for inefficient loop patterns"""
        results = []
        
        for file_diff in request.diff:
            # Look for nested loops with large datasets
            loop_count = file_diff.diff.lower().count("for ") + file_diff.diff.lower().count("while ")
            if loop_count >= 2:
                results.append(AnalysisResult(
                    category=AnalysisCategory.PERFORMANCE,
                    priority=PriorityLevel.LOW,
                    confidence=0.5,
                    location=self._get_file_location(file_diff.file_path),
                    title="Nested loops detected",
                    description="Multiple nested loops may cause performance issues with large datasets",
                    suggestion="Consider optimizing algorithm complexity or using vectorized operations",
                    metadata={"loop_count": loop_count}
                ))
        
        return results
    
    async def _check_missing_indexes(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for missing database indexes"""
        results = []
        
        for file_diff in request.diff:
            # Look for WHERE clauses without indexes
            if "where" in file_diff.diff.lower() and "index" not in file_diff.diff.lower():
                # Simple heuristic - in production, analyze actual queries
                results.append(AnalysisResult(
                    category=AnalysisCategory.PERFORMANCE,
                    priority=PriorityLevel.LOW,
                    confidence=0.4,
                    location=self._get_file_location(file_diff.file_path),
                    title="Query may benefit from index",
                    description="WHERE clause detected - ensure appropriate indexes exist",
                    suggestion="Verify database indexes exist for columns used in WHERE clauses",
                    metadata={"issue_type": "missing_index"}
                ))
        
        return results
    
    def _get_file_location(self, file_path: str):
        """Create a basic file-level location"""
        from ..models.review import CodeLocation
        return CodeLocation(
            file_path=file_path,
            line_start=1,
            line_end=1
        )



