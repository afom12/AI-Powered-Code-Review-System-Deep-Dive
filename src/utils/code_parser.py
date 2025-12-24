"""Code parsing utilities"""

from typing import Optional, Dict, List
import re


class CodeParser:
    """Utility class for parsing code"""
    
    @staticmethod
    def detect_language(filename: str) -> Optional[str]:
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
    
    @staticmethod
    def extract_functions(diff_content: str, language: str) -> List[Dict]:
        """Extract function definitions from diff"""
        functions = []
        
        if language == "python":
            pattern = r"def\s+(\w+)\s*\([^)]*\)"
        elif language in ["javascript", "typescript"]:
            pattern = r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:\([^)]*\)\s*=>|function))"
        else:
            return functions
        
        for match in re.finditer(pattern, diff_content):
            functions.append({
                "name": match.group(1) or match.group(2),
                "line": diff_content[:match.start()].count('\n') + 1
            })
        
        return functions
    
    @staticmethod
    def extract_imports(diff_content: str, language: str) -> List[str]:
        """Extract import statements"""
        imports = []
        
        if language == "python":
            pattern = r"(?:from\s+(\S+)\s+import|import\s+(\S+))"
        elif language in ["javascript", "typescript"]:
            pattern = r"(?:import\s+(?:.*\s+from\s+)?['\"](\S+)['\"]|require\(['\"](\S+)['\"]\))"
        else:
            return imports
        
        for match in re.finditer(pattern, diff_content):
            imports.append(match.group(1) or match.group(2))
        
        return imports



