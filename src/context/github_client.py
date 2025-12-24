"""GitHub API client for fetching context"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from github import Github
from github.Repository import Repository as GHRepository
from github.PullRequest import PullRequest
from github.Issue import Issue as GHIssue
from ..models.review import Repository, Commit, Issue, FileDiff


class GitHubClient:
    """Client for interacting with GitHub API"""
    
    def __init__(self, token: str):
        self.github = Github(token)
    
    def get_repository(self, owner: str, name: str) -> Repository:
        """Get repository information"""
        repo = self.github.get_repo(f"{owner}/{name}")
        
        languages = {}
        try:
            languages = repo.get_languages()
        except Exception:
            pass
        
        return Repository(
            owner=owner,
            name=name,
            full_name=repo.full_name,
            default_branch=repo.default_branch,
            language=repo.language,
            languages=languages
        )
    
    def get_pr_details(self, owner: str, name: str, pr_number: int) -> Dict:
        """Get pull request details"""
        repo = self.github.get_repo(f"{owner}/{name}")
        pr = repo.get_pull(pr_number)
        
        return {
            "id": str(pr.id),
            "number": pr.number,
            "title": pr.title,
            "description": pr.body,
            "author": pr.user.login,
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "state": pr.state,
            "created_at": pr.created_at,
            "updated_at": pr.updated_at,
            "labels": [label.name for label in pr.labels],
        }
    
    def get_pr_diff(self, owner: str, name: str, pr_number: int) -> List[FileDiff]:
        """Get file diffs for a pull request"""
        repo = self.github.get_repo(f"{owner}/{name}")
        pr = repo.get_pull(pr_number)
        
        files = pr.get_files()
        diffs = []
        
        for file in files:
            # Detect language from file extension
            language = self._detect_language(file.filename)
            
            diff = FileDiff(
                file_path=file.filename,
                additions=file.additions,
                deletions=file.deletions,
                changes=file.changes,
                diff=file.patch or "",
                status=file.status,
                language=language
            )
            diffs.append(diff)
        
        return diffs
    
    def get_commits(self, owner: str, name: str, pr_number: int) -> List[Commit]:
        """Get commits for a pull request"""
        repo = self.github.get_repo(f"{owner}/{name}")
        pr = repo.get_pull(pr_number)
        
        commits = []
        for commit in pr.get_commits():
            commit_obj = commit.commit
            commits.append(Commit(
                sha=commit.sha,
                message=commit_obj.message,
                author=commit_obj.author.name,
                timestamp=commit_obj.author.date,
                files_changed=[f.filename for f in commit.files],
                additions=sum(f.additions for f in commit.files),
                deletions=sum(f.deletions for f in commit.files)
            ))
        
        return commits
    
    def get_related_prs(self, owner: str, name: str, pr_number: int, days: int = 30) -> List[str]:
        """Get related PRs from the last N days"""
        repo = self.github.get_repo(f"{owner}/{name}")
        cutoff_date = datetime.now() - timedelta(days=days)
        
        related_prs = []
        for pr in repo.get_pulls(state="all"):
            if pr.created_at < cutoff_date:
                break
            if pr.number != pr_number:
                related_prs.append(str(pr.number))
        
        return related_prs[:10]  # Limit to 10 most recent
    
    def get_related_issues(self, owner: str, name: str, pr_number: int) -> List[Issue]:
        """Get issues related to the PR"""
        repo = self.github.get_repo(f"{owner}/{name}")
        pr = repo.get_pull(pr_number)
        
        issues = []
        
        # Get issues mentioned in PR description
        if pr.body:
            import re
            issue_refs = re.findall(r'#(\d+)', pr.body)
            for issue_num in issue_refs:
                try:
                    issue_obj = repo.get_issue(int(issue_num))
                    issues.append(Issue(
                        id=str(issue_obj.number),
                        title=issue_obj.title,
                        body=issue_obj.body,
                        labels=[label.name for label in issue_obj.labels],
                        state=issue_obj.state,
                        created_at=issue_obj.created_at,
                        closed_at=issue_obj.closed_at,
                        related_prs=[str(pr.number)]
                    ))
                except Exception:
                    pass
        
        return issues
    
    def post_comment(self, owner: str, name: str, pr_number: int, comment: str):
        """Post a comment on a pull request"""
        repo = self.github.get_repo(f"{owner}/{name}")
        pr = repo.get_pull(pr_number)
        return pr.create_issue_comment(comment)
    
    def post_review_comment(
        self, 
        owner: str, 
        name: str, 
        pr_number: int, 
        body: str, 
        commit_id: str, 
        path: str, 
        line: int
    ):
        """Post a review comment on a specific line"""
        repo = self.github.get_repo(f"{owner}/{name}")
        pr = repo.get_pull(pr_number)
        
        try:
            return pr.create_review_comment(
                body=body,
                commit_id=commit_id,
                path=path,
                line=line
            )
        except Exception as e:
            # Fallback to regular comment if review comment fails
            return pr.create_issue_comment(f"**{path}:{line}**\n\n{body}")
    
    def _detect_language(self, filename: str) -> Optional[str]:
        """Detect programming language from filename"""
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
            ".sh": "shell",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
        }
        
        for ext, lang in extension_map.items():
            if filename.endswith(ext):
                return lang
        
        return None


