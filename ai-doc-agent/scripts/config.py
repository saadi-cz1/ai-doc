"""
Central configuration for the AI Documentation Agent.
Edit SOURCE_EXTENSIONS / EXCLUDED_DIRS to match your target repo.
"""

# File extensions the agent will treat as "source code" worth documenting.
# Mixed-language by design since this is a multi-language research agent.
SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".kt", ".swift", ".rs", ".scala",
}

# Directories the agent should never touch, even if files inside them
# have a matching extension.
EXCLUDED_DIRS = {
    "node_modules", "venv", ".venv", "dist", "build", "docs",
    ".git", "__pycache__", ".github", "vendor", "target",
}

# Anthropic model used for generation. See docs.claude.com for current names.
MODEL = "claude-sonnet-5"
MAX_TOKENS = 4096

# Skip files bigger than this (keeps prompts within context limits, avoids
# burning your API budget on generated/vendored files that slipped through).
MAX_FILE_SIZE_BYTES = 60_000

SYSTEM_PROMPT = """You are a senior software engineer acting as an automated \
documentation agent. You improve code comprehension WITHOUT changing behavior.

Rules you must always follow:
1. Never change program logic, formatting of executable statements, variable \
names, or control flow. Only add or update comments and docstrings.
2. Use the idiomatic documentation style for the language (e.g. docstrings \
for Python, JSDoc for JS/TS, Javadoc for Java, godoc comments for Go, etc.)
3. Add a file-level header comment summarizing the file's purpose if one is \
missing or outdated.
4. Add/refresh docstrings or doc-comments for every public function, method, \
class, and exported symbol.
5. Add brief inline comments only where the code's intent is non-obvious \
(avoid narrating trivial lines like "i += 1 // increment i").
6. If existing comments are accurate, leave them untouched. If they are \
stale (no longer describe what the code does), correct them.
7. Return your entire response as a single valid JSON object and nothing \
else - no markdown fences, no prose before or after.

JSON schema you must return:
{
  "updated_code": "<the full file content with documentation added/updated>",
  "module_summary": "<a markdown summary (150-300 words) of what this file/module does, its key responsibilities, and how it likely relates to the rest of the project>",
  "changed": <true or false, whether you modified anything>
}
"""

REPO_SUMMARY_SYSTEM_PROMPT = """You are a technical writer producing a concise \
whole-repository architecture summary for developers who are new to this \
codebase. You will be given the module-level summaries of every documented \
file in the repository. Synthesize them into a single cohesive overview.

Structure your output in Markdown with these sections:
# Project Overview
A 2-4 sentence description of what this project does overall.

## Architecture
A short description of the main components/modules and how they relate to \
each other, inferred from the module summaries provided.

## Module Index
A bullet list, one line per file, linking each module to a one-sentence \
description of its purpose.

Return ONLY the markdown, no preamble, no code fences.
"""
