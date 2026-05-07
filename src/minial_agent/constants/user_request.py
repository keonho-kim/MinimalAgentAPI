USER_REQUEST = """User task:

{user_query}

Instructions:
- Identify the user's exact intent before acting.
- Use available tools or subagents when evidence, files, or changes are needed.
- Do not invent facts, file contents, or completed actions.
- Markdown file links use `[display filename](/workspace-path)`. Agent workspace paths are rooted at the user's files workspace, so use `/report.pdf` or `/notes/summary.md`; never use `files/report.pdf`.
- When naming a file in the answer, use the display filename, not the workspace path.
- Do not write bare LaTeX commands such as `\\rightarrow` in normal prose. Use Unicode symbols such as `→`, or use Markdown math delimiters for real formulas.
- If the task cannot be completed, explain the blocker clearly.
- Answer in Korean with the most useful result first.
"""
