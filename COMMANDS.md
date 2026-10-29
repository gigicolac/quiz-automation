# Shared command cards

Paste one of these phrases into Codex or Claude while working on this repository.
These are natural-language instructions, not terminal commands or installed slash
commands. The assistant must read this file and AGENTS.md before executing them.
Replace bracketed examples with your task or pull request number/link.

## Quick reference

| Say this | Outcome | Changes GitHub? |
|---|---|---|
| **Sync check** | Fetch updates and compare branches without integrating changes. | No |
| **Start task: [description]** | Start an isolated task branch from current remote main. | No, unless the task separately authorizes publishing |
| **Update my branch** | Bring current remote main into the current task branch and validate. | No push |
| **Save checkpoint** | Commit the intended work locally. | No |
| **Push my work** | Commit intended changes as needed and publish the task branch. | Yes, task branch only |
| **Prepare review** | Update, validate, push, and open/update a pull request. | Yes, no merge |
| **Merge approved work: [pull request number or link]** | Validate and merge that specific approved request. | Yes, main changes |
| **Show status** | Explain the current state and next step. | No |

Typical sequence: **Sync check → Start task → Save checkpoint → Push my work →
Prepare review → human review → Merge approved work**. Use **Update my branch**
when another contributor has merged work. You do not need to use every card:
Prepare review already includes updating and pushing the branch.

## Common rules for every card

- Follow AGENTS.md. Preserve unrelated work and existing assets; never use a hard
  reset or force-push to make a card succeed. Stage only intended files and check
  for credentials before committing.
- Determine the current repository, branch and working-tree state first. If the
  target is ambiguous, ask a specific question. Never guess which pull request
  to merge or treat a generic task request as permission to merge.
- If work is uncommitted, do not silently stash it, move it to another branch or
  mix it into someone else's commit. Continue independent checks and explain
  what must be preserved; use a separate checkout where appropriate.
- Resolve straightforward conflicts by preserving both intended behaviours.
  Ask about genuine product/behaviour conflicts rather than choosing a side.
- Do not trigger video uploads or change secrets, visibility, schedules or
  branch protection as a side effect of these cards. A merge can change future
  scheduled behaviour; explain the effect before completing the authorized merge.
- Report what actually happened: branch, commit if created, push/merge result,
  checks, limitations and next step. A commit is not a push; a push is not a merge.

## Sync check

**Example:** `Sync check`

1. Inspect local modifications, current branch and upstream tracking.
2. Fetch origin. Compare with the tracking branch and origin/main, reporting
   commits ahead/behind and relevant incoming changes.
3. Do not switch branches, merge, rebase, commit, push or edit files.

Fetching updates local remote-tracking references, not the working files. If
network access fails, label the report as based on stale local information.

## Start task: [description]

**Example:** `Start task: improve thumbnail readability`

1. Inspect work in progress and fetch current origin/main.
2. Create a new descriptive task branch from origin/main. Use codex/<task> or
   claude/<task> as appropriate. Avoid reusing an old merged branch.
3. Preserve unrelated work, using a separate checkout if necessary.
4. Read relevant shared instructions and code, then work on the requested task.
   This card does not itself authorize pushing, merging or a live video upload.

If the task depends on an unmerged branch, identify that dependency and the
required base explicitly rather than silently starting from incomplete main.

## Update my branch

**Example:** `Update my branch`

1. Fetch origin and inspect the current task branch and its remote counterpart.
2. If someone changed that same remote branch, integrate their work first,
   preserving both sides. Never overwrite their commits.
3. Merge origin/main into the task branch. Resolve meaningful conflicts with
   the intended combined behaviour; do not rewrite published history.
4. Run relevant checks and reread updated instruction files. Leave results
   local until Push my work or Prepare review is requested.

If currently on main, only fast-forward to origin/main when safe. Do not merge
unrelated local commits into main under this card; explain any divergence.

## Save checkpoint

**Example:** `Save checkpoint`

1. Review the task diff, identify intended files, and inspect the staged diff
   for unrelated work, generated media and secrets.
2. Run checks appropriate to the changes and create a clear local commit.
3. Do not push, merge or switch branches. If nothing changed, report that.

Do not create task commits on main: first establish an appropriate task branch
without disturbing the existing working tree. Report a failing check honestly;
a checkpoint is not a claim that the work is ready to merge.

## Push my work

**Example:** `Push my work`

1. Review and checkpoint intended changes if needed.
2. Fetch and compare the remote task branch before pushing. Integrate incoming
   work safely and rerun affected checks if the remote branch advanced.
3. Push the current task branch normally, setting its upstream on first push.
4. Report the branch link, commit and validation status. Never push to main or
   merge a pull request under this card. Do not force-push after rejection.

## Prepare review

**Example:** `Prepare review`

1. Update the task branch from current origin/main and resolve conflicts.
2. Run relevant tests and a non-publishing preview when supported and useful.
   Documentation-only changes need content/link/diff review, not a render.
3. Inspect the complete diff against main, including inherited changes from
   dependent branches, then commit/push the intended work.
4. Open or update one pull request targeting main. Describe resulting behaviour,
   tests, preview evidence, limitations and dependencies. Use a draft when
   substantive required work remains.
5. Leave it open for review. This card does not approve or merge the request.

## Merge approved work: [pull request number or link]

**Example:** `Merge approved work: #12` (replace with the actual request)

This phrase explicitly authorizes merging that request once its checks and
review requirements are satisfied. It does not authorize other merges.

1. Verify repository, request number, head/base branches and the reviewed diff.
   Explain any effect on scheduled publishing or shared operating behaviour.
2. Fetch current main and check required reviews and branch protection. Update
   the task branch if needed and rerun affected checks.
3. If new changes materially alter the reviewed behaviour, obtain renewed
   review before merging. Do not bypass failing checks or required reviews.
4. Check for dependent branches before choosing the merge method. Preserve
   ancestry with a merge commit when stacked shared branches need it and the
   repository permits it; otherwise plan their update explicitly.
5. Merge only this request, verify it landed on main, and report the final
   commit and link. Do not delete branches, upload videos, or change settings
   unless separately requested. Update other active branches before their
   next merge; this card does not authorize modifying another person's branch.

## Show status

**Example:** `Show status`

Report the branch, uncommitted work, local commits versus the last known remote,
known pull request/check state, pending decisions, and the next useful action.
Read-only remote status checks are allowed; do not fetch, edit, commit, push or
merge. Clearly distinguish live remote information from cached local references.
For an up-to-date ahead/behind comparison, use Sync check instead.

## Git words in plain language

- **Fetch:** discover and download remote commits without integrating them.
- **Pull:** fetch and integrate into the current branch according to Git's
  configuration. Prefer the explicit Update my branch procedure for this repo.
- **Commit:** save a version locally.
- **Push:** publish local commits to a remote branch.
- **Pull request:** ask for a branch's changes to be reviewed and merged.
- **Merge:** combine histories; updating a task branch from main is different
  from merging a reviewed task into main.

## First-time setup on an existing branch

Ask the assistant: "Fetch origin, merge origin/main into my task branch while
preserving existing work, then read AGENTS.md and COMMANDS.md."
Fetching alone does not install these files into an existing branch. Assistants
without automatic instruction-file loading must be explicitly asked to read
both files. These cards are shared conventions, not GitHub permission controls.
