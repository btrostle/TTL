#!/bin/sh
# Install the agents' shared instructions and skills. Run as the user
# "agent" on the agents box, from the unpacked TTL source directory:
#   sh deploy/agents/agent-config.sh
#
# ~/.agents holds the only copy. Each harness is pointed at it:
#   Codex:       ~/.codex/AGENTS.md -> ~/.agents/AGENTS.md; reads ~/.agents/skills itself
#   pi:          ~/.pi/agent/AGENTS.md -> ~/.agents/AGENTS.md; reads ~/.agents/skills itself
#   Claude Code: ~/.claude/CLAUDE.md imports ~/.agents/AGENTS.md; ~/.claude/skills -> ~/.agents/skills
set -eu

[ "$(id -un)" = agent ] || { echo "Run this as the user agent on the agents box." >&2; exit 1; }

mkdir -p ~/.agents/skills ~/.codex ~/.pi/agent ~/.claude ~/ttl
cp deploy/agents/AGENTS.md ~/.agents/AGENTS.md
# Replace only the repo's skills; Claude Code keeps synced skills here too.
for s in deploy/agents/skills/*; do
    rm -rf ~/.agents/skills/"$(basename "$s")"
    cp -r "$s" ~/.agents/skills/
done
cp deploy/agents/mcpcall.py deploy/agents/upload-config.py deploy/agents/esql.py deploy/agents/siem-fleet-setup.py ~/ttl/
# Range configs as committed (placeholders, no secrets). upload-config.py
# fills them from ~/.config/ttl/siem.env at upload.
rm -rf ~/ttl/ranges
cp -r deploy/ludus/ranges ~/ttl/ranges
cp docs/ranges.md ~/ttl/ranges.md
git rev-parse HEAD > ~/.agents/REVISION 2>/dev/null || cp REVISION ~/.agents/REVISION

ln -sfn ~/.agents/AGENTS.md ~/.codex/AGENTS.md
ln -sfn ~/.agents/AGENTS.md ~/.pi/agent/AGENTS.md
printf '@~/.agents/AGENTS.md\n' > ~/.claude/CLAUDE.md
[ -L ~/.claude/skills ] || [ ! -e ~/.claude/skills ] || { echo "~/.claude/skills is a real directory; move it first" >&2; exit 1; }
ln -sfn ~/.agents/skills ~/.claude/skills

# pi and node live under ~/.local/node/bin.
grep -q '.local/node/bin' ~/.profile 2>/dev/null ||
    printf '\nexport PATH="$HOME/.local/node/bin:$PATH"\n' >> ~/.profile
