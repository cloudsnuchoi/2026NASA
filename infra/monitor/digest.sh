#!/usr/bin/env bash
# Read-only progress digest for the 2026NASA hackathon (TEAM_SPEC 9).
# Usage: REPO=cloudsnuchoi/2026NASA STALE_MIN=60 ./infra/monitor/digest.sh > digest.md
# Needs: gh (authenticated), jq. Makes no writes to GitHub.
set -euo pipefail
REPO="${REPO:-cloudsnuchoi/2026NASA}"
STALE_MIN="${STALE_MIN:-60}"
now_epoch=$(date +%s)
echo "# Digest $(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M KST') · ${REPO}"
echo
echo "## Open issues by assignee"
gh issue list -R "$REPO" --state open --limit 200 --json number,title,assignees,labels,updatedAt \
  | jq -r '.[] | [(.assignees|map(.login)|join(",")|if .=="" then "(unassigned)" else . end), "#\(.number)", .title, (.labels|map(.name)|join(","))] | @tsv' \
  | sort | awk -F'\t' '{printf "- **%s** %s %s `%s`\n",$1,$2,$3,$4}'
echo
echo "## Blocked"
gh issue list -R "$REPO" --state open --label blocked --json number,title --jq '.[] | "- #\(.number) \(.title)"' 2>/dev/null || echo "- (no blocked label yet)"
echo
echo "## Stale (no update > ${STALE_MIN} min)"
gh issue list -R "$REPO" --state open --limit 200 --json number,title,updatedAt,assignees \
  | jq -r --argjson now "$now_epoch" --argjson m "$STALE_MIN" '.[] | select(.assignees|length>0) | select(($now - (.updatedAt|fromdateiso8601)) > ($m*60)) | "- #\(.number) \(.title) (\(.assignees|map(.login)|join(",")))"'
echo
echo "## Open PRs"
gh pr list -R "$REPO" --state open --json number,title,author,reviewDecision,isDraft \
  --jq '.[] | "- #\(.number) \(.title) by \(.author.login) review=\(.reviewDecision // "NONE") draft=\(.isDraft)"'
echo
echo "## Merged in last ${STALE_MIN} min"
since=$(date -u -d "-${STALE_MIN} min" +%Y-%m-%dT%H:%M:%SZ)
gh pr list -R "$REPO" --state merged --limit 50 --json number,title,mergedAt \
  | jq -r --arg s "$since" '.[] | select(.mergedAt >= $s) | "- #\(.number) \(.title)"'

echo
echo "## Latest STATUS comments (per author)"
since=$(date -u -d "2026-11-14T15:00:00Z" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1d +%Y-%m-%dT00:00:00Z)
gh api "repos/${REPO}/issues/comments?since=${since}&per_page=100&sort=updated&direction=desc" \
  | jq -r '
      [ .[] | select(.body | startswith("STATUS:") or test("^STATUS:"))
        | {
            login: .user.login,
            created: .created_at,
            updated: .updated_at,
            url: .html_url,
            issue: (.issue_url | split("/") | last),
            body: .body
          }
      ]
      | group_by(.login)
      | map(sort_by(.updated) | last)
      | .[]
      | "- **\(.login)** #\(.issue) \(.updated) — \((.body | split("\n") | map(select(length>0)) | .[0:3] | join(" / ")))"'
echo
