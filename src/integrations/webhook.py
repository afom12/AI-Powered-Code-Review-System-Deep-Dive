"""Webhook handler for GitHub events"""

from typing import Dict, Optional
import hmac
import hashlib
from ..integrations.github import GitHubIntegration
from ..engine.review_engine import ReviewEngine


class WebhookHandler:
    """Handles GitHub webhook events"""
    
    def __init__(
        self,
        github_token: str,
        webhook_secret: Optional[str] = None,
        review_engine: Optional[ReviewEngine] = None
    ):
        self.github_integration = GitHubIntegration(github_token)
        self.review_engine = review_engine or ReviewEngine()
        self.webhook_secret = webhook_secret
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        if not self.webhook_secret:
            return True  # Skip verification if no secret configured
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    async def handle_pr_event(self, event: Dict) -> Dict:
        """
        Handle pull request webhook event.
        
        Args:
            event: GitHub webhook event payload
            
        Returns:
            Result dictionary with status and details
        """
        action = event.get("action")
        pr_data = event.get("pull_request", {})
        
        # Only process opened, synchronize, or reopened PRs
        if action not in ["opened", "synchronize", "reopened"]:
            return {"status": "skipped", "reason": f"Action '{action}' not processed"}
        
        # Extract PR information
        repo = event.get("repository", {})
        owner = repo.get("owner", {}).get("login") or repo.get("owner", {}).get("name")
        repo_name = repo.get("name")
        pr_number = pr_data.get("number")
        
        if not all([owner, repo_name, pr_number]):
            return {"status": "error", "reason": "Missing required PR information"}
        
        try:
            # Create review request
            request = await self.github_integration.create_review_request(
                owner=owner,
                repo_name=repo_name,
                pr_number=pr_number
            )
            
            # Perform review
            results = await self.review_engine.review(request)
            
            # Post comments
            comments_posted = await self.github_integration.post_review_comments(
                owner=owner,
                repo_name=repo_name,
                pr_number=pr_number,
                results=results
            )
            
            return {
                "status": "success",
                "pr_number": pr_number,
                "results_count": len(results),
                "comments_posted": comments_posted
            }
        
        except Exception as e:
            return {
                "status": "error",
                "reason": str(e)
            }


