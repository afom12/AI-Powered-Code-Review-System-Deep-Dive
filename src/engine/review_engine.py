"""Main review orchestration engine"""

from typing import List, Optional
from ..models.review import CodeReviewRequest
from ..models.analysis import AnalysisResult
from ..analyzers import (
    PatternMatcher,
    SecurityScanner,
    ArchitectureChecker,
    PerformancePredictor,
    TestGapAnalyzer,
)
from ..context import HistoricalAnalyzer, TeamPatternsLoader
from ..utils.database import Neo4jConnection, QdrantConnection
from ..utils.embeddings import CodeEmbedder
from ..learning.feedback_analyzer import FeedbackAnalyzer
from .prioritizer import Prioritizer


class ReviewEngine:
    """
    Main orchestration engine for code review.
    Coordinates all analyzers and context gathering.
    """
    
    def __init__(
        self,
        min_confidence: float = 0.6,
        max_results: int = 50,
        enable_historical: bool = True,
        enable_learning: bool = True,
        neo4j_conn: Optional[Neo4jConnection] = None,
        qdrant_conn: Optional[QdrantConnection] = None,
        embedder: Optional[CodeEmbedder] = None
    ):
        self.min_confidence = min_confidence
        self.max_results = max_results
        self.enable_historical = enable_historical
        self.enable_learning = enable_learning
        
        # Initialize analyzers
        self.analyzers = [
            PatternMatcher(),
            SecurityScanner(),
            ArchitectureChecker(),
            PerformancePredictor(),
            TestGapAnalyzer(),
        ]
        
        # Initialize context gatherers with database connections
        self.historical_analyzer = HistoricalAnalyzer(
            neo4j_conn=neo4j_conn,
            qdrant_conn=qdrant_conn,
            embedder=embedder
        )
        self.team_patterns_loader = TeamPatternsLoader()
        self.prioritizer = Prioritizer()
        
        # Initialize feedback analyzer for learning
        self.feedback_analyzer = FeedbackAnalyzer(neo4j_conn=neo4j_conn) if enable_learning else None
    
    async def review(self, request: CodeReviewRequest) -> List[AnalysisResult]:
        """
        Perform comprehensive code review.
        
        Args:
            request: The code review request
            
        Returns:
            List of prioritized analysis results
        """
        # Load team context if available
        if request.team_context is None:
            request.team_context = self.team_patterns_loader.get_team_context()
        
        # Store PR data in databases for future analysis
        if self.enable_historical:
            try:
                await self.historical_analyzer.store_pr_data(request)
            except Exception as e:
                print(f"Warning: Failed to store PR data: {e}")
        
        # Run all analyzers in parallel
        all_results = []
        
        for analyzer in self.analyzers:
            try:
                results = await analyzer.analyze(request)
                all_results.extend(results)
            except Exception as e:
                # Log error but continue with other analyzers
                print(f"Error in {analyzer.name}: {e}")
                continue
        
        # Enhance with historical context
        if self.enable_historical:
            historical_data = await self._gather_historical_context(request)
            all_results = self.historical_analyzer.enhance_results_with_history(
                all_results,
                historical_data
            )
        
        # Apply learning from feedback
        if self.enable_learning and self.feedback_analyzer:
            all_results = await self._apply_learning(all_results)
        
        # Filter by confidence
        filtered_results = [
            r for r in all_results 
            if r.confidence >= self.min_confidence
        ]
        
        # Prioritize and deduplicate
        prioritized_results = self.prioritizer.prioritize(filtered_results)
        
        # Limit results
        return prioritized_results[:self.max_results]
    
    async def _gather_historical_context(self, request: CodeReviewRequest) -> dict:
        """Gather historical context for the review"""
        historical_data = {}
        
        try:
            # Find similar PRs
            similar_prs = await self.historical_analyzer.find_similar_prs(request)
            historical_data["similar_prs"] = similar_prs
            
            # Find bug patterns
            bug_patterns = await self.historical_analyzer.find_bug_patterns(request)
            historical_data["bug_patterns"] = bug_patterns
            
            # Get team patterns
            team_patterns = await self.historical_analyzer.get_team_patterns(request)
            historical_data["team_patterns"] = team_patterns
        except Exception as e:
            print(f"Error gathering historical context: {e}")
        
        return historical_data
    
    async def _apply_learning(self, results: List[AnalysisResult]) -> List[AnalysisResult]:
        """Apply learning from feedback to adjust confidence scores"""
        if not self.feedback_analyzer:
            return results
        
        adjusted_results = []
        
        for result in results:
            try:
                # Generate analysis result ID if not present
                if "analysis_result_id" not in result.metadata:
                    result.metadata["analysis_result_id"] = (
                        f"{result.category.value}_{result.location.file_path}_"
                        f"{result.location.line_start}_{hash(result.title)}"
                    )
                
                # Adjust confidence based on feedback
                adjusted_confidence = await self.feedback_analyzer.adjust_confidence(result)
                
                # Update confidence if adjusted
                if adjusted_confidence != result.confidence:
                    result.confidence = adjusted_confidence
                    # Update confidence level
                    if result.confidence >= 0.9:
                        result.confidence_level = result.confidence_level.__class__.VERY_HIGH
                    elif result.confidence >= 0.7:
                        result.confidence_level = result.confidence_level.__class__.HIGH
                    elif result.confidence >= 0.5:
                        result.confidence_level = result.confidence_level.__class__.MEDIUM
                    elif result.confidence >= 0.3:
                        result.confidence_level = result.confidence_level.__class__.LOW
                    else:
                        result.confidence_level = result.confidence_level.__class__.VERY_LOW
                
                adjusted_results.append(result)
            except Exception as e:
                print(f"Error applying learning to result: {e}")
                adjusted_results.append(result)  # Keep original if error
        
        return adjusted_results


