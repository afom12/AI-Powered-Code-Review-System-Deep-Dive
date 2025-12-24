# Learning System from Feedback

## Overview

The learning system collects feedback from code reviewers and uses it to continuously improve the accuracy and relevance of code analysis. The system learns from both explicit feedback (reactions, comments) and implicit feedback (whether issues were fixed).

## Architecture

### Components

1. **FeedbackCollector** (`src/learning/feedback_collector.py`)
   - Collects feedback from multiple sources
   - Stores feedback in Neo4j and Redis
   - Supports GitHub reactions, comment replies, and manual feedback

2. **FeedbackAnalyzer** (`src/learning/feedback_analyzer.py`)
   - Analyzes feedback patterns
   - Adjusts confidence scores based on historical feedback
   - Learns false positive/negative patterns

3. **Feedback Models** (`src/models/feedback.py`)
   - `Feedback`: Individual feedback entry
   - `FeedbackStats`: Aggregated statistics
   - `LearningPattern`: Learned patterns for improvement

## Features

### 1. Multiple Feedback Sources

**GitHub Reactions**
- Thumbs up (+1) = Positive feedback
- Thumbs down (-1) = Negative feedback
- Heart/Hooray = Positive feedback

**Comment Replies**
- Analyzes reply text to determine sentiment
- Extracts corrections from replies
- Detects agreement/disagreement

**Auto-Detection**
- Tracks whether issues were fixed in PRs
- Infers feedback from code changes

**Manual API**
- Direct feedback submission via API endpoint

### 2. Feedback Storage

**Neo4j Graph Database**
- Stores feedback nodes linked to PRs and analysis results
- Enables pattern analysis across feedback

**Redis Cache**
- Fast access to feedback statistics
- Stores recent feedback for quick lookups
- 30-day expiration

### 3. Learning and Adjustment

**Confidence Adjustment**
- Adjusts confidence scores based on feedback history
- Positive feedback increases confidence
- Negative feedback decreases confidence

**Pattern Learning**
- Identifies false positive patterns
- Identifies false negative patterns
- Creates learning patterns for future use

**Category Adjustments**
- Learns category-specific adjustments
- Applies multipliers based on feedback ratios

## API Endpoints

### Submit Feedback

```http
POST /feedback
Content-Type: application/json

{
  "analysis_result_id": "security_src/auth.py_42_12345",
  "pr_id": "owner/repo#123",
  "pr_number": 123,
  "repo_owner": "owner",
  "repo_name": "repo",
  "feedback_type": "positive",
  "source": "manual",
  "reviewer": "username",
  "category": "security",
  "file_path": "src/auth.py",
  "line_number": 42
}
```

### Submit Reaction Feedback

```http
POST /feedback/reaction
Content-Type: application/json

{
  "pr_id": "owner/repo#123",
  "pr_number": 123,
  "repo_owner": "owner",
  "repo_name": "repo",
  "analysis_result_id": "security_src/auth.py_42_12345",
  "reaction": "+1",
  "reviewer": "username",
  "category": "security",
  "file_path": "src/auth.py",
  "line_number": 42
}
```

### Get Feedback Statistics

```http
GET /feedback/stats/{analysis_result_id}
```

Response:
```json
{
  "status": "success",
  "stats": {
    "total_feedback": 10,
    "positive_count": 7,
    "negative_count": 2,
    "neutral_count": 1,
    "correction_count": 0,
    "positive_ratio": 0.7
  }
}
```

### GitHub Webhook for Comments

```http
POST /webhook/github/issue_comment
X-GitHub-Event: issue_comment
```

Automatically processes comment replies to review comments.

## Integration

### Review Engine Integration

The `ReviewEngine` automatically applies learning:

```python
# Learning is enabled by default
review_engine = ReviewEngine(
    enable_learning=True,
    neo4j_conn=neo4j_conn
)

# Results are automatically adjusted based on feedback
results = await review_engine.review(request)
```

### GitHub Comment Format

Comments include feedback collection prompts:

