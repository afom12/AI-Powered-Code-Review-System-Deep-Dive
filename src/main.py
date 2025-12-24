"""FastAPI application for code review system"""

import os
from typing import Dict, Optional
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings
from .integrations.webhook import WebhookHandler
from .integrations.github import GitHubIntegration
from .engine.review_engine import ReviewEngine
from .utils.database import Neo4jConnection, QdrantConnection
from .utils.embeddings import CodeEmbedder


class Settings(BaseSettings):
    """Application settings"""
    github_token: str
    webhook_secret: Optional[str] = None
    min_confidence_threshold: float = 0.6
    max_comments_per_pr: int = 50
    enable_learning_mode: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    environment: str = "development"
    
    # Database settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "your_password_change_this"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # AI/ML settings
    use_local_models: bool = False
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Initialize settings
settings = Settings()

# Initialize FastAPI app
app = FastAPI(
    title="AI-Powered Code Review System",
    description="Context-aware code review system with AI analysis",
    version="0.1.0"
)

# Initialize database connections
neo4j_conn = Neo4jConnection(
    uri=settings.neo4j_uri,
    user=settings.neo4j_user,
    password=settings.neo4j_password
)

qdrant_conn = QdrantConnection(
    host=settings.qdrant_host,
    port=settings.qdrant_port
)

# Initialize embedding model
embedder = CodeEmbedder(
    model_name=settings.embedding_model,
    use_local=settings.use_local_models
)

# Initialize review engine
review_engine = ReviewEngine(
    min_confidence=settings.min_confidence_threshold,
    max_results=settings.max_comments_per_pr,
    enable_learning=settings.enable_learning,
    neo4j_conn=neo4j_conn,
    qdrant_conn=qdrant_conn,
    embedder=embedder
)

# Initialize components
webhook_handler = WebhookHandler(
    github_token=settings.github_token,
    webhook_secret=settings.webhook_secret,
    review_engine=review_engine
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AI-Powered Code Review System",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    GitHub webhook endpoint.
    Handles pull request events and triggers code review.
    """
    # Get event type
    event_type = x_github_event
    
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")
    
    # Get payload
    payload = await request.body()
    
    # Verify signature if secret is configured
    if settings.webhook_secret and x_hub_signature_256:
        if not webhook_handler.verify_signature(payload, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse JSON payload
    import json
    try:
        event_data = json.loads(payload.decode())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    
    # Handle pull request events
    if event_type == "pull_request":
        result = await webhook_handler.handle_pr_event(event_data)
        return JSONResponse(content=result)
    
    # Handle other events (ping, etc.)
    elif event_type == "ping":
        return {"status": "pong"}
    
    else:
        return {"status": "ignored", "event_type": event_type}


@app.post("/review/{owner}/{repo}/{pr_number}")
async def review_pr(
    owner: str,
    repo: str,
    pr_number: int
):
    """
    Manually trigger review for a specific PR.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
    """
    try:
        github_integration = GitHubIntegration(settings.github_token)
        
        # Create review request
        request = await github_integration.create_review_request(
            owner=owner,
            repo_name=repo,
            pr_number=pr_number
        )
        
        # Perform review
        results = await review_engine.review(request)
        
        # Post comments
        comments_posted = await github_integration.post_review_comments(
            owner=owner,
            repo_name=repo,
            pr_number=pr_number,
            results=results
        )
        
        return {
            "status": "success",
            "pr_number": pr_number,
            "results_count": len(results),
            "comments_posted": comments_posted,
            "results": [
                {
                    "category": r.category.value,
                    "priority": r.priority.value,
                    "confidence": r.confidence,
                    "title": r.title,
                    "location": {
                        "file": r.location.file_path,
                        "line": r.location.line_start
                    }
                }
                for r in results[:10]  # Return top 10
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "analyzers": len(review_engine.analyzers),
        "min_confidence": review_engine.min_confidence,
        "max_results": review_engine.max_results,
        "learning_enabled": review_engine.enable_learning
    }


# Initialize feedback collector
feedback_collector = FeedbackCollector(neo4j_conn=neo4j_conn)


@app.post("/feedback")
async def submit_feedback(feedback: Feedback):
    """
    Submit feedback on an analysis result.
    
    This endpoint allows manual feedback submission.
    """
    try:
        success = await feedback_collector.collect_feedback(feedback)
        if success:
            return {"status": "success", "message": "Feedback collected"}
        else:
            raise HTTPException(status_code=500, detail="Failed to collect feedback")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback/reaction")
async def submit_reaction_feedback(
    pr_id: str,
    pr_number: int,
    repo_owner: str,
    repo_name: str,
    analysis_result_id: str,
    reaction: str,
    reviewer: str,
    category: str,
    file_path: str,
    line_number: int
):
    """Submit feedback from GitHub reaction"""
    try:
        feedback = await feedback_collector.collect_from_github_reaction(
            pr_id=pr_id,
            pr_number=pr_number,
            repo_owner=repo_owner,
            repo_name=repo_name,
            analysis_result_id=analysis_result_id,
            reaction=reaction,
            reviewer=reviewer,
            category=category,
            file_path=file_path,
            line_number=line_number
        )
        return {"status": "success", "feedback_id": feedback.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/feedback/stats/{analysis_result_id}")
async def get_feedback_stats(analysis_result_id: str):
    """Get feedback statistics for an analysis result"""
    try:
        stats = await feedback_collector.get_feedback_stats(analysis_result_id)
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/github/issue_comment")
async def github_comment_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    GitHub webhook for issue comments (replies to review comments).
    Collects feedback from comment replies.
    """
    if not x_github_event or x_github_event != "issue_comment":
        return {"status": "ignored"}
    
    # Verify signature if configured
    payload = await request.body()
    if settings.webhook_secret and x_hub_signature_256:
        if not webhook_handler.verify_signature(payload, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    import json
    event_data = json.loads(payload.decode())
    
    # Check if this is a reply to our review comment
    comment = event_data.get("comment", {})
    issue = event_data.get("issue", {})
    
    # Extract PR info from issue
    if "pull_request" in issue.get("html_url", ""):
        # This is a PR comment
        try:
            # Try to extract analysis result ID from parent comment
            # (In production, you'd store comment ID -> analysis result ID mapping)
            # For now, we'll use a simple heuristic
            
            await feedback_collector.collect_from_comment_reply(
                pr_id=f"{event_data.get('repository', {}).get('owner', {}).get('login')}/"
                      f"{event_data.get('repository', {}).get('name')}#{issue.get('number')}",
                pr_number=issue.get("number"),
                repo_owner=event_data.get("repository", {}).get("owner", {}).get("login"),
                repo_name=event_data.get("repository", {}).get("name"),
                analysis_result_id="unknown",  # Would need to lookup from comment
                reply_text=comment.get("body", ""),
                reviewer=comment.get("user", {}).get("login", "unknown"),
                category="unknown",
                file_path="unknown",
                line_number=0
            )
        except Exception as e:
            print(f"Error processing comment feedback: {e}")
    
    return {"status": "processed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development"
    )


