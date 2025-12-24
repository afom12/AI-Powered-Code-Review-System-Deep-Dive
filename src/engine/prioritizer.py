"""Prioritizes and deduplicates analysis results"""

from typing import List, Dict
from ..models.analysis import AnalysisResult, PriorityLevel, AnalysisCategory


class Prioritizer:
    """
    Prioritizes analysis results based on:
    - Category importance
    - Priority level
    - Confidence score
    - Location (critical files vs tests)
    """
    
    # Category weights (higher = more important)
    CATEGORY_WEIGHTS = {
        AnalysisCategory.SECURITY: 10.0,
        AnalysisCategory.BUG: 8.0,
        AnalysisCategory.ARCHITECTURE: 6.0,
        AnalysisCategory.PERFORMANCE: 5.0,
        AnalysisCategory.BUSINESS_LOGIC: 7.0,
        AnalysisCategory.TEST: 4.0,
        AnalysisCategory.CODE_QUALITY: 3.0,
        AnalysisCategory.STYLE: 1.0,
    }
    
    # Priority weights
    PRIORITY_WEIGHTS = {
        PriorityLevel.CRITICAL: 10.0,
        PriorityLevel.HIGH: 7.0,
        PriorityLevel.MEDIUM: 4.0,
        PriorityLevel.LOW: 2.0,
        PriorityLevel.INFO: 1.0,
    }
    
    def prioritize(self, results: List[AnalysisResult]) -> List[AnalysisResult]:
        """
        Prioritize and deduplicate results.
        
        Args:
            results: List of analysis results
            
        Returns:
            Prioritized and deduplicated results
        """
        # Calculate priority scores
        scored_results = []
        for result in results:
            score = self._calculate_score(result)
            scored_results.append((score, result))
        
        # Sort by score (descending)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Deduplicate similar results
        deduplicated = self._deduplicate([r for _, r in scored_results])
        
        return deduplicated
    
    def _calculate_score(self, result: AnalysisResult) -> float:
        """Calculate priority score for a result"""
        category_weight = self.CATEGORY_WEIGHTS.get(result.category, 1.0)
        priority_weight = self.PRIORITY_WEIGHTS.get(result.priority, 1.0)
        confidence_weight = result.confidence
        
        # Base score
        base_score = category_weight * priority_weight * confidence_weight
        
        # Boost for critical files
        if self._is_critical_file(result.location.file_path):
            base_score *= 1.5
        
        # Boost for security issues
        if result.category == AnalysisCategory.SECURITY:
            base_score *= 1.2
        
        return base_score
    
    def _is_critical_file(self, file_path: str) -> bool:
        """Check if file is critical (auth, payment, etc.)"""
        critical_keywords = [
            "auth", "payment", "security", "encrypt", "secret",
            "admin", "permission", "access"
        ]
        return any(keyword in file_path.lower() for keyword in critical_keywords)
    
    def _deduplicate(self, results: List[AnalysisResult]) -> List[AnalysisResult]:
        """Remove duplicate or very similar results"""
        seen = set()
        deduplicated = []
        
        for result in results:
            # Create a signature for the result
            signature = (
                result.location.file_path,
                result.location.line_start,
                result.category,
                result.title[:50]  # First 50 chars of title
            )
            
            if signature not in seen:
                seen.add(signature)
                deduplicated.append(result)
        
        return deduplicated



