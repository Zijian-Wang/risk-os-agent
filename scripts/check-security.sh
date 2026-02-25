#!/usr/bin/env bash
# Security check for RiskOS Agent: secrets, env exposure, unsafe patterns

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

ERRORS=0
WARNINGS=0

# Patterns that suggest hardcoded secrets (case-insensitive)
SECRET_PATTERNS=(
  "api_key\s*=\s*['\"]"
  "apikey\s*=\s*['\"]"
  "secret\s*=\s*['\"]"
  "password\s*=\s*['\"][^'\"]+['\"]"
  "token\s*=\s*['\"][a-zA-Z0-9_-]{20,}['\"]"
  "sk-[a-zA-Z0-9]{20,}"
  "ghp_[a-zA-Z0-9]{36}"
)

# Files to skip
SKIP_FILES=(
  ".git"
  "node_modules"
  ".env.example"
  "check-security.sh"
)

should_skip() {
  local f="$1"
  for s in "${SKIP_FILES[@]}"; do
    [[ "$f" == *"$s"* ]] && return 0
  done
  return 1
}

echo "=== RiskOS Agent Security Check ==="

# 1. Check .gitignore for sensitive files
for f in .env .env.local .env.*.local token.json credentials; do
  if [ -f "$f" ] && ! grep -q "$f" .gitignore 2>/dev/null; then
    echo "WARN: Sensitive file '$f' exists but may not be in .gitignore"
    ((WARNINGS++)) || true
  fi
done

# 2. Scan for secret patterns in code/config files
while IFS= read -r f; do
  should_skip "$f" && continue
  if grep -E "api_key\s*=\s*['\"][^'\"]{12,}|apikey\s*=\s*['\"][^'\"]{12,}|secret\s*=\s*['\"][^'\"]{12,}" "$f" 2>/dev/null | grep -v "example\|placeholder\|TODO\|XXX\|\.env"; then
    echo "WARN: Possible hardcoded credential in $f"
    ((WARNINGS++)) || true
  fi
  if grep -E "sk-[a-zA-Z0-9]{32,}|ghp_[a-zA-Z0-9]{36}" "$f" 2>/dev/null; then
    echo "FAIL: Likely API key/token in $f"
    ((ERRORS++)) || true
  fi
done < <(find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.mjs" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) ! -path "./.git/*" ! -path "./node_modules/*" 2>/dev/null)

# 3. Check scripts for unsafe eval/exec of user input
for f in scripts/*.sh .agents/skills/*/scripts/* 2>/dev/null; do
  [ -f "$f" ] || continue
  if grep -E "eval\s+\$|exec\s+\$|\.\s+\$" "$f" 2>/dev/null; then
    echo "WARN: Script may execute unvalidated input: $f"
    ((WARNINGS++)) || true
  fi
done

# 4. .env in .gitignore
if [ -f .gitignore ] && ! grep -qE "^\.env$|^\.env\.\*" .gitignore; then
  echo "WARN: Add .env and .env.* to .gitignore"
  ((WARNINGS++)) || true
fi

echo ""
if [ $ERRORS -gt 0 ]; then
  echo "FAIL: $ERRORS error(s), $WARNINGS warning(s)"
  exit 1
elif [ $WARNINGS -gt 0 ]; then
  echo "PASS with $WARNINGS warning(s) — review above"
  exit 0
else
  echo "PASS: Security check complete"
  exit 0
fi
