#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_FILES = sorted(ROOT.rglob("*.md"))

DOC_LINK_PATTERN = re.compile(r"`((?:docs|backend|scripts)/[^`]+\.md)`")
STALE_PATH_PATTERN = re.compile(r"docs/PHASE(?:2|3)_COMPLETION\.md")
HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def iter_lines(path: Path):
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f, start=1):
            yield idx, line.rstrip("\n")


def resolve_doc_path(raw: str) -> Path:
    return (ROOT / raw).resolve()


def normalize_heading(text: str) -> str:
    heading = text.strip()
    heading = re.sub(r"\s+#+$", "", heading)
    heading = heading.lower()
    heading = re.sub(r"[^\w\-\s]", "", heading)
    heading = re.sub(r"\s+", "-", heading)
    heading = re.sub(r"-+", "-", heading)
    return heading.strip("-")


def collect_anchors(md_path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for _, line in iter_lines(md_path):
        m = HEADER_PATTERN.match(line)
        if not m:
            continue
        raw = m.group(2)
        base = normalize_heading(raw)
        if not base:
            continue
        count = counts.get(base, 0)
        if count == 0:
            anchor = base
        else:
            anchor = f"{base}-{count}"
        counts[base] = count + 1
        anchors.add(anchor)
    return anchors


def is_external_link(target: str) -> bool:
    lower = target.lower()
    return lower.startswith(("http://", "https://", "mailto:"))


def resolve_markdown_target(source: Path, target: str) -> Path:
    return (source.parent / target).resolve()


def main() -> int:
    problems: list[str] = []
    anchor_index: dict[Path, set[str]] = {}

    for md in MARKDOWN_FILES:
        anchor_index[md.resolve()] = collect_anchors(md)

    for md in MARKDOWN_FILES:
        rel = md.relative_to(ROOT)
        for line_no, line in iter_lines(md):
            if STALE_PATH_PATTERN.search(line):
                problems.append(
                    f"[stale-ref] {rel}:{line_no} contains deprecated completion filename"
                )

            for m in DOC_LINK_PATTERN.finditer(line):
                raw = m.group(1)
                target = resolve_doc_path(raw)
                if not target.exists():
                    problems.append(
                        f"[missing-link] {rel}:{line_no} -> {raw} does not exist"
                    )

            for m in MARKDOWN_LINK_PATTERN.finditer(line):
                target = m.group(1).strip()
                if not target or is_external_link(target):
                    continue

                if "#" not in target:
                    continue

                path_part, anchor_part = target.split("#", 1)
                anchor = anchor_part.strip().lower()
                if not anchor:
                    continue

                if not path_part:
                    target_md = md.resolve()
                else:
                    target_md = resolve_markdown_target(md, path_part)

                if target_md.suffix.lower() != ".md":
                    continue

                if not target_md.exists():
                    problems.append(
                        f"[missing-link] {rel}:{line_no} -> {path_part} does not exist"
                    )
                    continue

                target_anchors = anchor_index.get(target_md)
                if target_anchors is None:
                    target_anchors = collect_anchors(target_md)
                    anchor_index[target_md] = target_anchors

                if anchor not in target_anchors:
                    shown = path_part if path_part else rel.as_posix()
                    problems.append(
                        f"[missing-anchor] {rel}:{line_no} -> {shown}#{anchor}"
                    )

    if problems:
        print("Documentation check failed:\n")
        for p in problems:
            print(f"- {p}")
        print(f"\nTotal issues: {len(problems)}")
        return 1

    print("Documentation check passed. No stale refs, missing links, or missing anchors found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
