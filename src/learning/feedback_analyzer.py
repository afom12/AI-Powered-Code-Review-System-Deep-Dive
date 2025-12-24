"""Analyzes feedback to learn patterns and improve analysis"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ..models.feedback import Feedback, FeedbackStats, LearningPattern, FeedbackType
from ..models.analysis import AnalysisResult, AnalysisCategory
from ..utils.database import Neo4jConnection
import redis
import os


class FeedbackAnalyzer:
    """Analyzes feedback to learn patterns and adjust confidence"""
    
    def __init__(
        self,
        neo4j_conn: Optional[Neo4jConnection] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        self.neo4j = neo4j_conn or Neo4jConnection()
        self.redis = redis_client or self._init_redis()
        self.learning_patterns: Dict[str, LearningPattern] = {}
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
            return redis.Redis(host=host, port=port, db=db, decode_responses=True)
        except Exception as e:
            print(f"Warning: Redis connection failed: {e}")
            return None
    
    async def analyze_feedback_patterns(self, days: int = 30) -> List[LearningPattern]:
        """
        Analyze feedback to identify learning patterns.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of learned patterns
        """
        try:
            # Query Neo4j for feedback patterns
            query = """
            MATCH (f:Feedback)-[:FEEDBACK_ON_RESULT]->(ar:AnalysisResult)
            WHERE f.timestamp > datetime() - duration({days: $days})
            WITH ar.category AS category, f.type AS feedback_type, count(*) AS count
            WHERE count >= 3
            RETURN category, feedback_type, count
            ORDER BY count DESC
            """
            
            results = self.neo4j.execute_query(query, {"days": days})
            
            patterns = []
            for result in results:
                category = result["category"]
                feedback_type = result["feedback_type"]
                count = result["count"]
                
                # Create pattern
                pattern_id = f"{category}_{feedback_type}"
                pattern = LearningPattern(
                    pattern_id=pattern_id,
                    pattern_type="category_feedback",
                    category=category,
                    pattern_description=f"{feedback_type} feedback for {category} category",
                    feedback_count=count,
                    confidence_multiplier=self._calculate_multiplier(feedback_type, count)
                )
                
                patterns.append(pattern)
                self.learning_patterns[pattern_id] = pattern
            
            return patterns
        except Exception as e:
            print(f"Error analyzing feedback patterns: {e}")
            return []
    
    def _calculate_multiplier(self, feedback_type: str, count: int) -> float:
        """Calculate confidence multiplier based on feedback"""
        # More negative feedback = lower confidence multiplier
        # More positive feedback = higher confidence multiplier
        base_multiplier = {
            "positive": 1.1,
            "negative": 0.9,
            "neutral": 1.0,
            "correction": 0.95,
            "ignored": 0.85
        }.get(feedback_type.lower(), 1.0)
        
        # Adjust based on count (more feedback = stronger signal)
        adjustment = min(count / 10.0, 0.2)  # Max 20% adjustment
        
        if feedback_type.lower() == "positive":
            return base_multiplier + adjustment
        elif feedback_type.lower() == "negative":
            return base_multiplier - adjustment
        else:
            return base_multiplier
    
    async def adjust_confidence(
        self,
        result: AnalysisResult,
        feedback_stats: Optional[Dict] = None
    ) -> float:
        """
        Adjust confidence score based on feedback.
        
        Args:
            result: Analysis result to adjust
            feedback_stats: Optional pre-computed feedback stats
            
        Returns:
            Adjusted confidence score
        """
        if not feedback_stats:
            # Get feedback stats if not provided
            from ..learning.feedback_collector import FeedbackCollector
            collector = FeedbackCollector(neo4j_conn=self.neo4j, redis_client=self.redis)
            feedback_stats = await collector.get_feedback_stats(
                result.metadata.get("analysis_result_id", "")
            )
        
        if not feedback_stats or feedback_stats.get("total_feedback", 0) == 0:
            # No feedback, return original confidence
            return result.confidence
        
        # Get pattern multiplier
        pattern_id = f"{result.category.value}_{result.priority.value}"
        pattern = self.learning_patterns.get(pattern_id)
        
        multiplier = pattern.confidence_multiplier if pattern else 1.0
        
        # Adjust based on feedback ratio
        positive_ratio = feedback_stats.get("positive_ratio", 0.5)
        
        # If positive ratio is high, increase confidence
        # If positive ratio is low, decrease confidence
        ratio_adjustment = (positive_ratio - 0.5) * 0.2  # Max ±10% adjustment
        
        # Apply adjustments
        adjusted = result.confidence * multiplier + ratio_adjustment
        
        # Clamp to valid range
        return max(0.0, min(1.0, adjusted))
    
    async def learn_from_false_positives(
        self,
        category: str,
        file_pattern: Optional[str] = None,
        code_pattern: Optional[str] = None
    ) -> LearningPattern:
        """
        Learn pattern from false positives (negative feedback).
        
        Args:
            category: Analysis category
            file_pattern: File path pattern
            code_pattern: Code pattern
            
        Returns:
            Learning pattern
        """
        pattern_id = f"fp_{category}_{datetime.now().timestamp()}"
        
        pattern = LearningPattern(
            pattern_id=pattern_id,
            pattern_type="false_positive",
            category=category,
            pattern_description=f"False positive pattern for {category}",
            file_pattern=file_pattern,
            code_pattern=code_pattern,
            confidence_multiplier=0.7,  # Reduce confidence for this pattern
            should_apply=True
        )
        
        self.learning_patterns[pattern_id] = pattern
        return pattern
    
    async def learn_from_false_negatives(
        self,
        category: str,
        file_pattern: Optional[str] = None,
        code_pattern: Optional[str] = None
    ) -> LearningPattern:
        """
        Learn pattern from false negatives (missed issues).
        
        Args:
            category: Analysis category
            file_pattern: File path pattern
            code_pattern: Code pattern
            
        Returns:
            Learning pattern
        """
        pattern_id = f"fn_{category}_{datetime.now().timestamp()}"
        
        pattern = LearningPattern(
            pattern_id=pattern_id,
            pattern_type="false_negative",
            category=category,
            pattern_description=f"False negative pattern for {category}",
            file_pattern=file_pattern,
            code_pattern=code_pattern,
            confidence_multiplier=1.2,  # Increase confidence for this pattern
            should_apply=True
        )
        
        self.learning_patterns[pattern_id] = pattern
        return pattern
    
    async def get_category_adjustments(self) -> Dict[str, float]:
        """
        Get confidence adjustments by category based on feedback.
        
        Returns:
            Dictionary mapping category to adjustment multiplier
        """
        adjustments = {}
        
        try:
            query = """
            MATCH (f:Feedback)-[:FEEDBACK_ON_RESULT]->(ar:AnalysisResult)
            WITH ar.category AS category, 
                 sum(CASE WHEN f.type = 'positive' THEN 1 ELSE 0 END) AS positive,
                 sum(CASE WHEN f.type = 'negative' THEN 1 ELSE 0 END) AS negative,
                 count(*) AS total
            WHERE total >= 5
            RETURN category, 
                   toFloat(positive) / toFloat(total) AS positive_ratio,
                   toFloat(negative) / toFloat(total) AS negative_ratio
            """
            
            results = self.neo4j.execute_query(query)
            
            for result in results:
                category = result["category"]
                positive_ratio = result.get("positive_ratio", 0.5)
                negative_ratio = result.get("negative_ratio", 0.5)
                
                # Calculate multiplier
                # High positive ratio = increase confidence
                # High negative ratio = decrease confidence
                multiplier = 1.0 + (positive_ratio - negative_ratio) * 0.3
                adjustments[category] = max(0.7, min(1.3, multiplier))
        except Exception as e:
            print(f"Error getting category adjustments: {e}")
        
        return adjustments
    
    async def should_apply_pattern(
        self,
        result: AnalysisResult,
        pattern: LearningPattern
    ) -> bool:
        """Check if a learning pattern should be applied to a result"""
        if not pattern.should_apply:
            return False
        
        # Check category match
        if pattern.category != result.category.value:
            return False
        
        # Check file pattern match
        if pattern.file_pattern:
            import re
            if not re.search(pattern.file_pattern, result.location.file_path):
                return False
        
        # Check code pattern match
        if pattern.code_pattern and result.code_snippet:
            import re
            if not re.search(pattern.code_pattern, result.code_snippet):
                return False
        
        # Check confidence range
        if pattern.confidence_range:
            min_conf, max_conf = pattern.confidence_range
            if not (min_conf <= result.confidence <= max_conf):
                return False
        
        return True


