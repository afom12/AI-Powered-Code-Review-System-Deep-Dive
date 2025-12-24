"""Database connection utilities for Neo4j and Qdrant"""

from typing import Optional
import os
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


class Neo4jConnection:
    """Neo4j graph database connection manager"""
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "your_password_change_this")
        self.driver = None
    
    def connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            return False
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
    
    def execute_query(self, query: str, parameters: Optional[dict] = None):
        """Execute a Cypher query"""
        if not self.driver:
            if not self.connect():
                raise ConnectionError("Failed to connect to Neo4j")
        
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def create_pr_node(self, pr_data: dict):
        """Create or update a PR node in Neo4j"""
        query = """
        MERGE (pr:PR {id: $pr_id})
        SET pr.number = $number,
            pr.title = $title,
            pr.author = $author,
            pr.repo_owner = $repo_owner,
            pr.repo_name = $repo_name,
            pr.created_at = $created_at,
            pr.updated_at = $updated_at,
            pr.state = $state
        RETURN pr
        """
        return self.execute_query(query, {
            "pr_id": pr_data["id"],
            "number": pr_data["number"],
            "title": pr_data["title"],
            "author": pr_data["author"],
            "repo_owner": pr_data["repo_owner"],
            "repo_name": pr_data["repo_name"],
            "created_at": pr_data.get("created_at"),
            "updated_at": pr_data.get("updated_at"),
            "state": pr_data.get("state", "open")
        })
    
    def create_file_dependency(self, pr_id: str, file_path: str, dependencies: list):
        """Create file dependency relationships"""
        query = """
        MATCH (pr:PR {id: $pr_id})
        MERGE (file:File {path: $file_path})
        MERGE (pr)-[:MODIFIES]->(file)
        
        WITH file
        UNWIND $dependencies AS dep
        MERGE (dep_file:File {path: dep})
        MERGE (file)-[:DEPENDS_ON]->(dep_file)
        """
        return self.execute_query(query, {
            "pr_id": pr_id,
            "file_path": file_path,
            "dependencies": dependencies
        })
    
    def find_related_prs_by_files(self, file_paths: list, limit: int = 10):
        """Find PRs that modified similar files"""
        query = """
        MATCH (pr:PR)-[:MODIFIES]->(file:File)
        WHERE file.path IN $file_paths
        WITH pr, count(file) AS common_files
        ORDER BY common_files DESC
        LIMIT $limit
        RETURN pr.id AS pr_id, pr.number AS pr_number, pr.title AS title, common_files
        """
        return self.execute_query(query, {
            "file_paths": file_paths,
            "limit": limit
        })
    
    def find_circular_dependencies(self, file_path: str):
        """Find circular dependencies for a file"""
        query = """
        MATCH path = (file:File {path: $file_path})-[r:DEPENDS_ON*]->(file)
        RETURN [n IN nodes(path) | n.path] AS cycle
        LIMIT 10
        """
        return self.execute_query(query, {"file_path": file_path})


class QdrantConnection:
    """Qdrant vector database connection manager"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: str = "code_reviews"
    ):
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = port or int(os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = collection_name
        self.client = None
        self.vector_size = 768  # CodeBERT embedding size
    
    def connect(self):
        """Establish connection to Qdrant"""
        try:
            self.client = QdrantClient(host=self.host, port=self.port)
            # Create collection if it doesn't exist
            self._ensure_collection()
            return True
        except Exception as e:
            print(f"Failed to connect to Qdrant: {e}")
            return False
    
    def _ensure_collection(self):
        """Ensure the collection exists with proper configuration"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
        except Exception as e:
            print(f"Error ensuring collection exists: {e}")
    
    def store_pr_embedding(
        self,
        pr_id: str,
        embedding: list,
        metadata: dict
    ):
        """Store PR embedding in Qdrant"""
        if not self.client:
            if not self.connect():
                raise ConnectionError("Failed to connect to Qdrant")
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[{
                "id": hash(pr_id) % (2**63),  # Convert to int64
                "vector": embedding,
                "payload": {
                    "pr_id": pr_id,
                    "pr_number": metadata.get("pr_number"),
                    "title": metadata.get("title"),
                    "repo_owner": metadata.get("repo_owner"),
                    "repo_name": metadata.get("repo_name"),
                    "files": metadata.get("files", []),
                    "created_at": metadata.get("created_at"),
                    **metadata
                }
            }]
        )
    
    def search_similar_prs(
        self,
        query_embedding: list,
        limit: int = 10,
        score_threshold: float = 0.7
    ):
        """Search for similar PRs using vector similarity"""
        if not self.client:
            if not self.connect():
                return []
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold
        )
        
        return [
            {
                "pr_id": hit.payload.get("pr_id"),
                "pr_number": hit.payload.get("pr_number"),
                "title": hit.payload.get("title"),
                "similarity_score": hit.score,
                "files": hit.payload.get("files", [])
            }
            for hit in results
        ]
    
    def get_pr_by_id(self, pr_id: str):
        """Retrieve PR embedding by ID"""
        if not self.client:
            if not self.connect():
                return None
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # Search with filter
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="pr_id",
                            match=MatchValue(value=pr_id)
                        )
                    ]
                ),
                limit=1
            )
            
            if results[0] and len(results[0]) > 0:
                hit = results[0][0]
                return {
                    "pr_id": hit.payload.get("pr_id"),
                    "vector": hit.vector,
                    "metadata": hit.payload
                }
        except Exception as e:
            print(f"Error retrieving PR from Qdrant: {e}")
        
        return None

