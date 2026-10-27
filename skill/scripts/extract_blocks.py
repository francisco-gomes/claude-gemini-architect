#!/usr/bin/env python3
"""Extract the bash blocks of a plan's PART B so next_block.py can tell which block Gemini asks to run.

Usage: python3 extract_blocks.py <plan.md> <out.json>
Needs a '# PART B' heading; block order becomes B0, B1, B2...
Exit codes: 0 written, 1 no PART B heading or no bash block (nothing written), 2 wrong usage.
"""
import json
import re
import sys

PART_B = re.compile(r"^# PART B\b", re.M)
BASH_BLOCK = re.compile(r"```bash\n(.*?)```", re.S)


def extract_part_b_blocks(text):
    """PART B's bash blocks, whitespace collapsed, in order. Raises ValueError when there are none."""
    heading = PART_B.search(text)
    if heading is None:
        raise ValueError("the plan has no '# PART B' heading")
    blocks = [" ".join(b.split()) for b in BASH_BLOCK.findall(text[heading.start():])]
    if not blocks:
        raise ValueError("PART B has no ```bash blocks")
    return blocks


def main(argv):
    if len(argv) != 3:
        print("usage: python3 extract_blocks.py <plan.md> <out.json>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        text = f.read()
    try:
        blocks = extract_part_b_blocks(text)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    with open(argv[2], "w", encoding="utf-8") as f:
        json.dump(blocks, f, ensure_ascii=False)
    print(f"{len(blocks)} blocks (B0..B{len(blocks) - 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
