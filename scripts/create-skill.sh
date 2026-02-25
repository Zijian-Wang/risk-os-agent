#!/usr/bin/env bash
# Create a new OpenClaw skill from template

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_DIR="$REPO_ROOT/scaffolds/templates/skill-template"
SKILLS_DIR="$REPO_ROOT/.agents/skills"

if [ -z "$1" ]; then
  echo "Usage: $0 <skill-name>"
  echo "  skill-name: lowercase, hyphens only (e.g. my-new-skill)"
  exit 1
fi

NAME="$1"
SKILL_DIR="$SKILLS_DIR/$NAME"

# Validate name: lowercase, hyphens, alphanumeric
if ! echo "$NAME" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*$'; then
  echo "Error: skill name must be lowercase letters, numbers, hyphens only"
  exit 1
fi

if [ -d "$SKILL_DIR" ]; then
  echo "Error: skill '$NAME' already exists at $SKILL_DIR"
  exit 1
fi

mkdir -p "$SKILLS_DIR"
mkdir -p "$SKILL_DIR" "$SKILL_DIR/scripts" "$SKILL_DIR/references"

# Copy template and substitute name
sed "s/skill-name/$NAME/g" "$TEMPLATE_DIR/SKILL.md" > "$SKILL_DIR/SKILL.md"

echo "Created skill: $SKILL_DIR"
echo "  - Edit SKILL.md with your instructions"
echo "  - Add scripts/ or references/ as needed"
