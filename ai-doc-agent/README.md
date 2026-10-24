# AI Documentation Agent

An agent that watches a GitHub repository and, on every push, automatically:

1. Detects which source files changed
2. Adds/updates inline comments and docstrings in those files (opened as a **Pull Request** for review)
3. Generates a **module-level summary** for each changed file (`docs/modules/`)
4. Regenerates a **whole-repository summary** (`docs/SUMMARY.md`)

No server required — it runs entirely as a GitHub Action, triggered by GitHub
itself whenever someone pushes code.

---

## How it works (architecture)

```
push to GitHub
      |
      v
GitHub Actions workflow (.github/workflows/auto-document.yml)
      |
      v
scripts/agent.py
      |-- git diff HEAD~1 HEAD          -> which files changed
      |-- for each changed source file:
      |       -> claude_utils.generate_documentation()
      |            -> Claude API: add inline comments/docstrings
      |                            + write a module summary
      |
      |-- github_utils.commit_and_push() + open_pull_request()
      |       -> PR containing the inline-documented source code
      |
      |-- github_utils.commit_directly()
              -> docs/modules/*.md and docs/SUMMARY.md pushed straight
                 to main (low-risk, no review needed for docs)
```

This maps directly onto the pipeline we discussed: trigger layer → change
analysis → generation layer → write-back layer. For your write-up, the
"change analysis" here is diff-based file selection (not full AST parsing) —
that's a reasonable scoping decision for a first working system, and a good
place to note as **future work** (e.g. tree-sitter-based diff analysis for
function-level granularity, rather than whole-file regeneration).

---

## One-time setup (step by step)

### 1. Get an Anthropic API key
- Go to https://console.anthropic.com → Settings → API Keys → Create Key
- Copy it, you'll need it in step 3.

### 2. Add this code to your repository
- Copy the entire contents of this folder into the root of the GitHub
  repository you want the agent to watch (keep the folder structure —
  `.github/workflows/`, `scripts/`, `docs/`, `requirements.txt`).
- Commit and push it to `main` once, manually, to get it into the repo.

### 3. Add your API key as a GitHub secret
- In your repo on GitHub: **Settings → Secrets and variables → Actions → New repository secret**
- Name: `ANTHROPIC_API_KEY`
- Value: the key from step 1
- Save. (`GITHUB_TOKEN` is provided automatically by GitHub Actions — you don't need to create it.)

### 4. Enable workflow write permissions
- **Settings → Actions → General → Workflow permissions**
- Select **"Read and write permissions"**
- Check **"Allow GitHub Actions to create and approve pull requests"**
- Save.

### 5. Done
That's it — the agent is now live. Push any change to a source file on
`main` and check the **Actions** tab to watch it run. Within a minute or two
you should see:
- A new Pull Request titled "AI Documentation Agent: inline documentation update"
- Updated files under `docs/modules/`
- An updated `docs/SUMMARY.md`

You can also trigger it manually from the **Actions** tab via
"Run workflow" (the `workflow_dispatch` trigger) to test it without pushing code.

---

## Testing locally (optional, before relying on Actions)

```bash
cd ai-doc-agent
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export GITHUB_TOKEN=ghp_...          # a personal access token with repo scope
export GITHUB_REPOSITORY=yourname/yourrepo
export GITHUB_SHA=$(git rev-parse HEAD)
cd scripts
python agent.py
```

Note: `agent.py` calls `git diff HEAD~1 HEAD`, so you need at least two
commits in your local clone for this to find anything to process.

---

## Configuration

Edit `scripts/config.py` to adjust:
- `SOURCE_EXTENSIONS` — which file types count as "source code"
- `EXCLUDED_DIRS` — directories to never touch (defaults cover common build/dependency folders)
- `MODEL` — which Claude model to use
- `MAX_FILE_SIZE_BYTES` — files larger than this are skipped (keeps costs/context bounded)
- `SYSTEM_PROMPT` / `REPO_SUMMARY_SYSTEM_PROMPT` — the instructions given to Claude; tune these if you want a different comment style (e.g. force Google-style Python docstrings)

---

## Suggested evaluation metrics for your research

Since this is a research project, a few things worth logging/measuring as
you run this against real repos:

- **Doc staleness**: time between a commit landing and the corresponding doc PR/commit appearing (the Actions run log gives you timestamps for free)
- **Acceptance rate**: % of AI-generated doc PRs merged without edits vs. merged with edits vs. rejected
- **Diff-based accuracy**: manually or LLM-graded — does the generated comment/summary actually reflect the change?
- **Comprehension study**: give developers old vs. AI-documented versions of the same file, time how long they take to answer "what does function X do" style questions

## Known limitations (worth stating explicitly in your report)

- Change detection is per-file (`git diff` between commits), not per-function via AST — a one-line change causes the whole file to be re-sent to the model. This is simple and robust across all languages but not the most token-efficient approach; tree-sitter-based diffing is the natural next step.
- No test suite is included — logic-preservation currently relies on the system prompt, not on automated verification (e.g. re-running the repo's tests against the doc PR). Adding a CI check that runs the project's existing tests against the agent's PR branch would strengthen the "we didn't break anything" claim.
- Large files (>60KB by default) are skipped rather than chunked.
