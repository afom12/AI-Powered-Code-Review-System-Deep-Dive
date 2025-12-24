# Setup Checklist

## ✅ Step 1: Docker Services Running

All services are running:
- ✅ Neo4j (port 7474, 7687)
- ✅ Qdrant (port 6333)
- ✅ Redis (port 6379)

## 📝 Step 2: Configure Environment

Edit `.env` file and add:

```env
# REQUIRED: GitHub Token
GITHUB_TOKEN=your_github_token_here

# Database passwords (already set in docker-compose.yml)
NEO4J_PASSWORD=your_password_change_this
```

### Get GitHub Token:
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (for private repos) or `public_repo` (for public only)
4. Copy token and paste into `.env` file

## 🚀 Step 3: Start the Application

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Start the FastAPI server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## ✅ Step 4: Verify Everything Works

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### Test Stats Endpoint
```bash
curl http://localhost:8000/stats
```

### Test Review Endpoint
```bash
# Replace with your repository
curl -X POST "http://localhost:8000/review/owner/repo/1"
```

### Check API Documentation
Open in browser: http://localhost:8000/docs

## 🔍 Step 5: Verify Database Connections

### Neo4j Browser
- URL: http://localhost:7474
- Username: `neo4j`
- Password: `your_password_change_this` (from docker-compose.yml)

### Qdrant Dashboard
- URL: http://localhost:6333/dashboard
- No authentication needed

### Redis (if redis-cli installed)
```bash
redis-cli ping
# Should return: PONG
```

## 🎯 Step 6: Test with a Real PR

Once everything is configured:

1. Create a test PR in your repository
2. Use the review endpoint:
   ```bash
   curl -X POST "http://localhost:8000/review/YOUR_OWNER/YOUR_REPO/PR_NUMBER"
   ```
3. Check the PR for review comments

## 🐛 Troubleshooting

### "GITHUB_TOKEN not found"
- Make sure `.env` file exists
- Check token is correctly set
- Restart the application

### "Connection refused" for databases
- Verify Docker containers are running: `docker compose ps`
- Check logs: `docker compose logs`

### "Module not found"
- Install dependencies: `pip install -r requirements.txt`
- Activate virtual environment if using one

## 📚 Next Steps

- Read `QUICKSTART.md` for detailed usage
- Check `README.md` for full documentation
- Review `HISTORICAL_PATTERN_DETECTION.md` for historical analysis
- See `LEARNING_SYSTEM.md` for feedback learning

