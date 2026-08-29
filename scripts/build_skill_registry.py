#!/usr/bin/env python3
"""Build or verify the explicit Skill Registry."""

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skill_runtime.core import build_registry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the committed registry is stale")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "skills",
        help="manifest.json file or directory containing per-Skill manifests",
    )
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "skill-registry" / "skill-registry.json")
    args = parser.parse_args()
    if args.check:
        from skill_runtime.core import SkillRegistry

        registry = SkillRegistry.from_file(args.output)
        stale = registry.check_drift(args.manifest)
        print("DRIFT" if stale else "OK")
        return int(stale)
    build_registry(args.manifest, args.project_root, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
