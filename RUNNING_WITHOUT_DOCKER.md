# Running Without Docker

## Overview

The Deep-Dive code review system can run without Docker, though some features will be limited. The system is designed to gracefully degrade when databases are unavailable.

## What Works Without Docker

✅ **Core Analysis**
- All code analyzers (Security, Architecture, Performance, etc.)
- Pattern matching
- Code quality checks
- Test gap analysis

✅ **GitHub Integration**
- PR review via API
- Webhook handling
- Comment posting
- Basic historical context (via GitHub API)

## What's Limited Without Docker

⚠️ **Historical Pattern Detection**
- No Neo4j for dependency tracking
- No Qdrant for code similarity search
- Falls back to GitHub API for similar PRs

⚠️ **Learning System**
- No Redis for feedback caching
- Feedback collection still works but slower
- Learning patterns may not persist

## Running the Application

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create `.env` file:

```env
GITHUB_TOKEN=your_token_here
ENABLE_LEARNING=false  # Set to false if Redis unavailable
```

### 3. Start the Application

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the System

```bash
# Health check
curl http://localhost:8000/health

# Review a PR (replace with your PR)
curl -X POST "http://localhost:8000/review/owner/repo/1"
```

## Database Connection Behavior

The system will automatically:

1. **Try to connect** to databases on startup
2. **Log warnings** if connections fail
3. **Continue operating** with reduced functionality
4. **Use fallbacks** where available

### Neo4j Fallback

- Uses GitHub API to find related PRs
- No dependency graph tracking
- No circular dependency detection

### Qdrant Fallback

- Uses simple file-based similarity
- No vector similarity search
- Basic file overlap matching

### Redis Fallback

- Feedback stored only in Neo4j (if available)
- No fast caching
- Slower feedback statistics

## Configuration

### Disable Database Features

In `.env`:

```env
# Disable learning if Redis unavailable
ENABLE_LEARNING=false

# System will skip database operations
# and use fallback methods
```

### Check System Status

```bash
curl http://localhost:8000/stats
```

Response shows:
- Number of analyzers
- Confidence thresholds
- Learning enabled status

## Installing Docker (Optional)

If you want full functionality:

1. **Download Docker Desktop**
   - https://www.docker.com/products/docker-desktop
   - Choose Windows version

2. **Install and Start**
   - Run installer
   - Start Docker Desktop
   - Wait for it to be ready

3. **Start Services**
   ```bash
   docker compose up -d
   ```

4. **Verify Services**
   ```bash
   docker compose ps
   ```

5. **Update .env**
   ```env
   ENABLE_LEARNING=true
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password_change_this
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   REDIS_HOST=localhost
   REDIS_PORT=6379
   ```

## Troubleshooting

### "Connection refused" Errors

These are expected if databases aren't running. The system will:
- Log warnings
- Continue with fallback methods
- Still perform code analysis

### Slow Performance

Without Redis caching:
- Feedback queries may be slower
- Historical analysis may take longer
- Consider installing Docker for better performance

### Missing Features

If you see warnings about:
- Historical pattern detection → Install Docker and start Neo4j/Qdrant
- Learning system → Install Docker and start Redis
- Feedback statistics → Redis is required for fast stats

## Summary

**You can use the system without Docker**, but you'll get:
- ✅ Full code analysis capabilities
- ✅ GitHub integration
- ⚠️ Limited historical context
- ⚠️ Slower feedback system

**For best experience**, install Docker Desktop and start the services.


