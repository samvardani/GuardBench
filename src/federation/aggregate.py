from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

from .signatures import Signature, merge_signatures


def _load_feed(path: Path) -> List[Signature]:
    if not path.exists():
        return []
    out: List[Signature] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        out.append(
            Signature(
                tenant=obj["tenant"],
                algo=obj["algo"],
                perms=list(obj["perms"]),
                bloom=list(obj["bloom"]),
                meta=dict(obj.get("meta", {})),
            )
        )
    return out


def _dump_feed(sigs: Iterable[Signature], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for sig in sigs:
            handle.write(
                json.dumps(
                    {
                        "tenant": sig.tenant,
                        "algo": sig.algo,
                        "perms": sig.perms,
                        "bloom": sig.bloom,
                        "meta": sig.meta,
                    },
                    separators=(",", ":"),
                )
            )
            handle.write("\n")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Aggregate federation signature feeds")
    p.add_argument("--inputs", nargs="+", help="Input feed JSONL files")
    p.add_argument("--output", required=True, help="Output merged JSONL feed")
    args = p.parse_args(argv)

    feeds = [_load_feed(Path(x)) for x in args.inputs]
    merged = merge_signatures(feeds)
    _dump_feed(merged, Path(args.output))
    print(f"Wrote merged feed with {len(merged)} signatures to {args.output}")


if __name__ == "__main__":
    main()


