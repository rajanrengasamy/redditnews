---
description: Sync local and remote git - fetch, pull, push with conflict handling
allowed-tools: Bash(git:*), Bash(git status:*), Bash(git fetch:*), Bash(git pull:*), Bash(git push:*), Bash(git stash:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git remote:*)
argument-hint: [--force | --rebase | --stash | branch-name]
---

# Git Sync Command

Synchronize local repository with remote, keeping everything in sync.

## Current State

Branch: !`git branch --show-current 2>/dev/null || echo "not a git repo"`
Remote: !`git remote -v 2>/dev/null | head -1 || echo "no remote"`
Status: !`git status --porcelain 2>/dev/null | head -5 || echo "not a git repo"`

## Instructions

Perform a complete git sync operation with the following steps:

### 1. Pre-flight Checks
- Verify this is a git repository
- Check for uncommitted changes
- Identify the current branch and its upstream

### 2. Handle Uncommitted Changes
If there are uncommitted changes:
- If `--stash` flag is in $ARGUMENTS: stash changes before sync, pop after
- Otherwise: warn the user and ask how to proceed (commit, stash, or abort)

### 3. Fetch & Update
- Run `git fetch --all --prune` to get latest remote state
- Show any new commits on remote that aren't local
- Show any local commits that aren't on remote

### 4. Pull Remote Changes
- If `--rebase` flag is in $ARGUMENTS: use `git pull --rebase`
- Otherwise: use `git pull` (merge strategy)
- If conflicts occur: stop, show the conflicts, and help resolve them

### 5. Push Local Changes
- If `--force` flag is in $ARGUMENTS: use `git push --force-with-lease`
- Otherwise: use `git push`
- If push fails due to divergence: explain the situation and suggest options

### 6. Final Status Report
Provide a summary:
- Commits pulled from remote
- Commits pushed to remote
- Current sync status (ahead/behind/even)
- Any warnings or issues

## Branch Override
If a branch name is provided in $ARGUMENTS (not a flag), sync that specific branch instead of the current one.

## Examples
- `/sync` - Standard sync of current branch
- `/sync --rebase` - Sync using rebase instead of merge
- `/sync --stash` - Auto-stash changes, sync, then pop stash
- `/sync --force` - Force push after pulling (use with caution)
- `/sync main` - Sync the main branch specifically
