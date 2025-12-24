# Quick Start Guide

Get the AI-Powered Code Review System running in 5 minutes!

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- GitHub Personal Access Token

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd Deep-Dive

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your GitHub token
# GITHUB_TOKEN=your_token_here
```

To get a GitHub token:
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token with `repo` scope
3. Copy token to `.env` file

## Step 3: Start Infrastructure (Optional)

**Note:** Docker is optional. The system works without it, but with limited features.

```bash
# Start Neo4j, Qdrant, and Redis
# Use 'docker compose' (newer) or 'docker-compose' (older)
docker compose up -d

# Verify services are running
docker compose ps
```

**If Docker is not installed:**
- The system will still work with basic analysis
- Historical pattern detection will be limited
- See `RUNNING_WITHOUT_DOCKER.md` for details

## Step 4: Run the Application

```bash
# Start the FastAPI server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 5: Test the System

### Option A: Manual Review via API

```bash
# Review a specific PR
curl -X POST "http://localhost:8000/review/octocat/Hello-World/1"
```

### Option B: Webhook Setup (Production)

1. Go to your GitHub repository settings
2. Navigate to Webhooks → Add webhook
3. Set Payload URL: `http://your-domain/webhook/github`
4. Content type: `application/json`
5. Select events: `Pull requests`
6. Add webhook secret to `.env`: `GITHUB_WEBHOOK_SECRET=your_secret`
7. Save webhook

Now every PR will be automatically reviewed!

## Step 6: View Results

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Stats**: http://localhost:8000/stats

## Example: Review Your First PR

```python
# examples/simple_review.py
python examples/simple_review.py
```

## Troubleshooting

### Issue: "GITHUB_TOKEN not found"
- Make sure `.env` file exists and contains `GITHUB_TOKEN=...`
- Check that token has `repo` scope

### Issue: "Connection refused" for databases
- Verify Docker containers are running: `docker-compose ps`
- Check logs: `docker-compose logs`

### Issue: "Module not found"
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

## Next Steps

1. **Customize Patterns**: Edit `team_patterns.json` to add your team's conventions
2. **Add Custom Analyzers**: Extend `BaseAnalyzer` in `src/analyzers/`
3. **Configure Thresholds**: Adjust `MIN_CONFIDENCE_THRESHOLD` in `.env`
4. **Set Up Monitoring**: Add Prometheus metrics (see `src/main.py`)

## Production Deployment

For production:
1. Use environment variables instead of `.env` file
2. Set up proper secret management
3. Use HTTPS for webhook endpoint
4. Configure rate limiting
5. Set up monitoring and alerting
6. Use a production WSGI server (Gunicorn)

```bash
# Production example
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Need Help?

- Check the [README.md](README.md) for detailed documentation
- Review [examples/](examples/) for usage examples
- See [tests/](tests/) for test cases


