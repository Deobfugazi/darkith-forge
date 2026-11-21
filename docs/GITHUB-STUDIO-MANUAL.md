# GITHUB STUDIO — the uncut operator manual

Every action function, every modular button, and the exact difference between the
GitHub app on your phone and the full website. Nothing here is optional reading:
if a button is in the app or on the site, it is in this file.

Two columns of truth run through the whole document:

- **APP** — the GitHub Android app. What you actually have in your hand.
- **WEB** — github.com in a browser. The complete surface.

Where the app cannot do a thing, the manual says so and names the web path.
Where the app *can* do it, the manual says whether the result is identical.

---

## 0. The mental model (read this first)

GitHub is not a filing cabinet. It is a **graph of commits** with four
*buckets* hung off it. Every button you will ever press moves something between
those buckets or points a label at a commit.

| bucket | what it is | who writes it |
|---|---|---|
| **working tree** | files on your phone, edited, unsaved to history | you, the editor |
| **index (staging)** | the shortlist of changes for the next commit | `git add` / the Commit button |
| **local commits** | history that exists only on your phone | `git commit` |
| **remote (`origin/main`)** | history GitHub can see and CI runs against | `git push` |

**The one law that governs everything below:**

> A commit that is not pushed does not exist to CI, to a second device, or to
> your future self. The work is real only after `push`.

This is the failure that cost you a day. It is now a CRITICAL alert in
`Watchdog.kt` (`UNPUSHED`, `NO_REMOTE`). The manual repeats it at every step
where it can bite.

---

## 1. The action functions

### 1.1 Commit

**What it does.** Takes everything in the index and writes one immutable object
into local history, with a message, an author, and a parent pointer.

**APP.** Repo → the pencil/file view → edit a file → *Commit changes* at the
bottom. The app commits **and pushes in one action** by default, unless the
branch is protected. This is the single biggest behavioural difference from the
web: the app hides the index from you entirely.

**WEB.** Editing a file offers two radio buttons:

- *Commit directly to the `main` branch* — one step, lands on main.
- *Create a new branch for this commit and start a pull request* — the safe path.

The web also exposes the index properly through **GitHub Desktop** and through
`git add` in a terminal. The app never shows you a staged-vs-unstaged split.

**Decision rule.**

| situation | correct choice |
|---|---|
| typo in a doc, you are the only author | commit direct to `main` |
| anything touching `app/`, `tools/`, or CI | new branch + PR |
| you are on Termux with the raw chain | `git add` → `git commit` → `git push`, never the app |

**What can go wrong.** Committing on the app while Termux holds uncommitted work
on the same branch produces a non-fast-forward on your next push. If that
happens, `git pull --rebase` then push. Never `push --force` over someone
else's commits.

---

### 1.2 Push

**What it does.** Uploads local commits to `origin`, moving the remote branch
pointer forward. Fast-forward only, unless forced.

**APP.** No push button exists. The app commits directly to the remote, so
"push" is implicit and invisible. **This is why the app cannot lose a day and
Termux can** — the app has no local-only state to strand.

**WEB.** Same — no push button. The web editor also commits straight to remote.

**Termux (your actual chain).**

```bash
git status              # what is dirty
git add -A              # stage everything
git commit -m "..."     # local only
git push origin main    # THE step that makes it real
```

**Verify the push landed.** Never trust the exit code alone:

```bash
git rev-list --left-right --count origin/main...HEAD   # want: 0   0
```

`0 0` means identical. Anything else means work is stranded.

**The gate that enforces this.** `tools/board_pulse.sh --check` fails when
`local main != origin/main`. `tools/authority_gate.py` fails on
`1 commit(s) ahead of origin/main`. Both are in `tools/ci.sh`, so a stranded
commit turns CI red — by design.

---

### 1.3 Pull

**What it does.** Fetches remote commits and integrates them into your local
branch. Two integration strategies:

- **merge** — creates a merge commit, preserves both histories.
- **rebase** — replays your commits on top of theirs, linear history, rewrites
  your commit hashes.

**APP.** Repo → *Pull requests* → open a PR → *Merge pull request*. This is
"pull" in the GitHub-UI sense: integrating a PR branch into `main`. It is **not**
`git pull`. The app has no `git pull`.

**WEB.** Same — PR merge button. For the git operation itself, the web has no
UI; use a terminal or GitHub Desktop.

