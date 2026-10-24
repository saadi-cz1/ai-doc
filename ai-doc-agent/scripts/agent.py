"""
AI Documentation Agent - main entry point.

Run inside GitHub Actions on every push. It:
  1. Finds source files changed in the latest commit.
  2. Asks Claude to add/update inline comments + docstrings for each,
     and to produce a module-level summary.
  3. Opens a Pull Request containing the inline-commented source code.
  4. Writes/updates per-module summary docs and a whole-repo summary,
     committing those directly (docs are low-risk, no review needed).
"""
import os
import sys
import time

from config import SOURCE_EXTENSIONS, EXCLUDED_DIRS, MAX_FILE_SIZE_BYTES
from claude_utils import generate_documentation, generate_repo_summary
import github_utils as gh

DOCS_DIR = "docs/modules"
SUMMARY_PATH = "docs/SUMMARY.md"


def is_documentable(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    ext = os.path.splitext(path)[1]
    if ext not in SOURCE_EXTENSIONS:
        return False
    parts = set(path.split(os.sep))
    if parts & EXCLUDED_DIRS:
        return False
    if os.path.getsize(path) > MAX_FILE_SIZE_BYTES:
        print(f"  skipping {path}: exceeds size limit")
        return False
    return True


def module_doc_path(source_path: str) -> str:
    safe_name = source_path.replace(os.sep, "__") + ".md"
    return os.path.join(DOCS_DIR, safe_name)


def main():
    changed_files = gh.get_changed_files()
    targets = [f for f in changed_files if is_documentable(f)]

    print(f"Changed files: {changed_files}")
    print(f"Files to document: {targets}")

    if not targets:
        print("No documentable source changes detected. Exiting.")
        return

    gh.configure_git_identity()

    updated_source_files = []
    updated_doc_files = []
    module_summaries = {}
    failures = []

    for path in targets:
        print(f"Processing {path} ...")
        try:
            with open(path, "r", encoding="utf-8") as f:
                original_code = f.read()

            result = generate_documentation(path, original_code)

            if result["changed"] and result["updated_code"].strip():
                with open(path, "w", encoding="utf-8") as f:
                    f.write(result["updated_code"])
                updated_source_files.append(path)

            os.makedirs(DOCS_DIR, exist_ok=True)
            doc_path = module_doc_path(path)
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(f"# `{path}`\n\n{result['module_summary']}\n")
            updated_doc_files.append(doc_path)
            module_summaries[path] = result["module_summary"]

        except Exception as e:
            print(f"  FAILED on {path}: {e}", file=sys.stderr)
            failures.append((path, str(e)))
        time.sleep(1)  # gentle rate limiting

    # --- 1. Open a PR for inline-commented source code ---
    if updated_source_files:
        branch = f"ai-docs/update-{os.environ.get('GITHUB_SHA', 'local')[:7]}"
        pushed = gh.commit_and_push(
            branch=branch,
            files=updated_source_files,
            message="docs: AI-generated inline documentation update",
        )
        if pushed:
            body = "Automated inline documentation update for:\n\n" + "\n".join(
                f"- `{p}`" for p in updated_source_files
            )
            if failures:
                body += "\n\nNote: the agent failed to process:\n" + "\n".join(
                    f"- `{p}`: {err}" for p, err in failures
                )
            url = gh.open_pull_request(
                branch=branch,
                title="AI Documentation Agent: inline documentation update",
                body=body,
            )
            print(f"Opened PR: {url}")

    # --- 2. Directly commit module summaries + refreshed repo summary ---
    if updated_doc_files:
        all_summaries = collect_all_module_summaries(module_summaries)
        repo_summary = generate_repo_summary(all_summaries)
        os.makedirs(os.path.dirname(SUMMARY_PATH), exist_ok=True)
        with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
            f.write(repo_summary)

        gh.commit_directly(
            files=updated_doc_files + [SUMMARY_PATH],
            message="docs: update module and repository summaries",
        )
        print("Committed updated docs directly to main.")

    if failures:
        print(f"Completed with {len(failures)} failure(s). See logs above.")


def collect_all_module_summaries(new_summaries: dict) -> dict:
    """
    Merges freshly generated summaries with any existing ones already on
    disk, so the whole-repo summary reflects the ENTIRE codebase, not just
    the files that changed in this run.
    """
    all_summaries = dict(new_summaries)
    if os.path.isdir(DOCS_DIR):
        for fname in os.listdir(DOCS_DIR):
            if not fname.endswith(".md"):
                continue
            source_path = fname[:-3].replace("__", os.sep)
            if source_path in all_summaries:
                continue
            with open(os.path.join(DOCS_DIR, fname), "r", encoding="utf-8") as f:
                content = f.read()
            # Strip the "# `path`" header we wrote, keep the summary body.
            body = content.split("\n\n", 1)[-1].strip()
            all_summaries[source_path] = body
    return all_summaries


if __name__ == "__main__":
    main()
