# Historical Pattern Detection Implementation

## Overview

This document describes the implementation of historical pattern detection using Neo4j and Qdrant databases. This feature enables the code review system to learn from past PRs and identify patterns, similarities, and potential issues based on historical data.

## Architecture

### Components

1. **Neo4jConnection** (`src/utils/database.py`)
   - Manages graph database connections
   - Stores PR nodes and file dependencies
   - Queries related PRs by file overlap
   - Detects circular dependencies

2. **QdrantConnection** (`src/utils/database.py`)
   - Manages vector database connections
   - Stores PR embeddings for similarity search
   - Searches similar PRs using cosine similarity
   - Retrieves PR data by ID

3. **CodeEmbedder** (`src/utils/embeddings.py`)
   - Generates embeddings for code snippets and PRs
   - Uses sentence-transformers (with fallback)
   - Supports batch processing
   - Calculates cosine similarity

4. **HistoricalAnalyzer** (`src/context/historical_analyzer.py`)
   - Orchestrates historical analysis
   - Stores PR data in databases
   - Finds similar PRs using multiple methods
   - Identifies bug patterns
   - Tracks team patterns

## Features

### 1. PR Data Storage

When a PR is reviewed, the system automatically:
- Stores PR metadata in Neo4j (title, author, files, etc.)
- Creates file dependency relationships
- Generates and stores PR embeddings in Qdrant
- Links PRs to modified files

### 2. Similar PR Detection

The system uses three methods to find similar PRs:

**Method 1: Vector Similarity (Qdrant)**
- Generates embedding for current PR content
- Searches Qdrant for similar embeddings
- Returns PRs with similarity scores > 0.6

**Method 2: File Overlap (Neo4j)**
- Finds PRs that modified the same files
- Calculates overlap percentage
- Returns PRs with common file modifications

**Method 3: GitHub API Fallback**
- Uses GitHub API if databases unavailable
- Returns recent PRs from same repository

### 3. Bug Pattern Detection

- Queries Neo4j for PRs that modified similar files
- Identifies closed PRs that might indicate bug fixes
- Links current PR to related bug issues
- Provides historical context for potential issues

### 4. Team Pattern Recognition

- Tracks frequently modified files (refactoring hotspots)
- Identifies team-specific patterns
- Provides insights into code evolution

## Database Schema

### Neo4j Graph Structure

```
(PR)-[:MODIFIES]->(File)
(File)-[:DEPENDS_ON]->(File)
```

**PR Node Properties:**
- id: Unique PR identifier (owner/repo#number)
- number: PR number
- title: PR title
- author: PR author
- repo_owner: Repository owner
- repo_name: Repository name
- created_at: Creation timestamp
- updated_at: Last update timestamp
- state: PR state (open/closed)

**File Node Properties:**
- path: File path

### Qdrant Collection Structure

**Collection:** `code_reviews`

**Vector Properties:**
- Size: 384 (default) or 768 (CodeBERT)
- Distance: Cosine

**Payload Properties:**
- pr_id: Unique PR identifier
- pr_number: PR number
- title: PR title
- repo_owner: Repository owner
- repo_name: Repository name
- files: List of modified files
- created_at: Creation timestamp
- author: PR author

## Configuration

### Environment Variables

Add to `.env`:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_change_this

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
USE_LOCAL_MODELS=false
```

### Settings in `src/main.py`

The `Settings` class includes:
- `neo4j_uri`, `neo4j_user`, `neo4j_password`
- `qdrant_host`, `qdrant_port`
- `use_local_models`, `embedding_model`

## Usage

### Automatic Storage

PR data is automatically stored when `ReviewEngine.review()` is called:

```python
from src.engine.review_engine import ReviewEngine
from src.utils.database import Neo4jConnection, QdrantConnection
from src.utils.embeddings import CodeEmbedder

# Initialize connections
neo4j = Neo4jConnection()
qdrant = QdrantConnection()
embedder = CodeEmbedder()

# Create review engine
engine = ReviewEngine(
    neo4j_conn=neo4j,
    qdrant_conn=qdrant,
    embedder=embedder
)

# Review PR (automatically stores data)
results = await engine.review(request)
```

### Manual Query

```python
from src.context.historical_analyzer import HistoricalAnalyzer

analyzer = HistoricalAnalyzer()

# Find similar PRs
similar_prs = await analyzer.find_similar_prs(request, days=30)

# Find bug patterns
bug_patterns = await analyzer.find_bug_patterns(request)

# Get team patterns
team_patterns = await analyzer.get_team_patterns(request)
```

## Error Handling

The implementation includes graceful degradation:

- **Database Unavailable**: System continues with fallback methods
- **Connection Failures**: Warnings logged, operations skipped
- **Missing Models**: Uses placeholder embeddings
- **Query Errors**: Caught and logged, doesn't crash system

## Testing

Run tests with:

```bash
pytest tests/test_historical_analyzer.py -v
```

Tests verify:
- Database connection initialization
- PR data storage (with graceful failure)
- Similar PR finding
- Bug pattern detection
- Team pattern retrieval

## Performance Considerations

1. **Embedding Generation**: Can be slow for large PRs
   - Solution: Limits code snippets and file paths
   
2. **Neo4j Queries**: Complex queries may be slow
   - Solution: Limits results and uses indexes
   
3. **Qdrant Search**: Vector search is fast but requires embeddings
   - Solution: Batch processing and caching

## Future Enhancements

1. **Caching**: Add Redis caching for frequent queries
2. **Indexing**: Add Neo4j indexes for faster queries
3. **Batch Processing**: Process multiple PRs in parallel
4. **Incremental Updates**: Update embeddings incrementally
5. **Model Fine-tuning**: Fine-tune embeddings on code-specific data

## Troubleshooting

### Neo4j Connection Issues

```python
# Check connection
conn = Neo4jConnection()
if conn.connect():
    print("Connected!")
else:
    print("Connection failed - check credentials and Docker")
```

### Qdrant Connection Issues

```python
# Check connection
conn = QdrantConnection()
if conn.connect():
    print("Connected!")
else:
    print("Connection failed - check Docker container")
```

### Embedding Issues

```python
# Test embedding
embedder = CodeEmbedder()
embedding = embedder.embed_code("def test(): pass")
print(f"Embedding size: {len(embedding)}")
```

## Dependencies

Required packages (already in `requirements.txt`):
- `neo4j==5.14.0`
- `qdrant-client==1.7.0`
- `sentence-transformers==2.2.2`
- `numpy` (via sentence-transformers)
- `torch==2.1.0` (for local models)

## Docker Setup

Start databases:

```bash
docker-compose up -d
```

Verify services:

```bash
docker-compose ps
```

Access Neo4j browser: http://localhost:7474
Access Qdrant dashboard: http://localhost:6333/dashboard


