USER_REQUEST = """User task:

{user_query}

Instructions:
- Identify the user's exact intent before acting.
- Use available tools or subagents when evidence, files, or changes are needed.
- Do not invent facts, file contents, or completed actions.
- If the task cannot be completed, explain the blocker clearly.
- Answer in Korean with the most useful result first.
"""
