#!/usr/bin/env bash
# Creates a new Pico project repo from this template and configures it fully.
#
# Prerequisites:
#   1. gh CLI installed and logged in (gh auth login)
#   2. NOTION_TOKEN set in your environment, e.g. in ~/.zshrc:
#      export NOTION_TOKEN="ntn_..."
#
# Usage:
#   ./new_project.sh MyProjectName [--public]

set -euo pipefail

PROJECT_NAME="${1:?Usage: $0 <ProjectName> [--public]}"
VISIBILITY="--private"
[[ "${2:-}" == "--public" ]] && VISIBILITY="--public"

GITHUB_USER="$(gh api user --jq .login)"
REPO="$GITHUB_USER/$PROJECT_NAME"

echo "Creating repo $REPO from template Meo98/Pico_Template..."
gh repo create "$REPO" \
  --template "Meo98/Pico_Template" \
  $VISIBILITY \
  --clone

echo "Setting NOTION_TOKEN secret..."
if [[ -z "${NOTION_TOKEN:-}" ]]; then
  echo "  NOTION_TOKEN not set in environment."
  echo "  Add this to your ~/.zshrc and restart the shell:"
  echo "    export NOTION_TOKEN=\"ntn_...\""
  echo "  Then run manually:"
  echo "    gh secret set NOTION_TOKEN --repo $REPO"
else
  gh secret set NOTION_TOKEN --repo "$REPO" --body "$NOTION_TOKEN"
  echo "  Secret set."
fi

echo ""
echo "Done! Project created at: https://github.com/$REPO"
echo ""
echo "Next steps:"
echo "  cd $PROJECT_NAME"
echo "  Rename hardware/Template.* to hardware/$PROJECT_NAME.*"
echo "  Edit firmware/pico_config.py with your pin assignments"
