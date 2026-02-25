#!/usr/bin/env bash
# Validate RiskOS Agent project structure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

ERRORS=0

check_dir() {
  if [ ! -d "$1" ]; then
    echo "FAIL: Missing directory: $1"
    ((ERRORS++)) || true
    return 1
  fi
  return 0
}

check_file() {
  if [ ! -f "$1" ]; then
    echo "FAIL: Missing file: $1"
    ((ERRORS++)) || true
    return 1
  fi
  return 0
}

echo "=== RiskOS Agent Structure Check ==="

# Required directories
check_dir ".agents/skills"
check_dir "config"
check_dir "workspace"
check_dir "scaffolds/templates"

# Required files
check_file "AGENTS.md"
check_file "SOUL.md"
check_file "HEARTBEAT.md"
check_file "risk-os-v2-spec.md"
check_file "README.md"

# Skill validation
if [ -d ".agents/skills" ]; then
  for skill_dir in .agents/skills/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    if [ ! -f "$skill_dir/SKILL.md" ]; then
      echo "FAIL: Skill '$skill_name' missing SKILL.md"
      ((ERRORS++)) || true
    else
      # Basic YAML frontmatter check
      if ! grep -q "name:" "$skill_dir/SKILL.md" || ! grep -q "description:" "$skill_dir/SKILL.md"; then
        echo "WARN: Skill '$skill_name' SKILL.md may lack required YAML (name, description)"
      fi
    fi
  done
fi

# Config placeholders
for cfg in config/phase-config.yaml config/ta-config.yaml config/risk-rules.yaml; do
  if [ ! -f "$cfg" ]; then
    echo "WARN: Config not found (optional): $cfg"
  fi
done

if [ $ERRORS -eq 0 ]; then
  echo "PASS: Structure check complete"
  exit 0
else
  echo "FAIL: $ERRORS error(s) found"
  exit 1
fi
