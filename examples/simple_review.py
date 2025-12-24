"""
Simple example of using the code review system programmatically.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.integrations.github import GitHubIntegration
from src.engine.review_engine import ReviewEngine


async def review_pr_example():
    """Example: Review a specific PR"""
    
    # Initialize components
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN not set in environment")
        return
    
    github_integration = GitHubIntegration(github_token)
    review_engine = ReviewEngine()
    
    # Example: Review PR #1 in a repository
    owner = "octocat"  # Replace with actual owner
    repo_name = "Hello-World"  # Replace with actual repo
    pr_number = 1  # Replace with actual PR number
    
    print(f"Reviewing PR #{pr_number} in {owner}/{repo_name}...")
    
    try:
        # Create review request
        request = await github_integration.create_review_request(
            owner=owner,
            repo_name=repo_name,
            pr_number=pr_number
        )
        
        print(f"PR Title: {request.title}")
        print(f"Files changed: {len(request.diff)}")
        print(f"Commits: {len(request.commit_history)}")
        
        # Perform review
        results = await review_engine.review(request)
        
        print(f"\nFound {len(results)} issues:")
        for i, result in enumerate(results[:10], 1):  # Show top 10
            print(f"\n{i}. [{result.category.value}] {result.title}")
            print(f"   Priority: {result.priority.value}")
            print(f"   Confidence: {result.confidence:.0%}")
            print(f"   Location: {result.location.file_path}:{result.location.line_start}")
            print(f"   Suggestion: {result.suggestion}")
        
        # Optionally post comments
        post_comments = input("\nPost comments to PR? (y/n): ")
        if post_comments.lower() == 'y':
            comments_posted = await github_integration.post_review_comments(
                owner=owner,
                repo_name=repo_name,
                pr_number=pr_number,
                results=results
            )
            print(f"Posted {comments_posted} comments")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(review_pr_example())