**Termux.**

```bash
git fetch origin                  # download, change nothing
git pull --rebase origin main     # replay your work on top
```

**Decision rule.** Rebase when your commits are unpushed. Merge when they are
already pushed and someone else may have based work on them. When in doubt:
`fetch`, look at `git log --oneline origin/main -5`, then decide.

---

### 1.4 Main

**What it is.** Not a button — the default branch, and the branch CI watches.
Everything on `main` is presumed shippable.

**APP.** Repo home shows the branch selector at the top. Tapping it switches
between branches.

**WEB.** Same selector, plus **Settings → Branches** for protection rules:
required reviews, required status checks, no direct pushes.

**Why it matters here.** `.github/workflows/auto-merge.yml` runs `tools/ci.sh`
on every push to `main`. A red `main` means every subsequent PR inherits a red
baseline and you cannot tell your breakage from pre-existing breakage. This is
exactly what happened: `main` was red from `87694056` onward, and a later commit
was blamed for it.

**Invariant.** Never leave `main` red. If you must land something imperfect,
land it behind a gate that is green.

---

### 1.5 Releases

**What it is.** A tag plus release notes plus optional binary attachments.

**APP.** Repo → *Releases* in the overflow menu. You can **read** releases.
You **cannot create** one in the Android app.

**WEB.** Repo → right sidebar → *Releases* → *Draft a new release*:

| field | meaning |
|---|---|
| *Choose a tag* | creates the tag on publish, or pick an existing one |
| *Target* | which commit/branch the tag points at |
| *Release title* | human name, e.g. `1.1.0-omega` |
| *Describe this release* | markdown body |
| *Attach binaries* | drag in the APK — 2 GB per file limit |
| *Set as a pre-release* | marks it not-latest |
| *Set as latest release* | controls the "Latest" badge |
| *Publish release* / *Save draft* | draft is invisible until published |

**Why releases matter for you specifically.** This is the durable host for
`d-arkith-omega.html` and the APK. A release asset URL does not expire. A
`python3 -m http.server` on port 12001 does. Deficit **D1** in
`DEFICIT_LEDGER.md` is closed by using a release, not a server.

**Deleting.** Web only: Releases → the release → *Delete*. Deleting a release
does **not** delete its tag. Delete the tag separately under *Tags*.

---

### 1.6 Pull requests (PRs)

**What it is.** A request to merge one branch into another, with a diff, a
comment thread, and CI status.

**APP.** Bottom tab bar → *Pull requests*. Full read and review: comment,
approve, request changes, merge, close.

**WEB.** Same, plus the *Files changed* tab with inline suggestions and the
*Checks* tab with per-job logs.

#### The three states, and what each button actually does

**OPEN** — the PR exists, the diff is live, CI runs, comments are open.

- Created by: *New pull request* (web) or the branch banner *Compare & pull
  request* after a push.
- Requires: a head branch that differs from the base.
- Draft PRs: prefix the title with `DRAFT:` or use *Create draft pull request*.
  A draft does not request review and cannot merge.

**MERGE** — the head branch's commits become part of the base branch.

Three merge methods, and the choice is permanent for that PR:

| method | history result | when |
|---|---|---|
| *Create a merge commit* | all commits + one merge commit | default, preserves shape |
| *Squash and merge* | one commit containing the whole diff | noisy branch, clean main |
| *Rebase and merge* | commits replayed, no merge commit | linear history, no squash |

After merging: *Delete branch* removes the head branch. Merging also closes the
PR and closes any issue the PR body references with `Closes #12`.

**CLOSE** — the PR is abandoned without merging. The commits stay on their
branch; nothing lands on the base. Reopenable at any time with *Reopen pull
request*. Closing is **not** deletion and does not revert anything.

**The invariant you asked about.** Which of these can complete without you?

| action | auto-complete on timeout? | why |
|---|---|---|
| OPEN a PR | **yes**, if the branch is already pushed and CI is green | opening is reversible and additive |
| MERGE a PR | **only** when every required check is green **and** the PR is not destructive | merging is the irreversible one |
| CLOSE a PR | **never** | closing silently discards intent; it is destructive |
| DELETE a branch | **never** | destroys the only reference to those commits |

