"""
Thin wrapper around the Anthropic API used by the documentation agent.
"""
import json
import re
import anthropic

from config import MODEL, MAX_TOKENS, SYSTEM_PROMPT, REPO_SUMMARY_SYSTEM_PROMPT

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env automatically


def _extract_json(text: str) -> dict:
    """
    Claude is instructed to return raw JSON, but this strips accidental
    markdown code fences just in case, and gives a clear error otherwise.
    """
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    return json.loads(text)


def generate_documentation(file_path: str, code: str) -> dict:
    """
    Sends one source file to Claude and asks it to return:
      - updated_code: the file with inline comments/docstrings added
      - module_summary: a markdown summary of the file
      - changed: whether anything was actually modified

    Returns a dict with those three keys. Raises on API/parsing failure
    so the caller can decide to skip that file rather than corrupt it.
    """
    user_prompt = f"File path: {file_path}\n\n```\n{code}\n```"

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    )

    data = _extract_json(raw_text)

    for key in ("updated_code", "module_summary", "changed"):
        if key not in data:
            raise ValueError(f"Malformed response for {file_path}: missing '{key}'")

    return data


def generate_repo_summary(module_summaries: dict) -> str:
    """
    module_summaries: dict of {relative_file_path: summary_markdown}
    Returns a single markdown document summarizing the whole repository.
    """
    joined = "\n\n".join(
        f"### {path}\n{summary}" for path, summary in sorted(module_summaries.items())
    )
    user_prompt = f"Module summaries:\n\n{joined}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=REPO_SUMMARY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return "".join(block.text for block in response.content if block.type == "text").strip()
