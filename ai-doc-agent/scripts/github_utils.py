"""
Git + GitHub REST API helpers: running git diff, committing, pushing,
and opening pull requests. Uses plain subprocess + requests so the only
dependency is what's in requirements.txt.
"""
import os
import subprocess
import requests

GITHUB_API = "https://api.github.com"


def run(cmd: list, check: bool = True) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def get_changed_files() -> list:
    """Returns list of files added/modified in the most recent commit."""
    output = run(["git", "diff", "--name-only", "--diff-filter=ACM", "HEAD~1", "HEAD"])
    return [f for f in output.splitlines() if f]


def configure_git_identity():
    run(["git", "config", "user.name", "ai-doc-agent[bot]"])
    run(["git", "config", "user.email", "ai-doc-agent-bot@users.noreply.github.com"])


def commit_and_push(branch: str, files: list, message: str, base_branch: str = "main"):
    """
    Creates (or reuses) `branch`, commits the given files, and pushes it.
    """
    run(["git", "checkout", "-B", branch])
    run(["git", "add"] + files)
    # Nothing to commit is not an error, just skip.
    diff = run(["git", "diff", "--cached", "--name-only"], check=False)
    if not diff:
        run(["git", "checkout", base_branch])
        return False

    run(["git", "commit", "-m", message])
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    remote = f"https://x-access-token:{token}@github.com/{repo}.git"
    run(["git", "push", remote, branch, "--force"])
    run(["git", "checkout", base_branch])
    return True


def open_pull_request(branch: str, title: str, body: str, base: str = "main"):
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    # Avoid opening duplicate PRs for the same branch.
    existing = requests.get(
        f"{GITHUB_API}/repos/{repo}/pulls",
        headers=headers,
        params={"head": f"{repo.split('/')[0]}:{branch}", "state": "open"},
    )
    if existing.ok and existing.json():
        return existing.json()[0]["html_url"]

    resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/pulls",
        headers=headers,
        json={"title": title, "body": body, "head": branch, "base": base},
    )
    if not resp.ok:
        raise RuntimeError(f"Failed to open PR: {resp.status_code} {resp.text}")
    return resp.json()["html_url"]


def commit_directly(files: list, message: str, branch: str = "main"):
    """
    Commits files straight to `branch` (used for docs, per project spec).
    Includes [skip ci] so the workflow's own doc commit doesn't retrigger it.
    """
    run(["git", "checkout", branch])
    run(["git", "add"] + files)
    diff = run(["git", "diff", "--cached", "--name-only"], check=False)
    if not diff:
        return False

    run(["git", "commit", "-m", f"{message} [skip ci]"])
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    remote = f"https://x-access-token:{token}@github.com/{repo}.git"
    run(["git", "push", remote, branch])
    return True