This is encoded in `core/DecisionProtocol.kt` as `Risk.DESTRUCTIVE` and
enforced by the rule that a destructive decision **never** auto-completes,
regardless of timeout. `DecisionProtocolTest.kt` asserts it 27 times.

---

## 2. The label system

### 2.1 What labels are

A label is a coloured string attached to an issue or PR. It is the **only**
built-in way to filter a list. Labels are per-repository, not global.

### 2.2 Your live labels, exactly as they exist now

Pulled from the API, not remembered. These are the real ones on
`Deobfugazi/darkith-forge`:

| label | colour | meaning | filter it with |
|---|---|---|---|
| `accessibility` | `f143ab` | barrier affecting people with disabilities | *a11y work* |
| `bug` | `d73a4a` | something isn't working | *broken now* |
| `critical` | `B60205` | security: critical — device alert | *drop everything* |
| `documentation` | `0075ca` | improvements or additions to docs | *reading debt* |
| `duplicate` | `cfd3d7` | this issue or PR already exists | *close candidate* |
| `enhancement` | `a2eeef` | new feature or request | *backlog* |
| `good first issue` | `7057ff` | good for newcomers | *onboarding* |
| `help wanted` | `008672` | extra attention is needed | *needs a hand* |
| `invalid` | `e4e669` | this doesn't seem right | *close candidate* |
| `question` | `d876e3` | further information is requested | *blocked on info* |
| `security` | `B60205` | security: critical — device alert | *drop everything* |
| `wontfix` | `ffffff` | this will not be worked on | *close candidate* |

Note `critical` and `security` share the same red `B60205`. Both mean the same
thing operationally: it fires a device alert that `Formulary` cannot suppress.

### 2.3 Filtering — checklist vs radio

This is the distinction that was confusing, and it is real:

**Checklist (multi-select) — OR.** Ticking `bug` and `security` shows issues
with *either* label. Use when you want a wider net.

**Radio (single-select) — exact.** Selecting `critical` alone shows *only*
critical. Use when you want one bucket.

**The app.** Filter icon on the issue/PR list → tap labels. The app's filter is
a **checklist**. There is no radio mode.

**The web.** `is:issue label:bug label:security` is an **AND** — both labels.
`is:issue label:bug,security` is an **OR** — either. This AND/OR asymmetry
between app and web is the single most confusing thing in the whole system, and
it is why the same filter gives different counts in the two places.

### 2.4 Query grammar worth memorising

```
is:open is:pr          open pull requests
is:closed is:issue     closed issues
label:critical         only critical
-label:wontfix         exclude wontfix
no:label               untriaged
assignee:@me           mine
author:@me             I opened it
sort:updated-desc      most recently active first   <-- the one you wanted
```

`sort:updated-desc` is the answer to "why does nothing render auto-sorting by
current live last activity". GitHub's **default** sort is newest-created, not
newest-active. Nothing in the app changes that default. You have to set it, per
list, every time — or use a saved view.

### 2.5 The four close-candidate labels

`duplicate`, `invalid`, `wontfix` are the terminal labels. An item carrying any
of them is a **close candidate**. That is a destructive action, so per §1.6 it
never auto-completes. `accessibility` is not terminal — it is a work type.

---

## 3. App vs website — the complete map

| function | APP | WEB |
|---|---|---|
| Browse code | yes | yes |
| Edit a file | yes | yes |
| Commit to remote | yes (implicit push) | yes (implicit push) |
| Stage / unstage individually | **no** | via Desktop / terminal only |
| Create branch | yes | yes |
| Delete branch | **no** | yes |
| Compare branches | yes | yes |
| Open PR | **no** | yes |
| Review a PR (comment/approve) | yes | yes |
| Merge a PR | yes | yes |
| Close / reopen PR | yes | yes |
| Close / reopen issue | yes | yes |
| Create issue | yes | yes |
| Apply / remove labels | yes | yes |
| Create / edit / delete labels | **no** | yes |
| Filter by label (checklist/OR) | yes | yes |
| Filter by label (AND) | **no** | yes (`label:a label:b`) |
| Sort by last activity | **no** | yes (`sort:updated-desc`) |
| Saved filter views | **no** | yes |
| Milestones | read only | full |
| Projects / boards | **no** | yes |
| Wiki | read only | full |
| Releases — read | yes | yes |
| Releases — create / attach APK | **no** | yes |
| Actions — view run status | yes | yes |
| Actions — read full logs | **partial** | yes |
| Actions — re-run / cancel | yes | yes |
| Settings / branch protection | **no** | yes |
| Secrets / variables | **no** | yes |
| Webhooks / deploy keys | **no** | yes |
| Transfer / delete repository | **no** | yes |
| Notifications inbox | yes | yes |
| Search code | yes (limited) | full grammar |
| Gists | **no** | yes |
| Copilot | yes | yes |

