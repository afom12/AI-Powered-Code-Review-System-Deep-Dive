"""Base analyzer interface"""

from abc import ABC, abstractmethod
from typing import List
from ..models.review import CodeReviewRequest
from ..models.analysis import AnalysisResult


class BaseAnalyzer(ABC):
    """Base class for all code analyzers"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def analyze(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """
        Analyze the code review request and return findings.
        
        Args:
            request: The code review request to analyze
            
        Returns:
            List of analysis results
        """
        pass
    
    def _filter_by_confidence(
        self, 
        results: List[AnalysisResult], 
        min_confidence: float = 0.5
    ) -> List[AnalysisResult]:
        """Filter results by minimum confidence threshold"""
        return [r for r in results if r.confidence >= min_confidence]
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"



