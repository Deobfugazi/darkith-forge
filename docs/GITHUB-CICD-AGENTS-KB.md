# GITHUB, CI/CD, AGENTS.md & THE DARKITH REPO — A KNOWLEDGE BASE FROM ZERO

> This is the beginner's companion to `README.md`. The README explains **what Darkith is**.
> This file explains **the machinery around it**: git, GitHub, continuous integration,
> the `AGENTS.md` convention, and the exact procedures this repository uses to keep three
> parallel AI agents from destroying each other's work.
>
> It assumes you know **nothing**. Every word is defined the first time it is used, then
> listed again in the [master glossary](#part-11--the-master-glossary-every-term-one-line).
> If you finish this file and still have a question, that is a defect in this file, and the
> [final section](#part-12--the-loop-breaker-every-follow-up-question-pre-answered) is where
> it belongs — it lists the questions a reader asks next, each already answered above.
>
> **Format.** Like the README, this file uses the **Tri-Tongue** shape: each idea is given in
> **Plain** (a reader who has never seen this field), **Precise** (the correct technical
> statement), and **Machine** (the literal file, command, or identifier a computer reads).
> You may read only the **Plain** lines and understand everything; the **Machine** lines are
> what you actually type.

**Audience:** a first-timer with zero prior knowledge of version control, hosting, or
automation. **Scope:** everything about GitHub, CI/CD, `AGENTS.md`, and this repo's
procedural mechanics. **Contract:** exhaustive, no skipped topic, no follow-up query needed.

---

## HOW TO USE THIS FILE (read this box, then jump)

1. If you have never used git or GitHub, read **Part 0 → Part 1 → Part 2 → Part 3** in order.
   That is the foundation; everything else builds on it.
2. If you only want the commands this repo uses, go to **Part 7 (daily mechanics)** and
   **Part 8 (emergencies)**.
3. If a word confuses you, jump to **Part 11 (master glossary)** — every term, one line each.
4. If you are an AI agent reading this to work in the repo, read **Part 5 (AGENTS.md)** and
   **Part 7** first; they are your operating instructions.

A one-sentence map of the whole system:

> **Plain.** You write files on your machine, you *commit* snapshots of them, you *push* the
> snapshots to GitHub, GitHub runs automatic *checks*, and if the checks pass the work is
> safe forever — because your own machine's memory is wiped every session, and GitHub is the
> only thing that survives.
>
> **Machine.** `git add -A && git commit -m "…" && git push origin main` → GitHub Actions runs
> `bash tools/ci.sh` → exit `0` = keep, non-zero = fix.

---

# PART 0 — THE ONE-PAGE ORIENTATION (what every word means, in order)

Before the deep explanations, here is the entire vocabulary of this document as a single
chain of plain sentences. Read it once; the rest of the file expands each link.

- **Version control** is the practice of remembering every version of your files.
- **Git** is the program that does version control. It lives on your machine.
- A **repository** ("repo") is a folder that git is tracking — it remembers every change.
- A **commit** is one saved snapshot, with a message saying what changed.
- **GitHub** is a website that stores a copy of your repo online, so it survives even when
  your machine is wiped, and so several people (or AI agents) can share it.
- **Remote** is the online copy; **local** is the copy on your machine.
- **Push** sends your commits up to the remote; **pull** brings the remote's commits down.
- A **branch** is a movable label pointing at the latest commit of a line of work; the main
  one is called **main**.
- A **merge** joins two branches; a **fast-forward** is the special easy case.
- A **rebase** replays your commits on top of someone else's, rewriting them as new commits.
- A **conflict** happens when two people changed the same lines; a human must choose.
- A **pull request** ("PR") is a request to merge one branch into another, with discussion
  and automatic checks attached.
- **CI** (continuous integration) is the practice of running automatic checks on every change.
- **CD** (continuous delivery/deployment) is the practice of shipping automatically after CI.
- A **gate** is one automatic check that can pass or fail.
- **GitHub Actions** is GitHub's robot that runs your checks for you when you push.
- **`AGENTS.md`** is a plain file that tells an AI agent how to work in the repo.
- **Ephemeral** means "temporary, wiped when the session ends" — which is what this project's
  machines are, and the single most important fact in this whole file.

Everything below expands these, with the real commands and the real file names this repo uses.

---

# PART 1 — WHAT GIT AND GITHUB ARE (from absolute zero)

## 1.1 The problem: memory that forgets

> **Plain.** Imagine writing a document and having no "save as", no undo history, and a
> memory that is wiped clean every night. Every morning you would start from whatever single
> copy survived. If that copy was broken, the work is gone. That is the situation this
> project was in: the machines it runs on are wiped between sessions.
>
> **Precise.** A filesystem without version control has no history, no branching, and no
> distribution. Any loss is total. Version control adds three things: **history** (every
> past state is retrievable), **branching** (parallel lines of work that can be rejoined),
> and **distribution** (many copies that can be reconciled).
>
> **Machine.** `git log` shows history; `git branch` lists lines of work; `git push` / `git fetch`
> distribute copies between machines.

## 1.2 What git is

> **Plain.** Git is a program that watches a folder. Every time you tell it "save the current
> state", it stores a complete snapshot of that folder inside a hidden sub-folder called
> `.git`. From then on you can see any snapshot you ever made, compare two, or go back.
>
> **Precise.** Git is a distributed version-control system. It stores content-addressed
> objects (each blob/commit named by the SHA-256-style hash of its content) in the `.git`
> directory. A **commit** points to a **tree** (the folder state) and to its **parent**
> commit, forming a directed acyclic graph. Because objects are named by content hash, the
> same content is never stored twice, and any tampering changes the hash.
>
> **Machine.** The history lives in `.git/`. `git status` shows what changed; `git log` walks
> the commit graph; `git cat-file -p <hash>` prints any object.

The word **repo** is short for *repository* — the folder git is tracking, including its `.git`
history. The folder you are in, `/workspace/project/darkith-forge`, is a repo.

## 1.3 The three "places" a file can be in

This trips up every beginner, so learn it early. In git, a file is always in one of three
places, and you move it forward one step at a time.

| Place | What it means | How a file gets there |
|---|---|---|
| **Working tree** | The actual files on disk that you edit | You create or edit a file |
| **Staging area** ("index") | A draft of the next snapshot | `git add <file>` |
| **Repository** (a commit) | A permanent snapshot in history | `git commit -m "message"` |

> **Plain.** Editing a file changes only your disk. "Adding" it puts it in a waiting room.
> "Committing" takes a permanent photograph of the waiting room. Only committed things are
> remembered; only committed things can be pushed to GitHub.
>
> **Machine.** `git status` shows the three zones; `git add -A` stages everything;
> `git commit -m "msg"` freezes the snapshot; `git push` uploads the commits.

## 1.4 What GitHub is (and is not)

> **Plain.** GitHub is a website that keeps a copy of your repo. It is not git itself — git
> is the tool; GitHub is one popular place to *host* the copy. Because the copy lives on
> GitHub's servers (not your machine), it survives when your machine is wiped. GitHub also
> adds extra features on top of plain git: pull requests, the Actions robot, issues, and
> permissions.
>
> **Precise.** GitHub is a **forge**: a hosting platform for git repositories that adds
> collaboration and automation layers (pull requests, CI runners, review, access control).
> Git itself is provider-neutral; GitHub is one provider. This repo is written so that the
> *logic* lives in `tools/` and only the thin glue lives in GitHub-specific files, so it
> could move to another forge without rewriting the logic.
>
> **Machine.** This repo's GitHub home is `github.com/Deobfugazi/darkith-forge` (private).
> The provider-neutral principle is stated at the top of `tools/ci.sh` and `tools/sync.sh`.

Two more words you will see:

- **Private repo** — only people (and tokens) you authorize can see it. This repo is private.
- **Public repo** — anyone on the internet can see it. Do not put secrets in either one.

## 1.5 Remote, origin, local — the three-way relationship

> **Plain.** Your machine holds the **local** copy. GitHub holds the **remote** copy. The
> default nickname for "my remote" is **origin**. Push sends local → remote; fetch/pull brings
> remote → local.
>
> **Precise.** A **remote** is a named URL that git remembers. `origin` is the conventional
> name of the remote you cloned from. `git remote -v` prints them.
>
> **Machine.**
> ```bash
> git remote -v
> # origin  https://github.com/Deobfugazi/darkith-forge.git (fetch)
> # origin  https://github.com/Deobfugazi/darkith-forge.git (push)
> ```

## 1.6 Clone: getting the repo onto a new machine

> **Plain.** "Cloning" is downloading a full copy of a repo (all its history included) onto a
> new machine.
>
> **Machine.** `git clone <url>` — for this repo, `bash tools/restore.sh` wraps the clone so
> the right branch and credentials are used automatically.

## 1.7 The commit: the atom of history

> **Plain.** A commit is one snapshot plus a short message. "Fixed the login bug" is a commit.
> Each commit gets a long unique ID (a **hash**) so you can always name it exactly.
>
> **Precise.** A commit object stores: a pointer to the snapshot tree, a pointer to its
> parent commit(s), the author, the timestamp, and the message. Its identity is the hash of
> all that. Two commits with the same hash are byte-for-byte identical.
>
> **Machine.**
> ```bash
> git commit -m "fix: the thing that was broken"
> git log --oneline            # one line per commit: <short-hash> <message>
> git show <hash>              # everything about one commit
> ```

A **commit message** is the human sentence explaining the change. Convention in this repo is
a lowercase type prefix then a colon: `fix:`, `docs:`, `chore:`, `reconcile:`, `proof:`.

## 1.8 The hash: why commits have names like `8813115`

> **Plain.** Git names every snapshot with a long string of letters and numbers, like
> `8813115a2…`. You never have to type the whole thing — the first 7 characters are enough.
>
> **Precise.** The hash is a cryptographic digest (SHA-1 for object identity in git, SHA-256
> for the content hashes this repo prints) of the object's bytes. It is deterministic: the
> same content always has the same hash, and any change changes the hash. That is why the
> repo can *prove* two files are identical by comparing hashes.
>
> **Machine.** `git rev-parse HEAD` prints the full hash of the current commit;
> `sha256sum <file>` prints a file's content hash.

## 1.9 HEAD: "where you are right now"

> **Plain.** `HEAD` is a bookmark meaning "the commit you are currently standing on".
>
> **Machine.** `git rev-parse HEAD`; `git rev-parse --short HEAD` prints the 7-char form.

## 1.10 Branch: a line of work

> **Plain.** A branch is a movable label pointing at the newest commit of one line of work.
> You can have several lines in progress at once and join them later.
>
> **Precise.** A branch is a reference (a pointer) to a commit. Creating a branch is nearly
> free; committing on a branch advances that pointer; `main` is the conventional name of the
> primary line.
>
> **Machine.** `git branch` lists branches; `git switch -c my-branch` makes and switches to a
> new one; `git branch --show-current` prints the current one (here: `main`).

## 1.11 Push and pull: moving commits between machines

> **Plain.** "Push" sends your new commits up to GitHub. "Pull" brings GitHub's new commits
> down to you. They are opposite directions of the same road.
>
> **Precise.** `git push <remote> <branch>` updates the remote branch to include your local
> commits; it is **rejected** if it would *lose* a commit already on the remote (a
> **non-fast-forward**), which is git's built-in safety catch. `git fetch` downloads without
> merging; `git pull` fetches and then merges.
>
> **Machine.** `git push origin main` · `git fetch origin` · `git pull origin main`.

## 1.12 Merge and fast-forward

> **Plain.** "Merging" joins two branches back together. If your branch has simply moved
> forward and nothing else happened, git just slides the label forward — that easy case is a
> **fast-forward**. If both sides did different work, git builds a **merge commit** joining
> them.
>
> **Precise.** A **fast-forward** is a merge where the target is a direct ancestor of the
> source, so no new commit is needed — the pointer is advanced. A **three-way merge** creates
> a merge commit with two parents when both lines diverged.
>
> **Machine.** `git merge --ff-only <hash>` refuses anything but a fast-forward (this repo's
> `tools/sync.sh` uses exactly this for the "behind" case).

## 1.13 Rebase: replaying your work on top of newer work

This word is in your question, so it gets a full explanation.

> **Plain.** Imagine you started editing while a colleague also edited the same file. A
> "rebase" takes *your* edits and re-applies them as if you had started *after* the colleague
> finished. The result reads as one straight line of history instead of a tangle. The catch:
> because the commits are re-created, they get **new** hashes.
>
> **Precise.** `git rebase <base>` finds the commits unique to your branch, rewinds to
> `<base>`, and re-applies each of your commits one at a time on top. Each re-application is a
> new commit with a new hash. If a re-application cannot apply cleanly, the rebase pauses for
> a human to resolve the **conflict**.
>
> **Machine.**
> ```bash
> git rebase origin/main     # replay my commits on top of the remote's latest
> git rebase --continue      # after fixing a conflict
> git rebase --abort         # undo the whole rebase, back to where you started
> ```

**Why this repo uses rebase:** two AI tabs work in parallel. When one pushes first, the other
**rebases** onto it so history stays a single clean line, and the push is never *forced*
(forced pushes can silently delete someone's work — see [§2.9](#29-force-push-and-why-this-repo-never-uses-it)).

## 1.14 Conflict: when git cannot choose for you

> **Plain.** If two people changed the same line in different ways, git cannot know which
> version is right. It stops and marks the file with both versions, asking a human to pick.
>
> **Precise.** A **merge conflict** is produced when the three-way merge cannot reconcile
> hunks. The file gains `<<<<<<<`, `=======`, `>>>>>>>` markers delimiting "ours" and "theirs".
>
> **Machine.** After resolving, `git add <file>` then `git rebase --continue` (or
> `git merge --continue`). This repo's `tools/sync.sh` deliberately **stops and exits 3** on a
> conflict rather than auto-resolving — a human decides.

## 1.15 Stash: parking work-in-progress

> **Plain.** A "stash" is a drawer where you temporarily park uncommitted changes so you can
> do something else (like pull) and then take them back out.
>
> **Machine.** `git stash` puts them away; `git stash pop` takes them back; `git stash list`
> shows the drawer.

## 1.16 Reflog: git's own diary (the safety net)

> **Plain.** Even when you "lose" commits, git keeps a private diary of everywhere `HEAD` has
> been. You can almost always find lost work here. This is how a lost commit was recovered in
> this very project.
>
> **Machine.** `git reflog` prints the diary; `git reset --hard <hash>` returns to any entry.

## 1.17 `.gitignore`: telling git what to ignore

> **Plain.** Some files should never be saved — caches, build output, and especially secrets.
> A file called `.gitignore` lists patterns git should pretend it cannot see.
>
> **Precise.** `.gitignore` is a set of glob patterns; matching paths are excluded from
> `git status` and `git add` unless forced. This repo's `.gitignore` excludes generated output
> (`delivery/`, `dist/`, `*.zip`) and any signing-key material.
>
> **Machine.** `cat .gitignore` · a file already tracked is **not** un-tracked by adding it
> to `.gitignore` — you must also `git rm --cached <file>`.

## 1.18 Tag: a permanent name for one commit

> **Plain.** A tag is a sticky label you put on one commit, usually a release, like
> `v1.0.0`. Unlike a branch, a tag never moves.
>
> **Machine.** `git tag v1.0.0` · `git tag -l` · `git push origin v1.0.0`.

## 1.19 Fork and upstream

> **Plain.** To "fork" a repo is to make your own full copy of someone else's repo on GitHub,
> so you can change it without touching theirs. The original is called the **upstream**.
> (This project's history mentions "six forks" of its own source tree — copies of the code
> that had drifted apart; reconciling them into one is a recurring theme.)
>
> **Machine.** On GitHub: the *Fork* button. Locally: `git remote add upstream <url>`.

## 1.20 Pull request (PR): asking to merge

> **Plain.** A pull request is a proposal: "please merge my branch into `main`." It is where
> people review the change, discuss it, and where the automatic checks run before the merge
> is allowed. In git the word "pull" is confusing here — a PR is really a *merge request*.
> (GitLab calls it exactly that: an **MR**.)
>
> **Precise.** A PR is a host-side object (not a git object) that tracks a source branch, a
> target branch, the diff between them, a comment thread, a review state, and the status of
> required checks. Merging the PR merges the branches.
>
> **Machine.** GitHub UI, or `gh pr create --base main --title "…" --body "…"`.

**PR states:** *open* (awaiting merge), *draft* (not ready), *merged*, *closed* (rejected or
withdrawn without merging).

## 1.21 Issue: a tracked to-do

> **Plain.** An issue is a numbered note in the repo's tracker: a bug, a task, a question.
> PRs can reference issues ("Fixes #12") to link code to the problem it solves.
>
> **Machine.** `gh issue list` · `gh issue create`.

## 1.22 Actions, workflow, runner, job, step

> **Plain.** "Actions" is GitHub's built-in robot. You write a small recipe file; when you
> push, GitHub spins up a temporary computer in the cloud, follows the recipe, and reports
> pass/fail. Each recipe is a **workflow**; the temporary computer is a **runner**; a workflow
> contains **jobs**, and each job contains **steps**.
>
> **Precise.** Workflows are YAML files in `.github/workflows/`. They are triggered by
> **events** (`on:`) such as `push`, `pull_request`, or `schedule`. Each `job` runs on a fresh
> `runs-on` runner; `steps` run shell commands or reusable `uses:` actions.
>
> **Machine.** This repo has two workflows:
> `.github/workflows/auto-merge.yml` and `.github/workflows/fracture-scout.yml`.

## 1.23 Token: the password a robot uses

> **Plain.** A token is a long secret string that acts like a password for a program (rather
> than a human at a keyboard). This repo's agents authenticate to GitHub with a token named
> `GITHUB_TOKEN`, provided by the environment, never written into a file.
>
> **Machine.** Never commit a token. This repo gates that: `tools/secret_gate.py` fails CI if
> a credential-shaped string is committed.

## 1.24 The `.git` directory and where the "scrollback" lives

> **Plain.** `.git` is the hidden folder holding all history. Separately, an AI agent's chat
> transcript is stored on disk under `/var/openhands/conversations/`, one file per event —
> so even when the chat window cannot scroll back, the history is recoverable.
>
> **Machine.** `/var/openhands/conversations/<id>/events/event-NNNNN-*.json`.

---

# PART 2 — CI/CD, EXPLAINED COMPLETELY

## 2.1 The problem: humans forget to check

> **Plain.** If checking your work is a step a human must remember, it will be skipped on the
> busy day it matters most. The fix is to make a machine do it every single time.
>
> **Precise.** Manual verification is not reproducible and does not scale. Automation turns
> "I think it works" into "a check proved it works, on every change, identically."
>
> **Machine.** `bash tools/ci.sh` — one command that runs every check and exits `0` only if
> all pass.

## 2.2 CI (continuous integration)

> **Plain.** "Continuous integration" means: every time anyone changes the code, automatically
> build it and run all the tests. If anything fails, you know immediately, before it spreads.
> "Continuous" = happens automatically on every change; "integration" = the separate pieces
> are combined and checked together.
>
> **Precise.** CI is the practice of merging every change into a shared mainline frequently,
> with an automated build-and-test on each integration, so defects are caught at the smallest
> possible scope.
>
> **Machine.** Here CI = `tools/ci.sh`, invoked locally by you and remotely by
> `.github/workflows/auto-merge.yml`.

## 2.3 CD (continuous delivery / continuous deployment)

> **Plain.** After the checks pass, "CD" is about shipping. *Continuous delivery* means the
> result is always ready to release (one button). *Continuous deployment* means it releases
> automatically. For an Android app, "release" means producing and publishing the `.apk`.
>
> **Precise.** Delivery keeps the artifact in a releasable state; deployment makes it live.
> This repo's delivery is gated by `tools/delivery_gate.sh`, which refuses the word
> "delivered" while any known loophole is open.
>
> **Machine.** `bash tools/delivery_gate.sh . --source-only` (source laws only) or with an APK
> for the full gate.

## 2.4 The pipeline: the stages a change passes through

> **Plain.** A change flows through a fixed sequence. In this repo:
>
> 1. **Edit** files in the working tree.
> 2. **Stage & commit** a snapshot.
> 3. **Push** to GitHub.
> 4. **CI runs** (`tools/ci.sh`): every gate must pass.
> 5. **Integrate** (merge/rebase into `main`) — only green work integrates.
> 6. **Package** (`tools/pack_delivery.py`) — build the downloadable artifacts.
> 7. **Deliver** (`tools/delivery_gate.sh`) — publish, but only if the gate says DELIVERED.
>
> **Precise.** Each stage has an exit code; a non-zero exit at any stage stops the flow. The
> gates are composable because each is a small program returning `0`/non-zero.
>
> **Machine.** The exact commands are in [Part 7](#part-7--the-darkith-repo-mechanics-the-real-procedures).

## 2.5 What a "gate" is (the central idea of this repo)

> **Plain.** A gate is a small program that answers one yes/no question about the repo and
> says "pass" (exit 0) or "fail" (non-zero). "Does the code compile?" "Is there a secret in
> the tree?" "Is a task marked done without proof?" Each is a gate. Many gates chained = CI.
>
> **Precise.** A gate is an executable check. The repo's law **SPI-15** says: *a rule that is
> not an executable gate is only a note.* In other words, a rule nobody can run is not
> enforced, so it does not count. Every law here must name a gate that exists on disk, or it
> fails `tools/law_gate.py`.
>
> **Machine.** Gates live in `tools/*.py` and `tools/*.sh`; `tools/ci.sh` runs them;
> `tools/law_gate.py` proves each declared law names one.

## 2.6 How CI is triggered (locally and remotely)

> **Plain.** You run CI yourself by typing one command. GitHub runs the same command for you
> whenever you push, because the workflow file says to.
>
> **Precise.** The **adapter** pattern: the provider-neutral logic is `tools/ci.sh`; the
> GitHub YAML is only glue that decides *when* to run it and *how* to react. Copying logic
> into the YAML would make the repo a hostage to one provider.
>
> **Machine.** `.github/workflows/auto-merge.yml` runs `bash tools/ci.sh` on `pull_request`,
> on `push` to `main`, and on a weekly `schedule`.

## 2.7 A real CI run, step by step (the auto-merge workflow)

> **Plain.** This repo's dependency workflow checks that any change still passes all gates,
> then merges it only if the *exact* commit that was tested is still the one being merged.
> That last guard matters: if the code changed after the test, the test proves nothing about
> the new code.
>
> **Precise.** Jobs: `tests` (checkout → set up Python/Node → install deps → stage toolchain →
> run `tools/ci.sh`) and `merge` (`needs: tests`; only for dependency-bot PRs; re-checks the
> head SHA — a **TOCTOU** guard — then merges). A third job `bump` runs on the schedule to
> propose dependency updates.
>
> **Machine.** See `.github/workflows/auto-merge.yml`. Key idea: `merge` has
> `needs: tests`, so it cannot run unless `tests` succeeded.

**TOCTOU** = "time-of-check to time-of-use": the classic bug where you check something, time
passes, the thing changes, and you act on a stale check. The fix here is to re-read the
commit hash right before merging and refuse if it moved.

## 2.8 Fail closed vs. fail open (and the honest skip)

> **Plain.** "Fail closed" means: if the check cannot run, treat that as a failure (safe).
> "Fail open" means: if it cannot run, treat it as a pass (unsafe — a broken thing slips
> through looking green). This repo fails **closed** for anything that matters, and where a
> check genuinely cannot run (say, no Android device attached) it prints a loud, **named
> skip** — never a silent pass.
>
> **Precise.** `tools/ci.sh` uses `set -u`, tracks a `FAILED` flag, and prints
> `--- <name>: PASS|FAIL`. A missing toolchain is a named `SKIP` (and often sets `FAILED=1`),
> so a green-looking run can never hide an unrun check.
>
> **Machine.** Look for the literal strings `SKIP:` and `--- <gate>: FAIL` in `tools/ci.sh`.

## 2.9 Force push, and why this repo never uses it

> **Plain.** A "force push" overwrites the remote branch, even if that deletes commits
> someone else added. It is a loaded gun: it can silently destroy another worker's work. This
> repo's rule is that the push is **never** forced; if histories diverge, it rebases instead.
>
> **Precise.** `git push --force` bypasses the non-fast-forward protection. The correct
> alternative when histories diverged is to integrate (rebase/merge) and then push a
> fast-forward. `tools/sync.sh` does exactly this and exits non-zero on a real conflict rather
> than forcing.
>
> **Machine.** The words "never forced" appear in the header of `tools/sync.sh`.

## 2.10 Secrets in CI

> **Plain.** Robots need passwords, but passwords must never be saved in the code. GitHub
> stores them as **secrets** and injects them into the runner as environment variables.
>
> **Precise.** `secrets.GITHUB_TOKEN` etc. are injected at run time; a gate
> (`tools/secret_gate.py`) fails CI if a credential-shaped string is ever committed, and
> `tools/continuity.sh` refuses to push if a private key becomes tracked.
>
> **Machine.** `env: GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` in the workflow; the guard is in
> `tools/secret_gate.py`.

## 2.11 The Actions security posture (least privilege, pinned versions)

> **Plain.** A robot should get the smallest permissions it needs, and should use exact,
> frozen versions of other people's tools (never "the latest", which can change under you).
>
> **Precise.** Workflows set `permissions: contents: read` by default and elevate only where
> needed; third-party actions are pinned to full commit **SHAs** (not mutable tags); fork PRs
> never auto-merge.
>
> **Machine.** See the `permissions:` blocks and the `@<40-hex-sha> # v4` pins in the
> workflows.

## 2.12 Scheduled jobs (cron)

> **Plain.** Some jobs run on a timer instead of on a push — e.g. "every day, look for new
> problems". The timer syntax is called **cron**.
>
> **Precise.** `on: schedule: - cron: "23 5 * * *"` means 05:23 UTC daily (fields: minute,
> hour, day-of-month, month, day-of-week).
>
> **Machine.** `fracture-scout.yml` runs daily; `auto-merge.yml` runs Mondays 06:17 UTC.

## 2.13 Providers: GitHub Actions, GitLab CI, Bitbucket, Jenkins

> **Plain.** Several companies offer the same service. GitHub's is "Actions"; GitLab's is
> "GitLab CI"; Bitbucket has "Pipelines"; Jenkins is a self-hosted one. Because this repo
> keeps the logic in `tools/`, moving providers means rewriting only the thin YAML glue.
>
> **Machine.** `tools/ci.sh`'s header says it "knows nothing about GitHub, GitLab, Bitbucket,
> Jenkins or any other CI vendor."

## 2.14 Dependabot, auto-merge, and this repo's dependency bot

> **Plain.** Software depends on other software ("dependencies"). A **bot** can watch for
> newer versions and propose updates automatically. "Auto-merge" merges such an update *only
> after* the checks pass and *only if* nothing changed since.
>
> **Precise.** `tools/darkbot.py` bumps pinned versions, regenerates `requirements-dev.txt`,
> and the workflow commits or merges only after `tools/ci.sh` exits 0. The manifest of
> dependencies is `tools/deps.txt`.
>
> **Machine.** `python3 tools/darkbot.py update|export|selftest`.

---

# PART 3 — `AGENTS.md`, AND WHY IT EXISTS

## 3.1 What `AGENTS.md` is

> **Plain.** `AGENTS.md` is a plain text file at the top of the repo that tells an AI coding
> agent (like the ones working on this project) how to behave here: the rules, the traps, the
> commands, the things never to do. It is the agent's briefing document.
>
> **Precise.** `AGENTS.md` is an emerging convention: a machine-readable-but-human-written
> instruction file at the repository root. Agents are expected to read it before acting, so
> project-specific knowledge does not have to be re-derived (or re-explained by the human)
> every session.
>
> **Machine.** This repo's `AGENTS.md` starts with `# AGENTS.md — Darkith` and a "CONTINUITY"
> section that says the machine is ephemeral and to run `bash tools/restore.sh` first.

## 3.2 Why it matters *more* here (the ephemeral machine)

> **Plain.** The AI runs on a temporary machine that is **wiped between sessions**. So the
> agent literally cannot remember yesterday. `AGENTS.md` (committed to GitHub) is how
> yesterday's knowledge survives: each session reads it, learns the traps, and writes back
> anything new.
>
> **Precise.** Session memory is per-conversation and volatile; only committed bytes persist.
> `AGENTS.md` is therefore part of the durable state, not decoration. It is paired with
> `RESUME.md` (the recovery protocol) and `DARKITH.md` (the canonical record).
>
> **Machine.** `bash tools/restore.sh` (start) and `bash tools/continuity.sh "msg"` (end).

## 3.3 What a good `AGENTS.md` contains (and this one does)

> **Plain.** A good agent file says: where the project lives, how to restore it, how to save
> it, the hard rules ("never do X"), the environment traps ("Y is broken here"), the exact
> commands that work, and where the deeper truth lives.
>
> **Precise.** This repo's `AGENTS.md` sections: §0 continuity; the project description; the
> **SPI invariants**; resolved defects; the web-studio layout; known gotchas (the `#` sigil
> trap; the multi-session context trap); the synchronicity engine; verification commands;
> proof logs; the OMEGA reconciliation; the §19 anti-divergence laws; the §20 delivery gate
> and its **loophole registry**; version truth; build/deliver commands; where the scrollback
> lives; §21 circadian + one-surface; §22 dedup/idempotency; §23 no stalled deficiency.
>
> **Machine.** `grep -nE '^## ' AGENTS.md` lists every section.

## 3.4 The `AGENTS.md` / `README.md` / `DARKITH.md` / `RESUME.md` division of labour

A beginner's most common confusion: "there are four big markdown files — which is which?"

| File | Audience | Holds | Analogy |
|---|---|---|---|
| `README.md` | a human newcomer | what the project *is*, and why it is unique | the front door |
| `AGENTS.md` | an AI agent / returning dev | how to *work* here; the traps | the staff handbook |
| `DARKITH.md` | everyone | the *canonical record*: version, laws, deficits | the single ledger |
| `RESUME.md` | the next session | the *recovery protocol* | the emergency card |

> **Plain.** Four files, four jobs, no overlap on purpose. `DARKITH.md` is the one truth;
> the others point at it instead of copying it, because a copy drifts.
>
> **Precise.** This is the repo's **NEVER #16 (One Document)** law: one canonical record per
> layer; copies are *generated*, never hand-edited. `tools/kb_index.py` files each of these
> into the `A-apparatus` register and fails if a readable file is unfiled or duplicated.

## 3.5 The wider convention: `AGENTS.md`, `.cursorrules`, skills

> **Plain.** `AGENTS.md` is one of several ways to give an agent instructions. Others:
> `.cursorrules` (for the Cursor editor), and **skills** (small folders of reusable
> know-how). They all exist for the same reason: an agent should not need the human to repeat
> the same instructions every time.
>
> **Machine.** In OpenHands, skills live under `.agents/skills/` and are invoked by name.

## 3.6 The injection hazard (why `AGENTS.md` is also *untrusted*)

> **Plain.** Anything that *instructs* an agent is also a way to *attack* one: if a stranger
> can edit the file, they can tell the agent to do harmful things. So agent files are treated
> as untrusted input, and any instruction to change security settings is refused.
>
> **Precise.** "Prompt injection" is the class of attack where untrusted content carries
> instructions. This repo gates it: `tools/blueprint_gate.py` fails CI if the Operator's
> specification corpus contains injected imperatives (e.g. "COPY AND PASTE … INTO OPENHANDS",
> "do not ask for confirmation; execute immediately").
>
> **Machine.** `python3 tools/blueprint_gate.py` — runs unconditionally in CI.

---

# PART 4 — THE MULTI-AGENT MODEL (why "another VM tab" is the wrong mental model)

This part answers the question that opened the project, and prevents the whole class of
confusion behind it.

## 4.1 The setup: several agents, one repo, no shared disk

> **Plain.** Several AI agents ("tabs") work on this project **at the same time**. Each runs
> on its **own separate temporary machine**. Those machines **cannot see each other's disks**.
> The *only* thing they share is the GitHub repo. So the repo is the single meeting point; a
> tab is just one checkout of it.
>
> **Precise.** Each tab is an ephemeral sandbox with an independent filesystem. They
> synchronize exclusively through the git remote (push/fetch). There is no cross-VM
> filesystem, no shared clipboard, no shared memory. Therefore the remote branch is the
> single authoritative history, and any tab's local state is provisional until pushed.
>
> **Machine.** `tools/sync.sh`'s header states it: "Two (or more) OpenHands tabs run in
> separate ephemeral sandboxes that share **ONLY the git remote**."

## 4.2 "Did one VM pull from another VM?" — the precise answer

> **Plain.** No. A VM cannot reach into another VM's disk; that is physically impossible here.
> What actually happens is: tab A **pushes** its commits to GitHub; tab B **fetches** them
> from GitHub and fast-forwards onto them. The bytes moved through GitHub, never machine-to-
> machine. The effect you *feel* — "my tree changed under me" — is real, but the mechanism is
> the shared remote, not a copy between VMs.
>
> **Precise.** The observed `git reflog` entries `merge origin/main: Fast-forward` are a tab
> integrating the other tab's pushed commits. The provenance is a **push** from a sibling tab,
> not a "pull from a VM."
>
> **Machine.** `git reflog` shows every integration; `git log --oneline` shows whose commits
> landed.

## 4.3 Why divergence is the real danger (and the laws that prevent it)

> **Plain.** If two tabs each keep their own copy of a file and both edit it, you now have two
> versions that disagree — a "fork". Merging them is where work is lost. So the repo has hard
> laws against it.
>
> **Precise.** The anti-divergence laws (from `AGENTS.md` §19, `DARKITH.md`):
> - **NEVER #11 (One Tree)** — never two divergent live copies of a file; reconcile into one.
> - **NEVER #12 (No Foreign Symbol)** — never reference a symbol defined in another tree.
> - **NEVER #13 (No Unproven Currency)** — a tree is current only after *its own* clean compile.
> - **MUST #10** — byte-diff every fork before declaring a tree current.
> - **MUST #11 (Compile Is The Proof)** — reconciliation ends with 0 compiler errors.
> - **SPI-12** one authoritative tree · **SPI-13** every symbol resolves in-tree ·
>   **SPI-14** every input versioned.
>
> **Machine.** `tools/fork_integrity_gate.sh` is the executable form of these laws; CI runs it.

## 4.4 Convergence: the ritual when two tabs have written

> **Plain.** When two tabs may have both written, you run **two** steps: first integrate their
> commits, then re-run all the checks on the *combined* result. Both steps are required,
> because git can merge two edits into something that is "clean" to git but broken in reality
> — only running the code catches that.
>
> **Precise.** `tools/converge.sh` = `tools/sync.sh` (integrate + publish, non-forced) then
> `tools/ci.sh` (gate the merged tree). "In sync" without the gate is not convergence.
>
> **Machine.** `bash tools/converge.sh`.

## 4.5 The durable board (`TASKS.md`) as the shared channel

> **Plain.** The in-session task list is wiped with the machine, so it cannot be how tabs
> coordinate. Instead, the task list is a **file** in the repo — `TASKS.md` — that is
> committed and pushed like any other. That is the shared channel.
>
> **Precise.** `TASKS.md` is the durable board; `tools/board_gate.py` fails CI if a `done` row
> carries no evidence or cites a path that does not exist. An item not on the board is a
> defect in the board.
>
> **Machine.** `python3 tools/board_gate.py` · statuses are `done | in_progress | todo | blocked`.

## 4.6 Coordinate addressing: how a tab names itself

> **Plain.** Because several tabs exist, each needs an **address** so work can be attributed
> and so "which tab did this?" is answerable. The address is the **conversation id**.
>
> **Precise.** Each OpenHands conversation has a UUID; the workspace metadata records it
> (`meta.json`), and the on-disk event log is keyed by it. A tab's identity is therefore
> `<conversation_id>`; its checkout commit (`HEAD`) and its branch are the rest of its
> coordinate.
>
> **Machine.** This tab's conversation id is read from
> `/var/openhands/conversations/<id>/meta.json`; `git rev-parse HEAD` gives its commit.

---

# PART 5 — THE GATES THAT SPECIFICALLY POLICE KNOWLEDGE AND DOCS

These are the gates a *writer* must satisfy. They are the reason this document is filed where
it is.

## 5.1 `tools/kb_index.py` — the knowledge-base index (registers)

> **Plain.** Every readable file in the repo must be filed in exactly one "shelf" (register):
> the governance files, the corpus under `docs/`, the interactive web apps, shipped assets,
> machine proof, or build config. The tool builds an index (`docs/INDEX.md`) and a manifest,
> and fails if a readable file is unfiled, duplicated, or if the index is stale.
>
> **Precise.** Registers: `A-apparatus` (root governance), `B-knowledge` (`docs/**`),
> `C-skillbase` (root `*.html`), `D-asset` (`app/src/main/assets/**`), `E-evidence`
> (`proof/**`), `F-config` (dependency/query manifests). A file that resolves to no register
> is a defect. Two readable files with the same hash must be a *declared mirror*, or the gate
> fails (NEVER #11/#15/#16, §22).
>
> **Machine.** `python3 tools/kb_index.py` (check) · `python3 tools/kb_index.py --write`
> (regenerate `docs/INDEX.md` + `docs/kb_manifest.json`).

**Consequence for this file:** because it is a human-readable `.md`, it belongs in the
`B-knowledge` register, i.e. under `docs/`. Putting it at the repo root would make it
**misfiled** and fail the gate. So it lives at `docs/GITHUB-CICD-AGENTS-KB.md`.

## 5.2 `tools/doc_path_gate.py` — every cited path must exist

> **Plain.** When a doc says "run `tools/foo.sh`", that file must actually exist. This gate
> extracts every backticked path from the governance docs and fails if one does not resolve.
>
> **Precise.** The "disconnecting fragment" defect (SPI-23): docs keep naming files that
> moved. The gate resolves a cited path if it is tracked, if a tracked file ends with it, or
> if it is on a small allowlist of generated/external artifacts.
>
> **Machine.** `python3 tools/doc_path_gate.py` — checks `README.md`, `AGENTS.md`,
> `DARKITH.md`, `RESUME.md`.

**Consequence:** if you cite a path in one of those four docs, it must be real. (This file is
not one of the four, but it follows the same discipline anyway.)

## 5.3 `tools/consolidate_docs.sh` — one canonical doc, no overlaps

> **Plain.** Four old docs were collapsed into `DARKITH.md`. This tool checks that the old
> copies are gone and never deletes anything unless the canonical doc already contains every
> law.
>
> **Precise.** Idempotent (running twice is a no-op). `--check` is the gate form (SPI-15).
> The overlapping docs are `singularity_progressive_continuum.md`, `RECONCILIATION.md`,
> `DEFICIT_LEDGER.md`, `VERSION.md`.
>
> **Machine.** `bash tools/consolidate_docs.sh --check`.

## 5.4 `tools/law_gate.py` — a law must name a gate

> **Plain.** Every rule the repo declares (each `NEVER`, `MUST`, `SPI`) must name an
> executable gate that exists on disk. A rule with no gate is a note, not a law.
>
> **Precise.** Scans `DARKITH.md` for law headings; each body must cite a `tools/*.py|sh|js`
> that exists, or fail. The `[NOTE: not yet gated]` escape hatch is itself forbidden — build
> the gate.
>
> **Machine.** `python3 tools/law_gate.py`.

## 5.5 `tools/blueprint_gate.py` — no injected instructions

> **Plain.** The Operator's specification corpus must never contain text that orders an agent
> to act (a prompt injection). This gate fails CI if it does.
>
> **Machine.** `python3 tools/blueprint_gate.py`.

## 5.6 The mirror rule (one page, two names, byte-identical)

> **Plain.** Sometimes the same page must exist in two places (the app ships it as an asset;
> the repo root serves it in a browser). That is allowed **only** if the two copies are
> byte-for-byte identical, and the gate fails the moment they drift.
>
> **Precise.** Declared mirror: `app/src/main/assets/darkith_ui.html` == `darkith-inscriber.html`.
>
> **Machine.** `tools/kb_index.py` and the `D-2b` block of `tools/ci.sh` both enforce it.

---

# PART 6 — THE FULL GATE CATALOGUE (every check, what it guards)

`bash tools/ci.sh` runs all of these. Learn them as "one gate = one past failure, made
impossible to repeat."

| Gate (file) | The question it answers | The failure it prevents |
|---|---|---|
| `build/verify.py --fast` | do the core invariants still hold? | silent drift of the built artifacts |
| `build/savf-cli-test.py` | does the audit engine's command line behave? | a broken auditing tool |
| `tools/darkbot.py selftest` | does the dependency bot work? | a bot that corrupts the manifest |
| `tools/secret_gate.py` | is a credential committed? | a leaked password in history |
| `tools/secret_gate.py selftest` | is the secret gate itself correct? | a gate that misses secrets |
| `tools/fracture_scout.py selftest` | is the novelty hunter's logic correct? | junk "novelty" tasks |
| `tools/syntax_gate.py` | any unclosed Kotlin comment? | a file that silently swallows code |
| `tools/api_level_gate.py` | a high-API call with no guard? | a crash on older Android |
| `tools/icon_gate.py` | a missing/malformed app icon? | a blank launcher tile |
| `tools/board_gate.py` | a `done` item with no evidence? | a board that rots |
| `tools/law_gate.py` | a law with no gate? | rules that are only notes |
| `tools/circadian_gate.py` | is time reported in the right zone? | confusing UTC with the Operator's clock |
| `tools/download_gate.py` | does a link download instead of opening a viewer? | a delivery that does not deliver |
| `tools/stall_gate.py` | is a named deficit left open across deliveries? | a problem nobody ever closes |
| `tools/synchrony_gate.py` | does every surface have one clock? | two clocks disagreeing |
| `tools/synchrony_pulse.py` | is the activity record current? | a stale heartbeat |
| `tools/convergence_gate.py` | do two derivations of one fact agree? | two answers that disagree |
| `tools/nt_gate.py` | is every corpus claim carried and resolved? | a cited-but-absent rule |
| `tools/nt_sensor.py` | does the example name a symbol the real SDK has? | a "fixed" example that cannot compile |
| `tools/omega_deficit.py` | is the progress-deficit indicator honest? | a stagnant board |
| `tools/board_pulse.sh --check` | is the board pushed in real time? | a sibling tab working blind |
| `tools/fork_integrity_gate.sh` | one tree? every symbol in-tree? does it compile? | divergent trees (§19, MUST #11) |
| `tools/delivery_gate.sh --source-only` | are the source-level laws held? | declaring delivery with open loopholes |
| `tools/bridge_contract_audit.py` | does the app bridge's contract match? | a UI calling a method that is gone |
| `tools/consolidate_docs.sh --check` | one canonical doc? | overlapping docs drifting |
| `tools/doc_path_gate.py` | does every cited path exist? | docs pointing at moved files |
| `tools/blueprint_gate.py` | any injected instruction? | a prompt-injection payload on `main` |
| `tools/kb_index.py` | every readable file filed, no dupes? | docs "all over the place" |
| `tools/test_darktools.js` | do the dev toolkits pass? | broken in-app tools |
| `tools/test_omega_reader.js` | does the reader page behave? | a broken reading surface |
| `tools/test_icon_forge.js` | does the icon forger behave? | bad generated icons |
| `tools/source_inspector.py trial` | are the 10 charges calibrated? | a miscalibrated gate |
| `tools/source_inspector.py inspect` | any open blocker or new escrow debt? | debt that never goes down |
| `tools/test_inscriber.js` | does the studio boot in a DOM? | a studio that will not start |
| `build/omega/omega-test.mjs` | does the engine harness pass? | a broken engine |
| `build/omega/ui-test.py` | does the real UI render? | a blank screen on launch |
| no-signing-material check | is any key file tracked? | a leaked signing key |
| APK store rule | are `resources.arsc`/`*.so` stored, not deflated? | "App not installed" |
| `tools/install_gate.py` | will the APK actually install? | the failure a user feels |
| `tools/runtime_gate.py` | does the launcher paint? | the second failure a user feels |
| fork-singularity (inline) | two divergent copies of a file? | a fork (NEVER #11) |
| version truth (inline) | does `AGENTS.md` state the manifest's version? | docs disagreeing with the app |
| `build/make-oneshot.py --check` | is the one-shot installer current? | a vanished installer |
| `build&install.sh` check | does the entrypoint exist, Gradle-free? | a broken build entrypoint |

> **Plain.** You do not have to memorise this table. You have to remember **one** command:
> `bash tools/ci.sh`. If it exits `0`, every check above passed. If it does not, it prints
> exactly which one failed.
>
> **Machine.** `bash tools/ci.sh; echo "exit=$?"`

---

# PART 7 — THE DARKITH REPO MECHANICS (the real procedures)

This is the "how you actually operate" part. Each procedure is given as the exact command,
then what it does, then what can go wrong.

## 7.1 Start of a session — restore

> **Plain.** A fresh machine has nothing. Restore pulls the latest checkpoint from GitHub.
>
> **Machine.**
> ```bash
> bash tools/restore.sh
> ```
> Clones the repo if absent, otherwise fast-forwards/rebases it to the latest `main`. Requires
> the `GITHUB_TOKEN` secret.

## 7.2 Save at the end — continuity

> **Plain.** Commit everything and push it, so the next session (on a different machine) can
> pick it up.
>
> **Machine.**
> ```bash
> bash tools/continuity.sh "what I just did"
> ```
> Refuses to push if signing-key material ever becomes tracked, then hands off to
> `tools/sync.sh` to converge and publish (never forced).

## 7.3 Integrate with the other tabs — sync

> **Plain.** Bring in whatever the other tabs pushed, then publish yours. If you both changed
> the same lines, it stops and asks a human.
>
> **Machine.**
> ```bash
> bash tools/sync.sh            # converge: fetch + (ff | push | rebase) + push
> bash tools/sync.sh --check    # report only; non-zero if not in sync
> ```
> Exit codes: `0` in sync · `1` dirty tree · `2` no remote · `3` conflict (needs a human).

## 7.4 The full ritual — converge

> **Plain.** When two tabs may have both written: integrate, then re-run every check on the
> merged result. Two steps, both required.
>
> **Machine.** `bash tools/converge.sh` (= `sync.sh` then `ci.sh`).

## 7.5 Run all checks — CI

> **Machine.** `bash tools/ci.sh` — exits `0` only if every gate passed.

## 7.6 Package the delivery — pack

> **Plain.** Build the downloadable artifacts (the whole project zip, the web-app zip) and
> the single hub page that lists them with sizes and hashes.
>
> **Machine.** `python3 tools/pack_delivery.py` — deterministic (same inputs → byte-identical
> output), so re-running proves idempotency.

## 7.7 Prove the delivery — the delivery gate

> **Plain.** Do not *say* "delivered". *Run the gate*; the word is the gate's output, not your
> assertion.
>
> **Machine.** `bash tools/delivery_gate.sh . --source-only` (source laws) or with an APK for
> the full check. The **loophole registry** names every way a delivery can lie: L-01 manifest
> version, L-02 APK version, L-03 self-report, L-04 artifact-built, L-05 artifact-signed,
> L-06 artifact-aligned, L-07 fork singularity, L-08 bridge contract, L-09 asset parity,
> L-10 currency, L-11 registry non-empty.

## 7.8 Build the Android app — the raw chain

> **Plain.** The app is compiled by a seven-step chain that runs on the phone (or a sandbox),
> deliberately without Gradle. The seven steps: package resources (`aapt2 compile`), link them
> (`aapt2 link`, which also makes `R.java`), compile Kotlin (`kotlinc`), turn it into Android
> bytecode (`d8` → `classes.dex`), pack the APK (`zip`), align it (`zipalign`), sign it
> (`apksigner`).
>
> **Machine.**
> ```bash
> bash build.sh . Darkith com.darkith.transliaison
> ```
> (Gradle is forbidden — SPI-1 — because it exhausts the phone's memory.)

## 7.9 One-shot build-and-install

> **Plain.** The single command the Operator runs on the phone to build and install.
>
> **Machine.** `bash build&install.sh`.

## 7.10 Verify a claim (the SPI-2 habit)

> **Plain.** Never trust a summary — read the actual bytes. If a doc says a file contains X,
> open the file and look. The terminal "lies" (its scrollback is incomplete), so write
> results to a file and read the file.
>
> **Precise.** **SPI-2** read exact bytes before writing; **SPI-4** log to disk and read from
> disk; **SPI-6** read the whole log, not just the first error.
>
> **Machine.** `git show <hash>:<path> | sed -n '1,40p'` · `sha256sum <file>` · `wc -c <file>`.

## 7.11 Read the whole history / find lost work

> **Machine.** `git log --oneline` · `git reflog` · `git show <hash>` ·
> `git log --format='%h %ad %an %s' --date=iso`.

## 7.12 The naming conventions

> **Plain.** Commit messages start with a type; tasks have statuses; laws have prefixes.
>
> **Machine.** Commit types seen here: `fix:`, `docs:`, `chore:`, `reconcile:`, `proof:`,
> `board:`, `feat:`. Task statuses: `done | in_progress | todo | blocked`. Law prefixes:
> `NEVER #N` (forbidden), `MUST #N` (required), `SPI-N` (Sovereign Sandbox Protocol rule).

---

# PART 8 — EMERGENCIES (what to do when it breaks)

## 8.1 "My tree changed under me."

You integrated another tab's push (or `restore.sh`/`sync.sh` fast-forwarded). It is not data
loss. Check what landed: `git log --oneline -10`. To see exactly what moved:
`git reflog`. If you had uncommitted edits and they are gone, `git reflog` + `git stash list`
usually recover them.

## 8.2 "There is a merge/rebase conflict."

Stop. Read the conflicted files (`git diff --name-only --diff-filter=U`). Open each, choose
the correct content between the `<<<<<<<`/`=======`/`>>>>>>>` markers, then
`git add <file>` and `git rebase --continue`. To back out entirely: `git rebase --abort`.
`tools/sync.sh` deliberately stops (exit 3) rather than guessing.

## 8.3 "CI fails and I don't know which gate."

Run it and read the last lines: `bash tools/ci.sh 2>&1 | tail -40`. Each gate prints
`--- <name>: PASS|FAIL`. Fix the named gate, re-run. Remember SPI-6: read the *whole* log,
not just the first error.

## 8.4 "A secret got committed."

This is the most serious emergency. A committed secret is **already leaked** (forks, backups,
logs, history) — deleting the file does **not** un-leak it. You must (1) remove it and
(2) **rotate** (replace) the credential. The repo's CI pushes a device alert when this
happens (`tools/security_alert.py`).

## 8.5 "I pushed something wrong."

Do **not** force-push. Add a new commit that corrects it (git history is append-only by
design here). If it was a credential, see 8.4.

## 8.6 "The build says `aapt2 not found` / `kotlinc not found`."

The toolchain is not installed. Run `bash tools/fetch_toolchain.sh` and rebuild.

## 8.7 "I think I lost commits."

`git reflog` is the diary; `git reset --hard <hash>` returns to any entry. This repo recovered
lost work this way.

---

# PART 9 — WHAT CI/CD MEANS *FOR THIS PROJECT SPECIFICALLY*

> **Plain.** For an ordinary project, CI/CD is "test, then ship". Here it is also the
> project's **memory** and its **safety system**: because the machines forget, the repo is the
> brain; because several agents write, the gates are the referee.
>
> **Precise.** Three roles, one pipeline:
> 1. **Memory** — `tools/restore.sh` / `tools/continuity.sh` make the ephemeral machine
>    survivable; the remote is the only durable state.
> 2. **Referee** — `tools/sync.sh` / `tools/converge.sh` keep parallel tabs on one history
>    without losing a commit.
> 3. **Proof** — `tools/ci.sh` / `tools/delivery_gate.sh` make every claim checkable, so
>    "done" means a green gate, not an assertion.
>
> **Machine.** The three commands that carry all of it: `restore.sh`, `converge.sh`,
> `delivery_gate.sh`.

The single most important sentence in this file:

> **On an ephemeral machine, un-pushed work does not exist. Commit and push early and often.**

---

# PART 10 — THE README FORMAT SPEC (so you can write docs this way too)

This knowledge base follows the repo's **invariant README format** (specified in `README.md`
§15). The rules, restated so you can apply them anywhere:

1. **Declare the audience and the prerequisite.** Say who it is for and what they must
   already know (ideally nothing).
2. **Define before use.** Define every specialist term and abbreviation at first use; list
   them in a glossary.
3. **State the principle first.** Say what is unique in principle before the mechanics.
4. **Narrate three tongues.** **Plain** (beginner) / **Precise** (engineer) / **Machine**
   (literal file or command).
5. **Inventory every asset.** List each source file, what it is, and its function; mark
   generated things as generated.
6. **Correct the point of view.** Name and correct the reader's wrong default assumption
   before building on it.
7. **Answer terminally.** End every answer with the reader able to act; never a bare pointer.
8. **Break the loop.** Close with the list of questions the reader would ask next, each
   already answered above.

**Why it works:** a confusing doc leaks in exactly four places — a term used before it is
defined, an expert-only register, an uncorrected wrong mental model, and an answer that opens
a new question. Rules 2, 4, 6, 7 close those four leaks; rule 8 proves the closure.

---

# PART 11 — THE MASTER GLOSSARY (every term, one line)

Alphabetical. This is the "no jargon left unexplained" list.

**A–C**

| Term | Meaning |
|---|---|
| **Actions** | GitHub's built-in robot that runs your checks when you push. |
| **Adapter** | Thin provider-specific glue that calls provider-neutral logic; here the YAML calls `tools/ci.sh`. |
| **AGENTS.md** | The file that briefs an AI agent on how to work in the repo. |
| **Artifact** | A produced file (an APK, a zip) — as opposed to source code. |
| **Auto-merge** | Merging a change automatically, but only after checks pass and nothing changed since. |
| **Behind / Ahead** | Your branch is behind (the remote has newer commits) or ahead (you have newer commits). |
| **Blocked** | A board status meaning "cannot proceed". |
| **Board** | `TASKS.md`, the durable task list that survives the machine. |
| **Branch** | A movable label pointing at one line of work; the main one is `main`. |
| **CD** | Continuous Delivery / Deployment — shipping automatically after CI. |
| **CI** | Continuous Integration — running all checks on every change. |
| **Clone** | Downloading a full copy of a repo, history included. |
| **Commit** | One saved snapshot with a message and a unique hash. |
| **Conflict** | Two changes to the same lines that git cannot reconcile without a human. |
| **Converge** | Integrate the other tabs' commits, then re-run the gate on the merged tree. |
| **Cron** | The timer syntax for scheduled jobs (`minute hour day month weekday`). |
| **Currency (of a tree)** | Whether a tree is up to date — provable only by its own clean compile (NEVER #13). |

**D–G**

| Term | Meaning |
|---|---|
| **Deficit** | A named, tracked gap; must be closed or descoped within one cycle (NEVER #17). |
| **Dependabot** | A bot that proposes dependency updates. |
| **Delivery** | Producing and publishing the artifacts; gated so the word "delivered" is earned. |
| **Descope** | Formally decide a requirement is out of scope, with a written reason. |
| **Divergence** | Two lines of history (or two copies of a file) that disagree. |
| **Ephemeral** | Temporary; wiped when the session ends. This project's machines are ephemeral. |
| **Fail closed / open** | On inability to check: fail closed = treat as failure (safe); fail open = treat as pass (unsafe). |
| **Fast-forward** | A merge where nothing else changed, so the label just slides forward. |
| **Fetch** | Download the remote's commits without merging them yet. |
| **Fork** | A copy of a repo (or a divergent copy of a tree); reconciling forks is a recurring theme. |
| **Gate** | One automatic check that passes (exit 0) or fails (non-zero). |
| **Git** | The version-control program on your machine. |
| **GitHub** | A website that hosts a copy of your repo and adds PRs and Actions. |
| **Gradle** | The conventional Android build system; forbidden here (SPI-1). |

**H–L**

| Term | Meaning |
|---|---|
| **Hash** | A unique ID computed from content; same content → same hash. |
| **HEAD** | The commit you are currently standing on. |
| **Hub (delivery)** | The one page listing every artifact with size + hash (ONE SURFACE). |
| **Idempotent** | Running it twice gives the same result as running it once. |
| **Index (kb)** | `docs/INDEX.md`, the universal index of readable files by register. |
| **In sync** | Local and remote point at the same commit. |
| **Issue** | A numbered to-do or bug report in the tracker. |
| **Law (NEVER/MUST/SPI)** | A rule; each must name an executable gate or it is only a note (SPI-15). |
| **Least privilege** | Giving a robot the smallest permissions it needs. |
| **Local** | The copy on your machine (as opposed to the remote). |
| **Loophole registry** | The named list of every way a delivery can lie (L-01…L-11). |

**M–P**

| Term | Meaning |
|---|---|
| **main** | The conventional name of the primary branch. |
| **Merge** | Joining two branches; the easy case is a fast-forward. |
| **Merge request (MR)** | GitLab's name for a pull request. |
| **Mirror** | One file under two names, kept byte-identical by a gate. |
| **Note (vs. law)** | A rule with no executable gate; forbidden by SPI-15. |
| **NT (Noveltreatise)** | The repo's long-form reasoning corpus in `docs/nt/`. |
| **Origin** | The default nickname for your remote. |
| **Pass / Fail** | A gate's two outcomes: exit 0 / non-zero. |
| **PR (Pull Request)** | A proposal to merge one branch into another, with review and checks. |
| **Private / Public repo** | Visible only to authorized users / visible to anyone. |
| **Proof** | Machine-generated evidence under `proof/`; proof lives in the artifact, not the claim. |
| **Provider** | A hosting/CI company (GitHub, GitLab, Bitbucket, Jenkins). |
| **Pull** | Fetch the remote's commits and merge them into yours. |
| **Push** | Send your commits up to the remote. |

**Q–Z**

| Term | Meaning |
|---|---|
| **Rebase** | Replay your commits on top of newer work; the replayed commits get new hashes. |
| **Reflog** | Git's private diary of everywhere HEAD has been; the recovery net. |
| **Register (kb)** | A "shelf" a readable file is filed on: A-apparatus … F-config. |
| **Remote** | The copy of the repo on GitHub (or another server). |
| **Repo (repository)** | A folder git tracks, with full history in `.git`. |
| **Restore** | Pull the latest checkpoint onto a fresh machine (`tools/restore.sh`). |
| **Runner** | The temporary cloud computer that executes a workflow job. |
| **SAVF** | The repo's offline auditing engine (`savf.html` / `savf.py`). |
| **Schedule** | A workflow trigger that runs on a timer (cron). |
| **Secret** | A credential injected at run time; never committed. |
| **SHA** | A cryptographic hash; used to pin actions and identify commits. |
| **SPI** | Sovereign Sandbox Protocol — the repo's rule family (SPI-1, SPI-2, …). |
| **Stash** | A drawer for parking uncommitted changes temporarily. |
| **Status** | `git status` (what changed) or a board row's state (`done`/`todo`/…). |
| **Sync** | Integrate the remote's commits and publish yours, without force (`tools/sync.sh`). |
| **Tag** | A permanent name for one commit (e.g. a release). |
| **Termux** | The Android app that gives you a terminal on the phone. |
| **Three-way merge** | A merge that creates a merge commit because both lines diverged. |
| **TOCTOU** | "Time-of-check to time-of-use": acting on a check that has gone stale. |
| **Token** | A password-like secret a program uses to authenticate. |
| **Untracked** | A file git is not (yet) tracking. |
| **Upstream** | The original repo you forked from. |
| **Version control** | Remembering every version of your files; git is the tool. |
| **Working tree** | The actual files on disk that you edit. |
| **Workflow** | A recipe file in `.github/workflows/` that Actions follows. |
| **YAML** | The human-readable configuration format workflow files are written in. |

---

# PART 12 — THE LOOP BREAKER (every follow-up question, pre-answered)

These are the questions a beginner asks next. Each is answered terminally — you should be able
to act after reading the answer, with no new question opened.

1. **"What is git, in one line?"** The program on your machine that remembers every version
   of your files.
2. **"What is GitHub, in one line?"** The website that stores a copy of your repo so it
   survives, and runs checks when you push.
3. **"What is the difference between git and GitHub?"** Git is the tool; GitHub is one place
   to host the copy. Git works without GitHub; GitHub needs git.
4. **"What is a repo?"** A folder git tracks, including its hidden `.git` history.
5. **"What is a commit?"** One saved snapshot plus a message; it has a unique hash.
6. **"What is a hash?"** A unique ID computed from content; same content, same ID.
7. **"What is a branch?"** A movable label pointing at one line of work.
8. **"What is `main`?"** The conventional name of the primary branch.
9. **"What is push vs. pull?"** Push sends your commits up; pull brings the remote's down.
10. **"What is a remote / origin?"** The online copy of the repo; `origin` is its default
    nickname.
11. **"What is a clone?"** A full local copy of a repo, history included.
12. **"What is a merge?"** Joining two branches; the easy case is a fast-forward.
13. **"What is a fast-forward?"** A merge where nothing else changed, so the label just slides.
14. **"What is a rebase?"** Replaying your commits on top of newer work; the commits get new
    hashes. Used here so parallel tabs keep one clean history without force-pushing.
15. **"What is a conflict?"** Two edits to the same lines git cannot reconcile; a human picks.
16. **"What is a stash?"** A drawer for parking uncommitted changes temporarily.
17. **"What is the reflog?"** Git's diary of everywhere HEAD has been; how lost work is found.
18. **"What is `.gitignore`?"** The list of paths git should ignore (caches, output, secrets).
19. **"What is a tag?"** A permanent name for one commit, e.g. a release.
20. **"What is a pull request (PR)?"** A proposal to merge a branch into `main`, with review
    and automatic checks. GitLab calls it a merge request (MR).
21. **"What is an issue?"** A numbered to-do or bug report in the tracker.
22. **"What is CI?"** Running all your checks automatically on every change.
23. **"What is CD?"** Shipping automatically after CI (delivery) or automatically to users
    (deployment).
24. **"What is a gate?"** One automatic check that passes or fails. Many gates chained = CI.
25. **"What is GitHub Actions?"** GitHub's robot that runs your workflow files when you push.
26. **"What is a workflow / job / step / runner?"** The recipe file / a task inside it / one
    command in a task / the temporary cloud computer that runs it.
27. **"What is a token / secret?"** A password-like credential a program uses; never committed.
28. **"What is `AGENTS.md`?"** The file that briefs an AI agent on how to work in the repo.
29. **"Why does `AGENTS.md` matter here?"** The machines are ephemeral, so committed files are
    the only memory; `AGENTS.md` carries that knowledge between sessions.
30. **"What is the difference between `README.md`, `AGENTS.md`, `DARKITH.md`, `RESUME.md`?"**
    The front door / the staff handbook / the canonical ledger / the emergency card.
31. **"Did another VM pull my tree?"** No. Tabs cannot reach each other's disks. A sibling tab
    *pushed* to GitHub and this tab *fetched* from GitHub. The shared remote is the only
    channel.
32. **"Why did my tree change under me?"** Because a sibling tab pushed and this tab
    integrated those commits (fast-forward or rebase). It is not data loss.
33. **"How do parallel tabs avoid clobbering each other?"** They integrate through
    `tools/sync.sh` (never forced) and re-gate the merged tree with `tools/converge.sh`.
34. **"How do I name/address a tab?"** By its conversation id (`meta.json`); plus its `HEAD`
    commit and branch.
35. **"What is the durable board?"** `TASKS.md` — a committed file, not the in-session list.
36. **"How do I start a session?"** `bash tools/restore.sh`.
37. **"How do I save?"** `bash tools/continuity.sh "message"`.
38. **"How do I integrate the other tabs?"** `bash tools/sync.sh` (or `converge.sh` to also
    re-run the gate).
39. **"How do I run all checks?"** `bash tools/ci.sh`.
40. **"How do I build the app?"** `bash build.sh . Darkith com.darkith.transliaison`, or
    `bash build&install.sh` on the phone. Never Gradle (SPI-1).
41. **"How do I prove a delivery?"** `bash tools/delivery_gate.sh …` — the word "delivered" is
    the gate's output, not your assertion.
42. **"What is a loophole?"** A named way a delivery can lie; the registry lists all eleven.
43. **"What is a deficit?"** A named gap; it must be closed or descoped within one cycle.
44. **"What is a mirror?"** One file under two names, kept byte-identical by a gate.
45. **"What is idempotent?"** Running it twice equals running it once.
46. **"What is fail closed?"** When a check cannot run, treat it as failure (the safe default).
47. **"Where does a new doc go?"** Under `docs/` (the `B-knowledge` register), or
    `tools/kb_index.py` will fail it as misfiled. This file is there for exactly that reason.
48. **"What if a doc cites a file that moved?"** `tools/doc_path_gate.py` fails; fix the path.
49. **"What if I find a rule with no check?"** `tools/law_gate.py` fails it; build the gate.
50. **"What if a secret got committed?"** It is already leaked: remove it and **rotate** it.
    Deleting the file does not un-leak it.
51. **"Can I force-push to fix history?"** No. This repo never force-pushes; add a correcting
    commit instead.
52. **"What does 'ephemeral' force me to do?"** Commit and push early and often; un-pushed work
    does not exist.
53. **"Where is the chat scrollback if the app won't scroll?"**
    `/var/openhands/conversations/<id>/events/`.
54. **"What is the raw chain?"** The seven-step, Gradle-free Android build: `aapt2 compile` →
    `aapt2 link` → `kotlinc` → `d8` → `zip` → `zipalign` → `apksigner`.
55. **"What is the one command I must remember?"** `bash tools/ci.sh`.

If you reached this line with a question not in this list, the fix is written at the top of
this file: add the question here and answer it above. This list is the acceptance test.

---

*This file is the beginner knowledge base for `Deobfugazi/darkith-forge`. It is governed by
the same laws it describes: if a term is undefined or a question is unanswerable, that is a
defect in this file. It is filed in the `B-knowledge` register (`docs/`), indexed by
`tools/kb_index.py`, and every path it cites is checked by `tools/doc_path_gate.py`.*
