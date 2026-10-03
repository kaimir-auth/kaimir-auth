#!/usr/bin/env bash
set -euo pipefail

BRANCH="${1:?Usage: publish-to-branch.sh <branch> <source-dir> [commit-message]}"
SOURCE_DIR="${2:?Usage: publish-to-branch.sh <branch> <source-dir> [commit-message]}"
COMMIT_MESSAGE="${3:-Update generated profile SVGs}"

: "${GITHUB_TOKEN:?GITHUB_TOKEN must be set}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must be set}"
: "${GITHUB_WORKSPACE:?GITHUB_WORKSPACE must be set}"

SOURCE_PATH="${GITHUB_WORKSPACE}/${SOURCE_DIR}"
[ -d "${SOURCE_PATH}" ] || { echo "Source directory not found: ${SOURCE_PATH}" >&2; exit 1; }

WORKDIR="$(mktemp -d)"
trap 'rm -rf "${WORKDIR}"' EXIT

cd "${WORKDIR}"
git init -q
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git remote add origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"

git fetch --depth=1 origin "${BRANCH}" 2>/dev/null || true
if git rev-parse --verify "refs/remotes/origin/${BRANCH}" >/dev/null 2>&1; then
  git checkout -q -b "${BRANCH}" "origin/${BRANCH}"
else
  git checkout -q --orphan "${BRANCH}"
fi

git rm -rf . >/dev/null 2>&1 || true
git clean -fdx -q
cp -R "${SOURCE_PATH}/." "${WORKDIR}/"

git add -A
if git diff --cached --quiet; then
  echo "No generated changes for ${BRANCH}."
  exit 0
fi

git commit -m "${COMMIT_MESSAGE}" -q
git push origin "HEAD:${BRANCH}" --force
