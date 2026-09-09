"""Command-line entry point for reproducible prototype runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .simulation import Simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic annual Amphoreus world simulation.")
    parser.add_argument("--seed", type=int, default=20260905, help="Root seed for all simulation random streams.")
    parser.add_argument("--ticks", type=int, default=100, help="Maximum number of simulated years.")
    parser.add_argument("--json", type=Path, help="Write a structured result to this path.")
    args = parser.parse_args()

    result = Simulation(args.seed, args.ticks).run()
    print(f"种子: {result.seed}")
    print(f"终态: {result.ending.value}")
    print(f"年数: {result.years_played}")
    print(f"状态哈希: {result.state_hash}")
    print(result.ending_summary)
    print("\n最终状态：")
    print(json.dumps(result.final_state, ensure_ascii=False, indent=2))
    print("\n历史事件：")
    for event in result.history:
        print(f"[{event.id}] {event.summary}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已写入: {args.json}")


if __name__ == "__main__":
    main()