```
🔒 **Potential hardcoded secret** [HIGH]

Found pattern matching hardcoded secrets

**Suggestion:** Use environment variables or secret management

**Confidence:** 85%

---
💬 **Was this helpful?** React with 👍 or 👎 to help improve future reviews.
<!-- analysis_result_id: security_src/auth.py_42_12345 -->
```

## Learning Process

### 1. Feedback Collection

- Feedback is collected from various sources
- Stored in Neo4j and Redis
- Linked to analysis results and PRs

### 2. Pattern Analysis

- Analyzes feedback patterns periodically
- Identifies categories with high/low feedback ratios
- Creates learning patterns

### 3. Confidence Adjustment

- Adjusts confidence scores based on feedback
- Applies category-specific multipliers
- Updates confidence levels accordingly

### 4. Pattern Application

- Applies learned patterns to new analysis
- Reduces confidence for known false positives
- Increases confidence for known true positives

## Configuration

### Environment Variables

```env
# Enable learning mode
ENABLE_LEARNING=true

# Redis for feedback caching
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Settings

```python
class Settings(BaseSettings):
    enable_learning: bool = True
    enable_learning_mode: bool = True
```

## Database Schema

### Neo4j Structure

```
(Feedback)-[:FEEDBACK_ON]->(PR)
(Feedback)-[:FEEDBACK_ON_RESULT]->(AnalysisResult)
```

**Feedback Node Properties:**
- id: Unique feedback ID
- type: positive/negative/neutral/correction/ignored
- source: github_reaction/comment_reply/manual/auto_detected
- reviewer: GitHub username
- timestamp: When feedback was given
- category: Analysis category
- file_path: File where issue was found
- line_number: Line number
- comment: Optional comment text
- correction: Optional correction text

### Redis Keys

- `feedback:{analysis_result_id}`: List of feedback JSON
- `feedback:stats:{analysis_result_id}`: Hash with statistics

## Usage Examples

### Collect Feedback from Reaction

```python
from src.learning.feedback_collector import FeedbackCollector

collector = FeedbackCollector()

feedback = await collector.collect_from_github_reaction(
    pr_id="owner/repo#123",
    pr_number=123,
    repo_owner="owner",
    repo_name="repo",
    analysis_result_id="security_src/auth.py_42_12345",
    reaction="+1",
    reviewer="username",
    category="security",
    file_path="src/auth.py",
    line_number=42
)
```

### Analyze Feedback Patterns

```python
from src.learning.feedback_analyzer import FeedbackAnalyzer

analyzer = FeedbackAnalyzer()

# Analyze patterns from last 30 days
patterns = await analyzer.analyze_feedback_patterns(days=30)

# Get category adjustments
adjustments = await analyzer.get_category_adjustments()
```

### Adjust Confidence Based on Feedback

```python
from src.learning.feedback_analyzer import FeedbackAnalyzer

analyzer = FeedbackAnalyzer()

# Get feedback stats
stats = await collector.get_feedback_stats(analysis_result_id)

# Adjust confidence
adjusted_confidence = await analyzer.adjust_confidence(result, stats)
```

## Benefits

1. **Continuous Improvement**: System learns from every review
2. **Reduced False Positives**: Learns patterns that cause false positives
3. **Improved Accuracy**: Adjusts confidence based on real feedback
4. **Team-Specific Learning**: Adapts to team's preferences and patterns
5. **Transparent**: Feedback is visible and trackable

## Future Enhancements

1. **Machine Learning Models**: Train ML models on feedback data
2. **A/B Testing**: Test different analysis strategies
3. **Feedback Dashboard**: Visualize feedback trends
4. **Automated Pattern Detection**: Auto-detect patterns without manual configuration
5. **Cross-Repository Learning**: Share patterns across repositories

## Troubleshooting

### Feedback Not Being Collected

- Check Redis connection
- Verify Neo4j is running
- Check webhook configuration

### Confidence Not Adjusting

- Ensure `enable_learning=True` in ReviewEngine
- Check feedback statistics exist
- Verify feedback analyzer is initialized

### Pattern Learning Not Working

- Ensure sufficient feedback (minimum 3-5 per category)
- Check Neo4j queries are working
- Verify pattern analysis is running periodically


