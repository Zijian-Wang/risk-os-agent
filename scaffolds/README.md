# Scaffolds

Templates and scripts for creating OpenClaw skills and validating the RiskOS Agent project.

## Templates

| Path | Purpose |
|------|---------|
| `templates/skill-template/` | Base template for new skills |

## Scripts

Run from repo root:

| Script | Purpose |
|--------|---------|
| `./scripts/create-skill.sh <name>` | Create a new skill in `.agents/skills/<name>/` |
| `./scripts/check-structure.sh` | Validate project structure and skill layout |
| `./scripts/check-security.sh` | Check for secrets, env exposure, unsafe patterns |

## Creating a Skill

```bash
./scripts/create-skill.sh my-skill-name
```

Then edit `.agents/skills/my-skill-name/SKILL.md`:
- Set `name` and `description` in YAML frontmatter
- Add `metadata.openclaw.requires` if the skill needs bins/env
- Write instructions for the agent

## Skill Checklist

- [ ] `name` is lowercase, hyphens only
- [ ] `description` is specific and includes trigger terms
- [ ] Instructions are concise (SKILL.md under ~500 lines)
- [ ] No hardcoded secrets; use env vars
- [ ] Run `check-structure.sh` and `check-security.sh` after changes
