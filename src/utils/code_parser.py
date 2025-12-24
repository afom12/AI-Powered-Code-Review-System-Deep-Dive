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
        
        patterns = {
            "python": r"def\s+(\w+)\s*\([^)]*\)",
            "javascript": r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:\([^)]*\)\s*=>|function))",
            "typescript": r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:\([^)]*\)\s*=>|function)|(\w+)\s*\([^)]*\)\s*:)",
            "java": r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(",
            "go": r"func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(",
            "rust": r"fn\s+(\w+)\s*\(",
            "cpp": r"(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*(?:const)?\s*\{",
            "c": r"(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*\{",
            "csharp": r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(",
            "ruby": r"def\s+(\w+)",
            "php": r"function\s+(\w+)\s*\(",
        }
        
        pattern = patterns.get(language)
        if not pattern:
            return functions
        
        for match in re.finditer(pattern, diff_content, re.MULTILINE):
            name = None
            for group in match.groups():
                if group:
                    name = group
                    break
            
            if name:
                functions.append({
                    "name": name,
                    "line": diff_content[:match.start()].count('\n') + 1
                })
        
        return functions
    
    @staticmethod
    def extract_imports(diff_content: str, language: str) -> List[str]:
        """Extract import statements"""
        imports = []
        
        patterns = {
            "python": r"(?:from\s+(\S+)\s+import|import\s+(\S+))",
            "javascript": r"(?:import\s+(?:.*\s+from\s+)?['\"](\S+)['\"]|require\(['\"](\S+)['\"]\))",
            "typescript": r"(?:import\s+(?:.*\s+from\s+)?['\"](\S+)['\"]|require\(['\"](\S+)['\"]\))",
            "java": r"import\s+(?:static\s+)?([\w.]+)",
            "go": r"import\s+(?:\([^)]*\)|['\"](\S+)['\"]|(\S+))",
            "rust": r"use\s+([\w:]+)",
            "cpp": r"#include\s*[<\"]([\w/]+)[>\"]",
            "c": r"#include\s*[<\"]([\w/]+)[>\"]",
            "csharp": r"using\s+([\w.]+)",
            "ruby": r"require\s+['\"](\S+)['\"]",
            "php": r"(?:require|include)(?:_once)?\s*['\"](\S+)['\"]",
        }
        
        pattern = patterns.get(language)
        if not pattern:
            return imports
        
        for match in re.finditer(pattern, diff_content):
            for group in match.groups():
                if group:
                    imports.append(group)
                    break
        
        return imports



