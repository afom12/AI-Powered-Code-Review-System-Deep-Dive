"""Historical pattern detection analyzer"""

import re
from typing import List, Dict, Tuple
from ..models.review import CodeReviewRequest, CodeLocation
from ..models.analysis import AnalysisResult, AnalysisCategory, PriorityLevel
from .base import BaseAnalyzer


class PatternMatcher(BaseAnalyzer):
    """
    Detects code patterns that have caused issues in the past.
    Uses historical data and team knowledge to identify problematic patterns.
    """
    
    # Common anti-patterns that often cause bugs
    ANTI_PATTERNS = {
        "empty_catch": {
            "pattern": r"catch\s*\([^)]*\)\s*\{\s*\}",  # Empty catch block
            "category": AnalysisCategory.BUG,
            "priority": PriorityLevel.MEDIUM,
            "confidence": 0.7,
            "message": "Empty catch block may hide errors",
            "suggestion": "Add error handling or logging in catch block"
        },
        "hardcoded_secret": {
            "pattern": r"(?:password|secret|api[_-]?key|token)\s*=\s*['\"][^'\"]+['\"]",
            "category": AnalysisCategory.SECURITY,
            "priority": PriorityLevel.CRITICAL,
            "confidence": 0.8,
            "message": "Potential hardcoded secret detected",
            "suggestion": "Use environment variables or secret management service"
        },
        "todo_in_code": {
            "pattern": r"(?:TODO|FIXME|HACK|XXX):\s*(.+)",
            "category": AnalysisCategory.CODE_QUALITY,
            "priority": PriorityLevel.LOW,
            "confidence": 0.6,
            "message": "TODO/FIXME comment found",
            "suggestion": "Consider creating an issue or addressing before merge"
        },
        "print_debug": {
            "pattern": r"print\s*\([^)]+\)",
            "category": AnalysisCategory.CODE_QUALITY,
            "priority": PriorityLevel.LOW,
            "confidence": 0.5,
            "message": "Print statement found (debug code?)",
            "suggestion": "Use proper logging instead of print statements"
        },
        "broad_except": {
            "pattern": r"except\s*:",
            "category": AnalysisCategory.BUG,
            "priority": PriorityLevel.MEDIUM,
            "confidence": 0.65,
            "message": "Bare except clause catches all exceptions",
            "suggestion": "Catch specific exceptions or at least log the error"
        },
        "nested_try": {
            "pattern": r"try\s*\{[^}]*try\s*\{",
            "category": AnalysisCategory.CODE_QUALITY,
            "priority": PriorityLevel.LOW,
            "confidence": 0.5,
            "message": "Nested try-catch blocks may indicate complex error handling",
            "suggestion": "Consider refactoring to simplify error handling"
        },
    }
    
    def __init__(self, custom_patterns: Dict = None):
        super().__init__("PatternMatcher")
        self.patterns = {**self.ANTI_PATTERNS}
        if custom_patterns:
            self.patterns.update(custom_patterns)
    
    async def analyze(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Analyze code for known anti-patterns"""
        results = []
        
        for file_diff in request.diff:
            if file_diff.status == "removed":
                continue
            
            # Skip binary files
            if not file_diff.language or file_diff.language == "binary":
                continue
            
            # Check each pattern
            for pattern_name, pattern_config in self.patterns.items():
                matches = self._find_pattern_matches(
                    file_diff.diff, 
                    pattern_config["pattern"],
                    file_diff.file_path
                )
                
                for match in matches:
                    result = AnalysisResult(
                        category=pattern_config["category"],
                        priority=pattern_config["priority"],
                        confidence=pattern_config["confidence"],
                        location=match["location"],
                        title=pattern_config["message"],
                        description=f"Found {pattern_name} pattern in {file_diff.file_path}",
                        suggestion=pattern_config["suggestion"],
                        code_snippet=match.get("snippet"),
                        metadata={"pattern_name": pattern_name}
                    )
                    results.append(result)
        
        return self._filter_by_confidence(results, min_confidence=0.5)
    
    def _find_pattern_matches(
        self, 
        diff_content: str, 
        pattern: str, 
        file_path: str
    ) -> List[Dict]:
        """Find all matches of a pattern in diff content"""
        matches = []
        regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        
        # Parse diff to get line numbers
        lines = diff_content.split('\n')
        current_line = 0
        
        for line in lines:
            # Skip diff headers
            if line.startswith(('---', '+++', '@@', 'diff')):
                continue
            
            # Track line numbers (lines starting with + are additions)
            if line.startswith('+') and not line.startswith('+++'):
                current_line += 1
                line_content = line[1:]  # Remove + prefix
                
                for match in regex.finditer(line_content):
                    # Estimate line number (simplified)
                    location = CodeLocation(
                        file_path=file_path,
                        line_start=current_line,
                        line_end=current_line
                    )
                    
                    matches.append({
                        "location": location,
                        "snippet": line_content[max(0, match.start()-20):match.end()+20]
                    })
            elif not line.startswith('-'):
                current_line += 1
        
        return matches



