# DEBUGGING MANIFESTO - READ FIRST

## Core Rules (Non-Negotiable):
1. **NEVER create duplicate methods** - Search existing code first
2. **ONE method, ONE location** - If it exists, modify it in place
3. **Surgical changes only** - Touch only what's broken
4. **No cascading rewrites** - Fix the immediate issue, nothing else

## Before Making ANY Changes:
1. Scan the ENTIRE file for existing methods
2. Use comments like `# ...existing code...` instead of repeating code
3. Show ONLY the lines that need to change
4. Preserve all working code exactly as-is

## Current Issue Context:
- File: search_dashboard_tab.py has syntax errors
- Problem: Line 1659 has incomplete f-string (missing closing brace)
- Goal: Fix ONLY the syntax error, don't restructure anything

## Response Format:
```python
# filepath: exact/file/path
# Line XXX: Fix the specific syntax error
old_code_with_error
# Replace with:
fixed_code_only
```