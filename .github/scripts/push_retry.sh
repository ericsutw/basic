#!/usr/bin/env bash
# Commit the given paths and push them, rebasing onto the remote branch first.
# Retries so an external machine pushing quotes and Actions pushing state
# do not fail the job with a non-fast-forward or a transient 403.
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: push_retry.sh <message> <path> [path...]" >&2
  exit 2
fi

MESSAGE="$1"
shift
PATHS=("$@")

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

added=0
for path in "${PATHS[@]}"; do
  if [[ -e "$path" ]]; then
    git add -- "$path"
    added=1
  fi
done

if [[ "$added" -eq 0 ]]; then
  echo "No matching paths to commit."
  exit 0
fi

if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi

git commit -m "$MESSAGE"

BRANCH="${GITHUB_REF_NAME:-main}"

resolve_rebase() {
  if [[ ! -d .git/rebase-merge && ! -d .git/rebase-apply ]]; then
    return 1
  fi
  echo "Rebase conflict; keeping this commit's versions of: ${PATHS[*]}" >&2
  git checkout --theirs -- "${PATHS[@]}" || true
  git add -- "${PATHS[@]}" || true
  if git diff --cached --quiet && git diff --quiet; then
    GIT_EDITOR=: git rebase --skip
  else
    GIT_EDITOR=: git rebase --continue
  fi
}

for attempt in 1 2 3 4 5; do
  if git pull --rebase origin "$BRANCH"; then
    if git push origin "HEAD:${BRANCH}"; then
      echo "Pushed to ${BRANCH}."
      exit 0
    fi
  else
    resolve_rebase || true
    if [[ -d .git/rebase-merge || -d .git/rebase-apply ]]; then
      git rebase --abort || true
    fi
    if git push origin "HEAD:${BRANCH}"; then
      echo "Pushed to ${BRANCH}."
      exit 0
    fi
  fi
  echo "Push attempt ${attempt} failed; retrying." >&2
  sleep $((2 ** attempt))
done

echo "ERROR: could not push to ${BRANCH} after retries." >&2
exit 1
