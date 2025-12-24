"""Security-focused code scanner"""

from typing import List
from ..models.review import CodeReviewRequest
from ..models.analysis import AnalysisResult, AnalysisCategory, PriorityLevel
from .base import BaseAnalyzer


class SecurityScanner(BaseAnalyzer):
    """
    Scans code for security vulnerabilities.
    Focuses on OWASP Top 10 and common security issues.
    """
    
    def __init__(self):
        super().__init__("SecurityScanner")
        # In production, integrate with Semgrep or similar tools
    
    async def analyze(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Analyze code for security issues"""
        results = []
        
        # Check for SQL injection risks
        results.extend(await self._check_sql_injection(request))
        
        # Check for XSS risks
        results.extend(await self._check_xss(request))
        
        # Check for authentication/authorization issues
        results.extend(await self._check_auth_issues(request))
        
        # Check for sensitive data exposure
        results.extend(await self._check_sensitive_data(request))
        
        return self._filter_by_confidence(results, min_confidence=0.6)
    
    async def _check_sql_injection(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for SQL injection vulnerabilities"""
        results = []
        
        for file_diff in request.diff:
            if "sql" in file_diff.file_path.lower() or file_diff.language == "sql":
                # Look for string concatenation in SQL queries
                if "SELECT" in file_diff.diff.upper() or "INSERT" in file_diff.diff.upper():
                    # Simple heuristic: f-strings or + operators with user input
                    if any(op in file_diff.diff for op in ["f'SELECT", "f\"SELECT", "+ 'SELECT", "+\"SELECT"]):
                        results.append(AnalysisResult(
                            category=AnalysisCategory.SECURITY,
                            priority=PriorityLevel.HIGH,
                            confidence=0.75,
                            location=self._get_file_location(file_diff.file_path),
                            title="Potential SQL injection risk",
                            description="SQL query appears to use string formatting with user input",
                            suggestion="Use parameterized queries or ORM methods instead of string concatenation",
                            metadata={"vulnerability_type": "sql_injection"}
                        ))
        
        return results
    
    async def _check_xss(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for XSS vulnerabilities"""
        results = []
        
        for file_diff in request.diff:
            if file_diff.language in ["html", "javascript", "jsx", "tsx"]:
                # Look for innerHTML usage without sanitization
                if "innerHTML" in file_diff.diff and "sanitize" not in file_diff.diff.lower():
                    results.append(AnalysisResult(
                        category=AnalysisCategory.SECURITY,
                        priority=PriorityLevel.MEDIUM,
                        confidence=0.65,
                        location=self._get_file_location(file_diff.file_path),
                        title="Potential XSS vulnerability",
                        description="innerHTML usage without sanitization detected",
                        suggestion="Use textContent or sanitize HTML before setting innerHTML",
                        metadata={"vulnerability_type": "xss"}
                    ))
        
        return results
    
    async def _check_auth_issues(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for authentication/authorization issues"""
        results = []
        
        for file_diff in request.diff:
            # Look for endpoints without authentication checks
            if any(keyword in file_diff.diff.lower() for keyword in ["@app.route", "def api_", "def endpoint"]):
                if "@require_auth" not in file_diff.diff and "@login_required" not in file_diff.diff:
                    # Check if it's a public endpoint (might be intentional)
                    if "public" not in file_diff.diff.lower() and "open" not in file_diff.diff.lower():
                        results.append(AnalysisResult(
                            category=AnalysisCategory.SECURITY,
                            priority=PriorityLevel.HIGH,
                            confidence=0.6,
                            location=self._get_file_location(file_diff.file_path),
                            title="Endpoint may lack authentication",
                            description="New endpoint detected without obvious authentication decorator",
                            suggestion="Verify this endpoint requires authentication. Add @require_auth or similar decorator if needed",
                            metadata={"vulnerability_type": "auth_bypass"}
                        ))
        
        return results
    
    async def _check_sensitive_data(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for sensitive data exposure"""
        results = []
        
        sensitive_keywords = ["password", "ssn", "credit_card", "api_key", "secret", "token"]
        
        for file_diff in request.diff:
            # Check for logging sensitive data
            if any(keyword in file_diff.diff.lower() for keyword in ["log", "print", "console.log"]):
                for sensitive in sensitive_keywords:
                    if sensitive in file_diff.diff.lower():
                        results.append(AnalysisResult(
                            category=AnalysisCategory.SECURITY,
                            priority=PriorityLevel.MEDIUM,
                            confidence=0.7,
                            location=self._get_file_location(file_diff.file_path),
                            title="Potential sensitive data in logs",
                            description=f"Found '{sensitive}' keyword near logging statements",
                            suggestion="Ensure sensitive data is not logged. Use masking or remove from logs",
                            metadata={"vulnerability_type": "data_exposure", "sensitive_type": sensitive}
                        ))
                        break
        
        return results
    
    def _get_file_location(self, file_path: str):
        """Create a basic file-level location"""
        from ..models.review import CodeLocation
        return CodeLocation(
            file_path=file_path,
            line_start=1,
            line_end=1
        )



