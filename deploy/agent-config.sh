#!/bin/sh
# Install the agents' shared instructions and skills. Run as the user
# "agent" on the agents box, from the unpacked TTL source directory:
#   sh deploy/agent-config.sh
#
# ~/.agents holds the only copy. Each harness is pointed at it:
#   Codex:       ~/.codex/AGENTS.md -> ~/.agents/AGENTS.md; reads ~/.agents/skills itself
#   pi:          ~/.pi/agent/AGENTS.md -> ~/.agents/AGENTS.md; reads ~/.agents/skills itself
#   Claude Code: ~/.claude/CLAUDE.md imports ~/.agents/AGENTS.md; ~/.claude/skills -> ~/.agents/skills
set -eu

[ "$(id -un)" = agent ] || { echo "Run this as the user agent on the agents box." >&2; exit 1; }

mkdir -p ~/.agents ~/.codex ~/.pi/agent ~/.claude ~/ttl
rm -rf ~/.agents/skills
cp agents/AGENTS.md ~/.agents/AGENTS.md
cp -r agents/skills ~/.agents/skills
cp deploy/mcpcall.py ~/ttl/mcpcall.py

ln -sfn ~/.agents/AGENTS.md ~/.codex/AGENTS.md
ln -sfn ~/.agents/AGENTS.md ~/.pi/agent/AGENTS.md
printf '@~/.agents/AGENTS.md\n' > ~/.claude/CLAUDE.md
[ -L ~/.claude/skills ] || [ ! -e ~/.claude/skills ] || { echo "~/.claude/skills is a real directory; move it first" >&2; exit 1; }
ln -sfn ~/.agents/skills ~/.claude/skills

# pi and node live under ~/.local/node/bin.
grep -q '.local/node/bin' ~/.profile 2>/dev/null ||
    printf '\nexport PATH="$HOME/.local/node/bin:$PATH"\n' >> ~/.profile
