"""Collects and stores feedback from reviewers"""

from typing import List, Optional, Dict
from datetime import datetime
from ..models.feedback import Feedback, FeedbackType, FeedbackSource
from ..utils.database import Neo4jConnection
import redis
import json
import os


class FeedbackCollector:
    """Collects feedback from various sources"""
    
    def __init__(
        self,
        neo4j_conn: Optional[Neo4jConnection] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        self.neo4j = neo4j_conn or Neo4jConnection()
        self.redis = redis_client or self._init_redis()
    
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
    
    async def collect_feedback(
        self,
        feedback: Feedback
    ) -> bool:
        """
        Collect and store feedback.
        
        Args:
            feedback: Feedback object to store
            
        Returns:
            True if stored successfully
        """
        try:
            # Store in Neo4j
            await self._store_in_neo4j(feedback)
            
            # Store in Redis for quick access
            await self._store_in_redis(feedback)
            
            return True
        except Exception as e:
            print(f"Error collecting feedback: {e}")
            return False
    
    async def _store_in_neo4j(self, feedback: Feedback):
        """Store feedback in Neo4j"""
        try:
            # Create feedback node
            query = """
            MERGE (f:Feedback {id: $id})
            SET f.type = $type,
                f.source = $source,
                f.reviewer = $reviewer,
                f.timestamp = $timestamp,
                f.category = $category,
                f.file_path = $file_path,
                f.line_number = $line_number,
                f.comment = $comment,
                f.correction = $correction
            WITH f
            MATCH (pr:PR {id: $pr_id})
            MERGE (f)-[:FEEDBACK_ON]->(pr)
            MERGE (ar:AnalysisResult {id: $analysis_result_id})
            MERGE (f)-[:FEEDBACK_ON_RESULT]->(ar)
            RETURN f
            """
            
            self.neo4j.execute_query(query, {
                "id": feedback.id or f"{feedback.pr_id}_{feedback.analysis_result_id}_{datetime.now().timestamp()}",
                "type": feedback.feedback_type.value,
                "source": feedback.source.value,
                "reviewer": feedback.reviewer,
                "timestamp": feedback.timestamp.isoformat(),
                "category": feedback.category,
                "file_path": feedback.file_path,
                "line_number": feedback.line_number,
                "comment": feedback.comment,
                "correction": feedback.correction,
                "pr_id": feedback.pr_id,
                "analysis_result_id": feedback.analysis_result_id
            })
        except Exception as e:
            print(f"Error storing feedback in Neo4j: {e}")
    
    async def _store_in_redis(self, feedback: Feedback):
        """Store feedback in Redis for quick access"""
        if not self.redis:
            return
        
        try:
            # Store feedback by analysis result ID
            key = f"feedback:{feedback.analysis_result_id}"
            feedback_data = feedback.model_dump_json()
            self.redis.lpush(key, feedback_data)
            self.redis.expire(key, 86400 * 30)  # Expire after 30 days
            
            # Store stats
            stats_key = f"feedback:stats:{feedback.analysis_result_id}"
            self.redis.hincrby(stats_key, f"{feedback.feedback_type.value}_count", 1)
            self.redis.hincrby(stats_key, "total_count", 1)
            self.redis.expire(stats_key, 86400 * 30)
        except Exception as e:
            print(f"Error storing feedback in Redis: {e}")
    
    async def collect_from_github_reaction(
        self,
        pr_id: str,
        pr_number: int,
        repo_owner: str,
        repo_name: str,
        analysis_result_id: str,
        reaction: str,  # "+1", "-1", "heart", etc.
        reviewer: str,
        category: str,
        file_path: str,
        line_number: int
    ) -> Feedback:
        """Collect feedback from GitHub reaction"""
        # Map reactions to feedback types
        reaction_map = {
            "+1": FeedbackType.POSITIVE,
            "thumbs_up": FeedbackType.POSITIVE,
            "-1": FeedbackType.NEGATIVE,
            "thumbs_down": FeedbackType.NEGATIVE,
            "heart": FeedbackType.POSITIVE,
            "hooray": FeedbackType.POSITIVE,
        }
        
        feedback_type = reaction_map.get(reaction.lower(), FeedbackType.NEUTRAL)
        
        feedback = Feedback(
            analysis_result_id=analysis_result_id,
            pr_id=pr_id,
            pr_number=pr_number,
            repo_owner=repo_owner,
            repo_name=repo_name,
            feedback_type=feedback_type,
            source=FeedbackSource.GITHUB_REACTION,
            reviewer=reviewer,
            category=category,
            file_path=file_path,
            line_number=line_number,
            metadata={"reaction": reaction}
        )
        
        await self.collect_feedback(feedback)
        return feedback
    
    async def collect_from_comment_reply(
        self,
        pr_id: str,
        pr_number: int,
        repo_owner: str,
        repo_name: str,
        analysis_result_id: str,
        reply_text: str,
        reviewer: str,
        category: str,
        file_path: str,
        line_number: int
    ) -> Feedback:
        """Collect feedback from comment reply"""
        # Analyze reply text to determine feedback type
        reply_lower = reply_text.lower()
        
        if any(word in reply_lower for word in ["thanks", "good", "helpful", "correct", "agree"]):
            feedback_type = FeedbackType.POSITIVE
        elif any(word in reply_lower for word in ["wrong", "incorrect", "not", "disagree", "false"]):
            feedback_type = FeedbackType.NEGATIVE
        elif any(word in reply_lower for word in ["actually", "should be", "better", "instead"]):
            feedback_type = FeedbackType.CORRECTION
            # Try to extract correction
            correction = reply_text
        else:
            feedback_type = FeedbackType.NEUTRAL
            correction = None
        
        feedback = Feedback(
            analysis_result_id=analysis_result_id,
            pr_id=pr_id,
            pr_number=pr_number,
            repo_owner=repo_owner,
            repo_name=repo_name,
            feedback_type=feedback_type,
            source=FeedbackSource.COMMENT_REPLY,
            reviewer=reviewer,
            comment=reply_text,
            correction=correction,
            category=category,
            file_path=file_path,
            line_number=line_number
        )
        
        await self.collect_feedback(feedback)
        return feedback
    
    async def collect_auto_detected(
        self,
        pr_id: str,
        pr_number: int,
        repo_owner: str,
        repo_name: str,
        analysis_result_id: str,
        category: str,
        file_path: str,
        line_number: int,
        was_fixed: bool  # Was the issue fixed in the PR?
    ) -> Feedback:
        """Auto-detect feedback based on whether issue was fixed"""
        feedback_type = FeedbackType.POSITIVE if was_fixed else FeedbackType.NEGATIVE
        
        feedback = Feedback(
            analysis_result_id=analysis_result_id,
            pr_id=pr_id,
            pr_number=pr_number,
            repo_owner=repo_owner,
            repo_name=repo_name,
            feedback_type=feedback_type,
            source=FeedbackSource.AUTO_DETECTED,
            reviewer="system",
            category=category,
            file_path=file_path,
            line_number=line_number,
            metadata={"auto_detected": True, "was_fixed": was_fixed}
        )
        
        await self.collect_feedback(feedback)
        return feedback
    
    async def get_feedback_stats(self, analysis_result_id: str) -> Dict:
        """Get feedback statistics for an analysis result"""
        if not self.redis:
            return {}
        
        try:
            stats_key = f"feedback:stats:{analysis_result_id}"
            stats = self.redis.hgetall(stats_key)
            
            total = int(stats.get("total_count", 0))
            positive = int(stats.get("positive_count", 0))
            negative = int(stats.get("negative_count", 0))
            neutral = int(stats.get("neutral_count", 0))
            correction = int(stats.get("correction_count", 0))
            
            return {
                "total_feedback": total,
                "positive_count": positive,
                "negative_count": negative,
                "neutral_count": neutral,
                "correction_count": correction,
                "positive_ratio": positive / total if total > 0 else 0.0
            }
        except Exception as e:
            print(f"Error getting feedback stats: {e}")
            return {}