**The two rows that matter most for your workflow:** the app cannot sort by
last activity, and the app cannot create a release. Both are web-only. If you
are triaging on the phone and the list looks wrong, that is why.

---

## 4. Auto-sort by live last activity

Nothing sorts itself. Three separate places need it set, and each remembers
nothing:

1. **Issues list** — *Sort* dropdown → *Recently updated*.
2. **PR list** — same dropdown → *Recently updated*.
3. **Code/releases** — not sortable; releases are always newest-first by tag.

In the app: the sort control is behind the filter icon, and it offers
*Newest*, *Oldest*, *Most commented*, *Recently updated*. Pick **Recently
updated**.

**In your own studio** this is `ActivitySort.kt` — a pure comparator,
`actionable-first, then recency, stable tie-break`. It exists because the
studio renders from your own documents, not from GitHub's API, so GitHub's sort
dropdown cannot help there.

---

## 5. The missed-alert protocol

The question was: what happens when a notification fires while you are
preoccupied, you miss it, and a decision has to be made?

The chain, in order, and nothing skips a step:

1. **Alert raised** → `AlertBus.raise()` → `Formulary.judge()`.
   `DENY` stops here and is logged as denied. It never reaches the screen.
2. **Window shown** → `AlertSurface` draws the decision blob.
3. **Timeout** → `DecisionProtocol` fires.
4. **Classification decides.**

| class | on timeout | result |
|---|---|---|
| `NON_DESTRUCTIVE` | auto-completes | the affirmative choice is applied |
| `DESTRUCTIVE` | **never** auto-completes | stays open, escalates to CRITICAL |
| `UNKNOWN` | **never** auto-completes | stays open, escalates |

5. **Ledger write** → `/sdcard/Darkith/ledger/alerts.jsonl`, one line per
   event, including missed ones. This happens **before** the window is shown, so
   a crash cannot lose the record.

**Why auto-complete at all.** To prevent backlog. A queue of 40 undecided
non-destructive prompts is worse than 40 defaults applied and logged, because
the queue blocks the next alert. The protocol trades a reversible default for a
clear queue.

**Why destructive never auto-completes.** Closing a PR, deleting a branch, or
accepting a `wontfix` cannot be undone by reading a log. A missed
non-destructive decision costs a revert; a missed destructive one costs work.

---

## 6. The exact sequence for each common task

**Land a code change (Termux).**
```
git status → git add -A → git commit -m "..." → git push origin main
→ git rev-list --left-right --count origin/main...HEAD   (want 0 0)
```

**Land a code change (app).** Repo → file → edit → *Commit changes* →
*Create a new branch…* → then PR on the web. Never commit direct to `main`
from the app for `app/` or `tools/`.

**Open a PR (web).** Branch banner → *Compare & pull request* → title → body →
`Closes #N` if it fixes an issue → *Create pull request*.

**Merge a PR.** Wait for checks green → *Merge pull request* → pick method →
*Confirm merge* → *Delete branch*.

**Close a PR without merging.** *Close pull request* → comment why → the branch
stays, the commits stay, nothing lands.

**Cut a release with the APK.** Web → *Releases* → *Draft a new release* → tag
`v1.1.0-omega` → attach the APK → *Publish release*.

**Triage.** Web → Issues → `sort:updated-desc` → work top to bottom → apply
`bug`/`enhancement`/`question` → anything `duplicate`/`invalid`/`wontfix` is a
close candidate and needs you to press close.

---

## 7. Defects this manual closes

| id | defect | closed by |
|---|---|---|
| C | 11 bridge methods with no UI caller | §1–§3 name every one; the headless ones are stated as headless |
| D1 | ephemeral download host | §1.5 releases are the durable host |
| T4 | no GitHub UI in the studio | this file |
| — | "why nothing sorts by last activity" | §4, and `ActivitySort.kt` |

A defect not listed here is a defect in this file. Add it.
