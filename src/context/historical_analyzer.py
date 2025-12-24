"""Analyzes historical patterns from past PRs and issues"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ..models.review import CodeReviewRequest
from ..models.analysis import AnalysisResult
from ..utils.database import Neo4jConnection, QdrantConnection
from ..utils.embeddings import CodeEmbedder
from ..utils.code_parser import CodeParser


class HistoricalAnalyzer:
    """
    Analyzes historical data to find patterns.
    Uses Neo4j for dependency tracking and Qdrant for code similarity search.
    """
    
    def __init__(
        self,
        github_client: Optional[object] = None,
        neo4j_conn: Optional[Neo4jConnection] = None,
        qdrant_conn: Optional[QdrantConnection] = None,
        embedder: Optional[CodeEmbedder] = None
    ):
        self.github_client = github_client
        self.neo4j = neo4j_conn or Neo4jConnection()
        self.qdrant = qdrant_conn or QdrantConnection()
        self.embedder = embedder or CodeEmbedder()
        self.code_parser = CodeParser()
        
        # Try to connect to databases (non-blocking)
        try:
            self.neo4j.connect()
        except Exception as e:
            print(f"Warning: Neo4j connection failed: {e}")
        
        try:
            self.qdrant.connect()
        except Exception as e:
            print(f"Warning: Qdrant connection failed: {e}")
    
    async def store_pr_data(self, request: CodeReviewRequest):
        """Store PR data in databases for future analysis"""
        pr_id = f"{request.repo.owner}/{request.repo.name}#{request.pr_number}"
        
        # Store in Neo4j
        try:
            self.neo4j.create_pr_node({
                "id": pr_id,
                "number": request.pr_number,
                "title": request.title,
                "author": request.author,
                "repo_owner": request.repo.owner,
                "repo_name": request.repo.name,
                "created_at": request.created_at.isoformat() if request.created_at else None,
                "updated_at": request.updated_at.isoformat() if request.updated_at else None,
                "state": "open"
            })
            
            # Store file dependencies
            for file_diff in request.diff:
                if file_diff.status != "removed":
                    # Extract dependencies from code
                    dependencies = self._extract_dependencies(file_diff)
                    self.neo4j.create_file_dependency(
                        pr_id,
                        file_diff.file_path,
                        dependencies
                    )
        except Exception as e:
            print(f"Error storing PR in Neo4j: {e}")
        
        # Store embedding in Qdrant
        try:
            # Generate embedding for PR content
            file_paths = [fd.file_path for fd in request.diff]
            code_snippets = [fd.diff[:500] for fd in request.diff[:10]]  # Limit snippets
            
            embedding = self.embedder.embed_pr_content(
                title=request.title,
                description=request.description or "",
                file_paths=file_paths,
                code_snippets=code_snippets
            )
            
            self.qdrant.store_pr_embedding(
                pr_id=pr_id,
                embedding=embedding.tolist(),
                metadata={
                    "pr_number": request.pr_number,
                    "title": request.title,
                    "repo_owner": request.repo.owner,
                    "repo_name": request.repo.name,
                    "files": file_paths,
                    "created_at": request.created_at.isoformat() if request.created_at else None,
                    "author": request.author
                }
            )
        except Exception as e:
            print(f"Error storing PR embedding in Qdrant: {e}")
    
    def _extract_dependencies(self, file_diff) -> List[str]:
        """Extract file dependencies from code diff"""
        dependencies = []
        
        # Simple heuristic: look for import statements
        if file_diff.language == "python":
            import re
            imports = re.findall(r'from\s+(\S+)\s+import|import\s+(\S+)', file_diff.diff)
            for match in imports:
                module = match[0] or match[1]
                # Convert module to potential file path
                if module and not module.startswith('.'):
                    # Simple conversion (could be improved)
                    file_path = module.replace('.', '/') + '.py'
                    dependencies.append(file_path)
        
        return dependencies[:10]  # Limit dependencies
    
    async def find_similar_prs(
        self, 
        request: CodeReviewRequest, 
        days: int = 30
    ) -> List[Dict]:
        """Find similar PRs from history using vector similarity and file overlap"""
        similar_prs = []
        
        # Method 1: Vector similarity search using Qdrant
        try:
            # Generate embedding for current PR
            file_paths = [fd.file_path for fd in request.diff]
            code_snippets = [fd.diff[:500] for fd in request.diff[:10]]
            
            query_embedding = self.embedder.embed_pr_content(
                title=request.title,
                description=request.description or "",
                file_paths=file_paths,
                code_snippets=code_snippets
            )
            
            # Search for similar PRs
            qdrant_results = self.qdrant.search_similar_prs(
                query_embedding=query_embedding.tolist(),
                limit=10,
                score_threshold=0.6
            )
            
            for result in qdrant_results:
                # Filter by repository if needed
                if result.get("repo_owner") == request.repo.owner and \
                   result.get("repo_name") == request.repo.name:
                    similar_prs.append({
                        "pr_number": result["pr_number"],
                        "similarity_score": result["similarity_score"],
                        "reason": "Code similarity",
                        "method": "vector_search"
                    })
        except Exception as e:
            print(f"Error in Qdrant similarity search: {e}")
        
        # Method 2: File-based similarity using Neo4j
        try:
            file_paths = [fd.file_path for fd in request.diff if fd.status != "removed"]
            if file_paths:
                neo4j_results = self.neo4j.find_related_prs_by_files(file_paths, limit=10)
                
                for result in neo4j_results:
                    pr_id = result.get("pr_id", "")
                    if pr_id and f"{request.repo.owner}/{request.repo.name}#" in pr_id:
                        pr_number = result.get("pr_number")
                        if pr_number and pr_number != request.pr_number:
                            similar_prs.append({
                                "pr_number": str(pr_number),
                                "similarity_score": result.get("common_files", 0) / len(file_paths),
                                "reason": f"Modified {result.get('common_files', 0)} common files",
                                "method": "file_overlap"
                            })
        except Exception as e:
            print(f"Error in Neo4j file similarity search: {e}")
        
        # Fallback: Use GitHub API if databases unavailable
        if not similar_prs and self.github_client:
            try:
                related_prs = self.github_client.get_related_prs(
                    request.repo.owner,
                    request.repo.name,
                    request.pr_number,
                    days=days
                )
                
                for pr_num in related_prs[:5]:
                    similar_prs.append({
                        "pr_number": pr_num,
                        "similarity_score": 0.5,
                        "reason": "Recent PRs in same repo",
                        "method": "github_api"
                    })
            except Exception as e:
                print(f"Error in GitHub API fallback: {e}")
        
        # Deduplicate and sort by similarity score
        seen = set()
        unique_prs = []
        for pr in similar_prs:
            key = pr["pr_number"]
            if key not in seen:
                seen.add(key)
                unique_prs.append(pr)
        
        # Sort by similarity score descending
        unique_prs.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return unique_prs[:10]  # Return top 10
    
    async def find_bug_patterns(self, request: CodeReviewRequest) -> List[Dict]:
        """Find bug patterns from historical issues and PRs"""
        bug_patterns = []
        
        # Check related issues for bug patterns
        for issue in request.related_issues:
            if "bug" in issue.labels or "error" in issue.title.lower():
                bug_patterns.append({
                    "issue_id": issue.id,
                    "title": issue.title,
                    "pattern": "bug_report",
                    "relevance": 0.7,
                    "source": "related_issue"
                })
        
        # Search Neo4j for PRs that caused bugs (if we track this)
        try:
            # Look for PRs that were later associated with bug fixes
            query = """
            MATCH (pr:PR)-[:MODIFIES]->(file:File)
            WHERE file.path IN $file_paths
            AND pr.state = 'closed'
            RETURN DISTINCT pr.id AS pr_id, pr.title AS title, pr.number AS pr_number
            LIMIT 5
            """
            file_paths = [fd.file_path for fd in request.diff]
            if file_paths:
                results = self.neo4j.execute_query(query, {"file_paths": file_paths})
                for result in results:
                    bug_patterns.append({
                        "pr_id": result.get("pr_id"),
                        "pr_number": result.get("pr_number"),
                        "title": result.get("title", "Unknown"),
                        "pattern": "historical_bug",
                        "relevance": 0.6,
                        "source": "neo4j"
                    })
        except Exception as e:
            print(f"Error searching for bug patterns in Neo4j: {e}")
        
        return bug_patterns
    
    async def get_team_patterns(self, request: CodeReviewRequest) -> Dict:
        """Get team-specific patterns from historical data"""
        patterns = {
            "preferred_patterns": [],
            "anti_patterns": [],
            "recent_refactors": []
        }
        
        # Query Neo4j for team patterns
        try:
            # Find frequently modified files (potential refactoring areas)
            query = """
            MATCH (pr:PR)-[:MODIFIES]->(file:File)
            WHERE pr.repo_owner = $owner AND pr.repo_name = $repo
            WITH file, count(pr) AS modification_count
            WHERE modification_count > 3
            RETURN file.path AS file_path, modification_count
            ORDER BY modification_count DESC
            LIMIT 10
            """
            results = self.neo4j.execute_query(query, {
                "owner": request.repo.owner,
                "repo": request.repo.name
            })
            
            patterns["recent_refactors"] = [
                result["file_path"] for result in results
            ]
        except Exception as e:
            print(f"Error querying team patterns: {e}")
        
        return patterns
    
    def enhance_results_with_history(
        self, 
        results: List[AnalysisResult], 
        historical_data: Dict
    ) -> List[AnalysisResult]:
        """Enhance analysis results with historical evidence"""
        enhanced_results = []
        
        for result in results:
            # Add historical evidence if available
            if historical_data.get("similar_prs"):
                evidence_items = []
                for pr in historical_data["similar_prs"][:3]:
                    score = pr.get("similarity_score", 0)
                    method = pr.get("method", "unknown")
                    evidence_items.append(
                        f"Similar pattern in PR #{pr['pr_number']} "
                        f"(similarity: {score:.2f}, method: {method})"
                    )
                result.evidence.extend(evidence_items)
            
            if historical_data.get("bug_patterns"):
                evidence_items = []
                for bug in historical_data["bug_patterns"][:2]:
                    if bug.get("source") == "related_issue":
                        evidence_items.append(
                            f"Related to issue #{bug['issue_id']}: {bug['title']}"
                        )
                    elif bug.get("source") == "neo4j":
                        evidence_items.append(
                            f"Similar files modified in PR #{bug.get('pr_number', 'unknown')}: {bug['title']}"
                        )
                result.evidence.extend(evidence_items)
            
            enhanced_results.append(result)
        
        return enhanced_results

