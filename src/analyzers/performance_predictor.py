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
        """Analyze code for performance issues and regression risks"""
        results = []
        
        # Check for N+1 query patterns
        results.extend(await self._check_n_plus_one(request))
        
        # Check for inefficient loops
        results.extend(await self._check_inefficient_loops(request))
        
        # Check for missing indexes
        results.extend(await self._check_missing_indexes(request))
        
        # Performance regression prediction
        results.extend(await self._predict_regressions(request))
        results.extend(await self._check_memory_issues(request))
        results.extend(await self._check_async_patterns(request))
        
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
    
    async def _predict_regressions(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Predict potential performance regressions"""
        results = []
        
        for file_diff in request.diff:
            diff_lower = file_diff.diff.lower()
            
            # Check for new loops in hot paths
            if any(path in file_diff.file_path.lower() for path in ["api", "controller", "handler", "route"]):
                loop_count = diff_lower.count("for ") + diff_lower.count("while ")
                if loop_count > 0:
                    results.append(AnalysisResult(
                        category=AnalysisCategory.PERFORMANCE,
                        priority=PriorityLevel.MEDIUM,
                        confidence=0.65,
                        location=self._get_file_location(file_diff.file_path),
                        title="Potential performance regression in hot path",
                        description="Loop detected in API/controller layer - may impact request latency",
                        suggestion="Consider moving heavy computation to background jobs or optimizing loop complexity",
                        metadata={"loop_count": loop_count, "risk_level": "medium"}
                    ))
            
            # Check for synchronous I/O in async contexts
            if "async def" in diff_lower or "async function" in diff_lower:
                if any(blocking in diff_lower for blocking in ["requests.get", "requests.post", "urllib", "time.sleep"]):
                    results.append(AnalysisResult(
                        category=AnalysisCategory.PERFORMANCE,
                        priority=PriorityLevel.HIGH,
                        confidence=0.7,
                        location=self._get_file_location(file_diff.file_path),
                        title="Blocking I/O in async function",
                        description="Synchronous I/O detected in async context - blocks event loop",
                        suggestion="Use async/await compatible libraries (aiohttp, httpx) instead of blocking calls",
                        metadata={"risk_level": "high", "issue_type": "blocking_io"}
                    ))
            
            # Check for large data processing without pagination
            if any(keyword in diff_lower for keyword in ["select *", "find_all", "get_all", "list()"]):
                if "limit" not in diff_lower and "paginate" not in diff_lower:
                    results.append(AnalysisResult(
                        category=AnalysisCategory.PERFORMANCE,
                        priority=PriorityLevel.MEDIUM,
                        confidence=0.6,
                        location=self._get_file_location(file_diff.file_path),
                        title="Potential memory issue - no pagination",
                        description="Query fetches all records without pagination - may cause memory issues",
                        suggestion="Add pagination or limit clause to prevent loading large datasets",
                        metadata={"risk_level": "medium", "issue_type": "no_pagination"}
                    ))
        
        return results
    
    async def _check_memory_issues(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for potential memory issues"""
        results = []
        
        for file_diff in request.diff:
            diff_lower = file_diff.diff.lower()
            
            # Check for large list/dict comprehensions
            if "[" in diff_lower and "for " in diff_lower and "in " in diff_lower:
                # Check if it's a nested comprehension (potential memory issue)
                if diff_lower.count("[") > 2:
                    results.append(AnalysisResult(
                        category=AnalysisCategory.PERFORMANCE,
                        priority=PriorityLevel.LOW,
                        confidence=0.5,
                        location=self._get_file_location(file_diff.file_path),
                        title="Nested list comprehension detected",
                        description="Complex nested comprehension may consume significant memory",
                        suggestion="Consider using generator expressions or breaking into multiple steps",
                        metadata={"issue_type": "memory_usage"}
                    ))
            
            # Check for string concatenation in loops
            if ("for " in diff_lower or "while " in diff_lower) and ("+=" in diff_lower or "= " + file_diff.file_path.split(".")[-1] + " +" in diff_lower):
                results.append(AnalysisResult(
                    category=AnalysisCategory.PERFORMANCE,
                    priority=PriorityLevel.MEDIUM,
                    confidence=0.6,
                    location=self._get_file_location(file_diff.file_path),
                    title="String concatenation in loop",
                    description="String concatenation in loops creates new objects each iteration",
                    suggestion="Use list.join() or string builder pattern for better performance",
                    metadata={"issue_type": "string_concat"}
                ))
        
        return results
    
    async def _check_async_patterns(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for async/await performance patterns"""
        results = []
        
        for file_diff in request.diff:
            diff_lower = file_diff.diff.lower()
            
            # Check for await in loops (potential sequential processing)
            if "await" in diff_lower and ("for " in diff_lower or "while " in diff_lower):
                if "asyncio.gather" not in diff_lower and "asyncio.create_task" not in diff_lower:
                    results.append(AnalysisResult(
                        category=AnalysisCategory.PERFORMANCE,
                        priority=PriorityLevel.MEDIUM,
                        confidence=0.65,
                        location=self._get_file_location(file_diff.file_path),
                        title="Sequential await in loop",
                        description="Awaiting in loop processes items sequentially - may be slow",
                        suggestion="Use asyncio.gather() or asyncio.create_task() for parallel processing",
                        metadata={"issue_type": "sequential_await"}
                    ))
        
        return results



