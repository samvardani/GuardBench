"""Background worker placeholder for scheduled safety tasks."""

from __future__ import annotations

import time

from src.utils.notify import NotificationManager
from src.utils.io_utils import load_config


def main() -> None:
    cfg = load_config()
    notifier = NotificationManager(cfg.get("notifications"))
    notifier.notify(
        subject="Worker startup",
        message="Background worker bootstrapped and awaiting tasks.",
        metadata={},
    )
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
