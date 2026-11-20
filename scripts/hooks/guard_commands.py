"""PreToolUse guard for AI shell commands (DECISIONS D14, D1; card P0-02).

Reads the hook JSON from stdin. Exits 2 (blocks the command, message on stderr) when the command:
- pushes, hard-resets, cleans, or force-pushes;
- checks out / switches to / merges into main;
- deletes a .blend file.
Exit 0 lets the command run.
"""
import json
import re
import sys

RULES = [
    (r"\bgit\s+push\b", "git push is blocked (push only when Prasad asks; do it by hand)"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard is blocked"),
    (r"\bgit\s+clean\b", "git clean is blocked"),
    (r"\bgit\s+(checkout|switch)\s+(-\S+\s+)*main\b", "switching to main is blocked (work on Beta)"),
    (r"\bgit\s+merge\b.*\bmain\b|\bgit\s+checkout\s+main\b.*&&.*\bgit\s+merge\b", "merging involving main is blocked"),
    (r"\bgit\s+branch\s+(-D|-d|--delete)\s+(main|Beta)\b", "deleting main/Beta is blocked"),
    (r"(\brm\b|\bdel\b|\berase\b|Remove-Item|\bunlink\b|os\.remove|shutil\.rmtree)[^\n|;&]*\.blend\b", "deleting .blend files is blocked (D1)"),
    (r"\bgit\s+rm\b[^\n|;&]*\.blend\b", "git rm of .blend files is blocked (D1: archive with git mv instead)"),
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    for pattern, message in RULES:
        if re.search(pattern, command, flags=re.IGNORECASE):
            print(f"BLOCKED by scripts/hooks/guard_commands.py: {message}. Command: {command[:200]}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
