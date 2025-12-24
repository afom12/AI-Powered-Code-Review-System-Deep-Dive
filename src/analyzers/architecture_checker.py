"""Architecture and design pattern checker"""

from typing import List
from ..models.review import CodeReviewRequest
from ..models.analysis import AnalysisResult, AnalysisCategory, PriorityLevel
from .base import BaseAnalyzer


class ArchitectureChecker(BaseAnalyzer):
    """
    Checks for architectural violations and design issues.
    Analyzes coupling, cohesion, and design pattern adherence.
    """
    
    def __init__(self):
        super().__init__("ArchitectureChecker")
    
    async def analyze(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Analyze code for architectural issues"""
        results = []
        
        # Check for circular dependencies
        results.extend(await self._check_circular_dependencies(request))
        
        # Check for violation of separation of concerns
        results.extend(await self._check_separation_of_concerns(request))
        
        # Check for large files/functions (complexity)
        results.extend(await self._check_complexity(request))
        
        return self._filter_by_confidence(results, min_confidence=0.5)
    
    async def _check_circular_dependencies(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for potential circular dependencies"""
        results = []
        
        # Simple heuristic: if file A imports B and B imports A
        imports_map = {}
        
        for file_diff in request.diff:
            if file_diff.status == "removed":
                continue
            
            imports = self._extract_imports(file_diff.diff, file_diff.file_path)
            imports_map[file_diff.file_path] = imports
        
        # Check for circular imports
        for file_path, imports in imports_map.items():
            for imported_file in imports:
                if imported_file in imports_map:
                    if file_path in imports_map[imported_file]:
                        results.append(AnalysisResult(
                            category=AnalysisCategory.ARCHITECTURE,
                            priority=PriorityLevel.MEDIUM,
                            confidence=0.6,
                            location=self._get_file_location(file_path),
                            title="Potential circular dependency",
                            description=f"Circular import detected between {file_path} and {imported_file}",
                            suggestion="Refactor to break circular dependency. Consider dependency injection or extracting shared code",
                            metadata={"circular_with": imported_file}
                        ))
        
        return results
    
    async def _check_separation_of_concerns(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for violations of separation of concerns"""
        results = []
        
        for file_diff in request.diff:
            # Check if file mixes concerns (e.g., database + business logic + API)
            concerns_found = []
            
            if any(keyword in file_diff.diff.lower() for keyword in ["select", "insert", "update", "delete", "from"]):
                concerns_found.append("database")
            
            if any(keyword in file_diff.diff.lower() for keyword in ["@app.route", "def get_", "def post_", "request"]):
                concerns_found.append("api")
            
            if any(keyword in file_diff.diff.lower() for keyword in ["def calculate", "def process", "def validate"]):
                concerns_found.append("business_logic")
            
            if len(concerns_found) >= 3:
                results.append(AnalysisResult(
                    category=AnalysisCategory.ARCHITECTURE,
                    priority=PriorityLevel.MEDIUM,
                    confidence=0.55,
                    location=self._get_file_location(file_diff.file_path),
                    title="Potential violation of separation of concerns",
                    description=f"File appears to mix multiple concerns: {', '.join(concerns_found)}",
                    suggestion="Consider splitting into separate modules following single responsibility principle",
                    metadata={"concerns": concerns_found}
                ))
        
        return results
    
    async def _check_complexity(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """Check for overly complex code"""
        results = []
        
        for file_diff in request.diff:
            # Simple heuristic: very large diffs might indicate complexity
            if file_diff.changes > 500:
                results.append(AnalysisResult(
                    category=AnalysisCategory.ARCHITECTURE,
                    priority=PriorityLevel.LOW,
                    confidence=0.5,
                    location=self._get_file_location(file_diff.file_path),
                    title="Large change set detected",
                    description=f"File has {file_diff.changes} changes, which may indicate high complexity",
                    suggestion="Consider breaking this into smaller, focused PRs for easier review",
                    metadata={"change_count": file_diff.changes}
                ))
        
        return results
    
    def _extract_imports(self, diff_content: str, file_path: str) -> List[str]:
        """Extract imported modules from diff"""
        imports = []
        lines = diff_content.split('\n')
        
        for line in lines:
            if line.startswith('+') and ('import' in line or 'from' in line):
                # Simple extraction - in production, use AST parser
                if 'from' in line:
                    parts = line.split('import')
                    if len(parts) > 1:
                        module = parts[0].replace('+', '').replace('from', '').strip()
                        imports.append(module)
                elif 'import' in line:
                    parts = line.split('import')
                    if len(parts) > 1:
                        module = parts[1].split(',')[0].strip()
                        imports.append(module)
        
        return imports
    
    def _get_file_location(self, file_path: str):
        """Create a basic file-level location"""
        from ..models.review import CodeLocation
        return CodeLocation(
            file_path=file_path,
            line_start=1,
            line_end=1
        )



