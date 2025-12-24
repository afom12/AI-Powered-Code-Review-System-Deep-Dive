"""GitHub integration module"""

from typing import Dict, Optional
from typing import List
from datetime import datetime
from ..context.github_client import GitHubClient
from ..models.review import CodeReviewRequest
from ..models.analysis import AnalysisResult


class GitHubIntegration:
    """Handles GitHub-specific integrations"""
    
    def __init__(self, token: str):
        self.client = GitHubClient(token)
    
    async def create_review_request(
        self, 
        owner: str, 
        repo_name: str, 
        pr_number: int
    ) -> CodeReviewRequest:
        """
        Create a CodeReviewRequest from GitHub PR.
        
        Args:
            owner: Repository owner
            repo_name: Repository name
            pr_number: Pull request number
            
        Returns:
            CodeReviewRequest object
        """
        # Get repository info
        repo = self.client.get_repository(owner, repo_name)
        
        # Get PR details
        pr_details = self.client.get_pr_details(owner, repo_name, pr_number)
        
        # Get file diffs
        diffs = self.client.get_pr_diff(owner, repo_name, pr_number)
        
        # Get commits
        commits = self.client.get_commits(owner, repo_name, pr_number)
        
        # Get related issues
        issues = self.client.get_related_issues(owner, repo_name, pr_number)
        
        # Get related PRs
        related_prs = self.client.get_related_prs(owner, repo_name, pr_number)
        
        # Create request
        request = CodeReviewRequest(
            pr_id=pr_details["id"],
            pr_number=pr_details["number"],
            title=pr_details["title"],
            description=pr_details["description"],
            repo=repo,
            base_branch=pr_details["base_branch"],
            head_branch=pr_details["head_branch"],
            author=pr_details["author"],
            diff=diffs,
            commit_history=commits,
            related_issues=issues,
            related_prs=related_prs,
            labels=pr_details["labels"],
            created_at=pr_details["created_at"],
            updated_at=pr_details["updated_at"]
        )
        
        return request
    
    async def post_review_comments(
        self,
        owner: str,
        repo_name: str,
        pr_number: int,
        results: List[AnalysisResult],
        max_comments: int = 50
    ) -> int:
        """
        Post analysis results as GitHub review comments.
        
        Args:
            owner: Repository owner
            repo_name: Repository name
            pr_number: Pull request number
            results: List of AnalysisResult objects
            max_comments: Maximum number of comments to post
            
        Returns:
            Number of comments posted
        """
        posted_count = 0
        
        # Get PR commits for review comments
        commits = self.client.get_commits(owner, repo_name, pr_number)
        if not commits:
            return 0
        
        latest_commit_sha = commits[0].sha if commits else None
        
        # Post comments (limit to max_comments)
        for result in results[:max_comments]:
            try:
                comment_body = self._format_comment(result)
                
                # Generate analysis result ID for tracking
                analysis_result_id = result.metadata.get(
                    "analysis_result_id",
                    f"{result.category.value}_{result.location.file_path}_{result.location.line_start}_{hash(result.title)}"
                )
                result.metadata["analysis_result_id"] = analysis_result_id
                
                # Try to post as review comment
                if latest_commit_sha:
                    comment = self.client.post_review_comment(
                        owner=owner,
                        name=repo_name,
                        pr_number=pr_number,
                        body=comment_body,
                        commit_id=latest_commit_sha,
                        path=result.location.file_path,
                        line=result.location.line_start
                    )
                else:
                    # Fallback to regular comment
                    comment = self.client.post_comment(
                        owner=owner,
                        name=repo_name,
                        pr_number=pr_number,
                        comment=comment_body
                    )
                
                # Store comment ID -> analysis result ID mapping for feedback tracking
                # (In production, store this in Redis or database)
                if hasattr(comment, 'id'):
                    result.metadata["comment_id"] = comment.id
                
                posted_count += 1
            except Exception as e:
                print(f"Error posting comment: {e}")
                continue
        
        return posted_count
    
    def _format_comment(self, result) -> str:
        """Format analysis result as GitHub comment"""
        emoji_map = {
            "security": "🔒",
            "bug": "🐛",
            "performance": "⚡",
            "architecture": "🏗️",
            "test": "🧪",
            "code_quality": "✨",
            "style": "💅",
            "business_logic": "💼",
        }
        
        emoji = emoji_map.get(result.category.value, "💡")
        priority_badge = f"**[{result.priority.value.upper()}]**" if result.priority != "info" else ""
        
        # Generate analysis result ID for feedback tracking
        analysis_result_id = result.metadata.get(
            "analysis_result_id",
            f"{result.category.value}_{result.location.file_path}_{result.location.line_start}_{hash(result.title)}"
        )
        
        comment = f"""{emoji} **{result.title}** {priority_badge}

{result.description}

**Suggestion:** {result.suggestion}

**Confidence:** {result.confidence:.0%}"""
        
        if result.evidence:
            comment += "\n\n**Related:**\n"
            for evidence in result.evidence[:3]:
                comment += f"- {evidence}\n"
        
        if result.code_snippet:
            comment += f"\n```\n{result.code_snippet[:200]}\n```"
        
        # Add feedback collection footer
        comment += f"""

---
💬 **Was this helpful?** React with 👍 or 👎 to help improve future reviews.
<!-- analysis_result_id: {analysis_result_id} -->"""
        
        return comment

