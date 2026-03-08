"""CLI to install HashMind SKILL.md into agent skill directories."""

import argparse
import shutil
import sys
from pathlib import Path


def get_skill_source() -> Path:
    return Path(__file__).resolve().parent / "SKILL.md"


def main():
    parser = argparse.ArgumentParser(
        description="Install HashMind SKILL.md to your AI agent's skill directory"
    )
    parser.add_argument(
        "--global", "-g",
        dest="global_install",
        action="store_true",
        help="Install to ~/.claude/skills/ and ~/.agents/skills/",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Custom output directory",
    )
    args = parser.parse_args()

    source = get_skill_source()
    if not source.exists():
        print(f"Error: SKILL.md not found at {source}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        targets = [args.output]
    elif args.global_install:
        home = Path.home()
        targets = [
            home / ".claude" / "skills" / "hashmind",
            home / ".agents" / "skills" / "hashmind",
        ]
    else:
        targets = [Path.cwd()]

    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        dest = target / "SKILL.md"
        shutil.copy2(source, dest)
        print(f"Installed SKILL.md -> {dest}")


if __name__ == "__main__":
    main()
