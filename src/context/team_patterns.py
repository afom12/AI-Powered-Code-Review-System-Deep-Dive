"""Loads and manages team-specific coding patterns"""

from typing import Dict, List, Optional
import json
from pathlib import Path
from ..models.review import TeamContext


class TeamPatternsLoader:
    """Loads team-specific patterns and conventions"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "team_patterns.json"
        self.patterns: Dict = {}
        self._load_patterns()
    
    def _load_patterns(self):
        """Load patterns from config file"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    self.patterns = json.load(f)
        except Exception:
            # Use default patterns if file doesn't exist
            self.patterns = self._default_patterns()
    
    def _default_patterns(self) -> Dict:
        """Default team patterns"""
        return {
            "coding_conventions": {
                "naming": {
                    "functions": "snake_case",
                    "classes": "PascalCase",
                    "constants": "UPPER_SNAKE_CASE"
                },
                "max_line_length": 100,
                "docstring_style": "google"
            },
            "known_patterns": [
                "Use dependency injection for services",
                "Always validate user input",
                "Use async/await for I/O operations"
            ],
            "anti_patterns": [
                "Avoid global state",
                "Don't use mutable default arguments",
                "Avoid deep nesting (>3 levels)"
            ],
            "recent_refactors": [],
            "team_members": []
        }
    
    def get_team_context(self, team_name: Optional[str] = None) -> TeamContext:
        """Get team context from loaded patterns"""
        return TeamContext(
            team_name=team_name,
            coding_conventions=self.patterns.get("coding_conventions", {}),
            known_patterns=self.patterns.get("known_patterns", []),
            anti_patterns=self.patterns.get("anti_patterns", []),
            recent_refactors=self.patterns.get("recent_refactors", []),
            team_members=self.patterns.get("team_members", [])
        )
    
    def add_pattern(self, pattern: str, pattern_type: str = "known_patterns"):
        """Add a new pattern"""
        if pattern_type not in self.patterns:
            self.patterns[pattern_type] = []
        
        if pattern not in self.patterns[pattern_type]:
            self.patterns[pattern_type].append(pattern)
            self._save_patterns()
    
    def _save_patterns(self):
        """Save patterns to config file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.patterns, f, indent=2)
        except Exception:
            pass



