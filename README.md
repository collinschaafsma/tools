# Agent worktree tools

Requires Git, Bash, and Python 3 for cleanup. Add this directory to PATH if you
want to invoke the tools by name.

## Start a task

Run from a repository:

```sh
agent-worktree voice-testing codex
agent-worktree voice-testing claude
agent-worktree voice-testing opencode
```

The launcher creates a unique linked checkout, runs `.codex/setup.sh` if present,
then executes the supplied agent command. Default agent: `codex`. Default Git
base: `HEAD`. Override with `AGENT_BASE_REF`. Override output location with
`AGENT_WORKTREES_DIR`. Setup receives `AGENT_SOURCE_PATH`, `AGENT_WORKTREE_PATH`,
and `AGENT_TASK_NAME`. Each repository may select its own branch during setup.

## Retire a task

Run from outside the target checkout:

```sh
agent-worktree-cleanup /absolute/worktree/path --base origin/main
agent-worktree-cleanup /absolute/worktree/path --base origin/main --apply --released
```

Default behavior is a preview with no hook execution. The integration ref is
resolved locally; fetch it beforehand if needed. Removal requires clean tracked
files, no untracked files, HEAD contained in the integration ref, and no Git
operation or worktree lock. Squash/rebase merges may need separate reconciliation;
there is no force option. The primary checkout is never removed.

`--released` is the caller's explicit declaration that no person, agent, service,
or reserved resource still uses the target. This tool cannot discover every
application session or resource lease. Exit agents and verify ownership first.
Preserve any evidence you need, including ignored files: ordinary Git worktree
removal removes ignored files such as build outputs and environment files too.

The tool retains the branch and parent directory, does not kill processes, and
never performs global pruning. Native Git removal remains the final authority;
for example, a worktree containing submodules may require separate handling.

## Repository cleanup contract

Optional `.codex/cleanup.sh` receives one argument:

- `--check`: read-only validation of resource ownership and teardown readiness.
- `--apply`: idempotently tear down exclusively owned resources and release claims.

The hook runs in the worktree with `AGENT_WORKTREE_PATH` and
`AGENT_CLEANUP_BASE` (the resolved integration commit). A nonzero exit preserves
the worktree. The hook must preserve tracked files, and may remove generated or
ignored files. On retry, it must handle resources it already cleaned up.
Both modes run only after explicit `--apply --released`; preview never runs code
from the repository. Install hooks only from repository code you trust.

Repositories with `.codex/setup.sh` but no cleanup hook are held by default.
After manually completing their resource cleanup, pass `--resources-cleaned`
to acknowledge that step. This does not skip any Git checks and does not bypass
an existing cleanup hook. A repository that provisions databases or other external resources needs its own
cleanup adapter or documented manual teardown before removal.

## Tests

Run from this directory:

```sh
bash -n agent-worktree
python3 tests/test_launcher.py
python3 tests/test_cleanup.py
```

Tests use temporary Git repositories and a mock agent. They do not provision
external resources or require a Codex installation.
