# Shared repository collaboration rules

These rules apply to all contributors and coding assistants, including Codex
and Claude. This file is the single source of truth. CLAUDE.md imports it;
do not maintain a separate competing set of rules there.

## Shared command cards

When the user invokes a command phrase such as "Sync check", "Push my work",
"Prepare review", or "Merge approved work", read [COMMANDS.md](COMMANDS.md)
and follow that card. These are natural-language procedures, not shell aliases.
Do not infer merge permission from a save, push or review command.

## Communication and shared context

- Be concise, direct, and explicit about uncertainty. Expand technical
  abbreviations in user-facing explanations.
- Assistants do not share chat history. Record decisions, validation evidence,
  remaining work, and important limitations in repository documentation or the
  pull request so another contributor can continue without the original chat.
- Read README.md, relevant code/workflows, and PLAN.md if present
  before changing behaviour. Distinguish proposed work from deployed behaviour.

## Starting and dividing work

1. Inspect the working tree and current branch. Preserve existing uncommitted
   work; do not reset, discard, or overwrite another person's changes.
2. Fetch origin and inspect current remote main before starting a new task.
   Start a fresh task branch from origin/main. Use codex/<task>, claude/<task>,
   or another clearly named contributor branch.
3. Continue an existing task on its existing branch when appropriate. If work
   depends on another unmerged branch, document the dependency and merge order.
4. Give separate contributors distinct tasks where possible. Coordinate edits
   to the same workflow or module. Do not have two assistants push to the same
   task branch concurrently. Use separate checkouts/worktrees when sharing a
   machine; changing branches in one shared checkout affects everyone using it.

## Reviewing and merging

- Work through branches and pull requests targeting main. Do not push code
  directly to main, force-push shared branches, or merge without explicit user
  authorization. A request to implement on a branch is not merge approval.
  A specific user instruction to publish a defined change to main authorizes
  that change only; keep unrelated unfinished work out of it.
- Keep changes focused. Describe the problem, resulting behaviour, validation,
  limitations, and dependencies in the pull request. Do not include secrets.
- Before merging, fetch again and compare with current origin/main. Incorporate
  main into the task branch, resolve conflicts, and rerun affected checks.
  Prefer merging origin/main into an already shared task branch to rewriting
  its published history. Do not rebase/force-push another contributor's work.
- Merge one related request at a time. Update and retest remaining branches
  after the first merge. Never blindly choose "ours" or "theirs" in conflicts:
  preserve the intended behaviour of both changes. A conflict-free merge does
  not prove the combined behaviour is correct.
- Check dependent/overlapping branches before selecting a merge method. Do not
  independently squash overlapping changes and assume their ancestry remains
  intact; update dependent branches and review the resulting diff afterward.
- Report the final branch, commit, checks, and any work still awaiting review.
  Start subsequent independent work from the updated main.

## Validation and publishing

- Run relevant tests. When available, run:
  `python -m unittest discover -s tests -v`
  Use the repository's environment and record missing dependencies or checks
  that could not run. Documentation-only edits need link/content/diff review,
  not an unnecessary video render.
- For changes affecting generated media or workflow inputs, run a preview on
  the task branch where supported and inspect the appropriate artifacts.
  Simulated tests are not evidence of a successful live upload.
- Before starting any workflow, inspect that branch's current workflow file.
  Input names and defaults may differ by branch. Verify-only/preview runs and
  publishing runs are different operations; never assume "Run workflow" is safe.
- Do not publish videos, change their visibility, or change schedules merely
  to test code without authorization for those actions. Keep review work on
  branches until approved. State whether a run created a public, unlisted,
  private, or local-only result.
- Treat merging workflow changes as an operational change: scheduled runs use
  the default branch. Explain any new publishing behaviour or review gates.
- Report successful processing separately from successful file transfer.
  Do not claim YouTube accepted a video based only on an upload response.

## Shared settings and assets

- GitHub repository secrets and variables affect multiple branches. Coordinate
  changes and describe their effect; a task branch does not isolate settings.
- Never commit credentials, refresh tokens, client_secret.json, private setup
  output, or generated media. Stage intended files explicitly and inspect the
  staged diff before committing. Keep credentials out of logs and chat.
- Preserve source media, quiz files and their metadata. Do not mark a quiz,
  question, GIF or voice take approved without actual review evidence.
  Unknown does not mean absent.
- Where upload history exists, preserve it. Do not delete reservations to bypass
  duplicate checks. Reconcile uncertain uploads against YouTube before retrying.

## Receiving these rules on an existing branch

Fetching updates remote references but does not copy files into a task branch.
With a clean working tree, fetch origin and merge origin/main into the current
branch, resolve any conflicts, and read these instructions again. Do not use a
hard reset. Start a fresh assistant session or explicitly ask the assistant to
read AGENTS.md after updating; existing sessions may retain earlier instructions.

These files are guidance, not access controls. Repository administrators should
use branch protection/rulesets to require a review and relevant passing checks
on main. Do not claim those protections are enabled without checking settings.
