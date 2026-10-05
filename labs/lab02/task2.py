import argparse
import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)

LOG_PATTERN = re.compile(
    r"^(?P<month>[A-Z][a-z]{2})\s+"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2}).*?"
    r"(?P<status>Failed|Accepted) password for "
    r"(?:(?:invalid user)\s+)?"
    r"(?P<user>\S+)\s+from\s+"
    r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3})"
)


def parse_line(line: str) -> dict | None:
    """Розбирає рядок auth.log."""
    match = LOG_PATTERN.search(line)

    if not match:
        return None

    data = match.groupdict()
    year = datetime.now(timezone.utc).year

    timestamp = datetime.strptime(
        f"{year} {data['month']} {data['day']} {data['time']}",
        "%Y %b %d %H:%M:%S",
    ).replace(tzinfo=timezone.utc)

    return {
        "timestamp": timestamp,
        "status": data["status"],
        "user": data["user"],
        "ip": data["ip"],
    }


def read_auth_log(path: Path) -> tuple[list[dict], int]:
    """Читає auth.log."""
    events = []
    total_lines = 0

    try:
        with path.open(encoding="utf-8") as file:
            for line in file:
                total_lines += 1
                event = parse_line(line)

                if event:
                    events.append(event)
    except OSError as exc:
        raise OSError(f"Cannot read log file: {path}") from exc

    events.sort(key=lambda event: event["timestamp"])
    return events, total_lines


def detect_bruteforce(
    events: list[dict],
    threshold: int,
    window_min: int,
) -> list[dict]:
    """Знаходить IP з понад threshold невдалими входами за window_min."""
    failed = defaultdict(list)

    for event in events:
        if event["status"] == "Failed":
            failed[event["ip"]].append(event)

    window = timedelta(minutes=window_min)
    alerts = []

    for ip, attempts in failed.items():
        left = 0

        for right in range(len(attempts)):
            while attempts[right]["timestamp"] - attempts[left]["timestamp"] > window:
                left += 1

            count = right - left + 1

            if count > threshold:
                window_events = attempts[left : right + 1]

                alerts.append(
                    {
                        "ip": ip,
                        "total_failures": len(attempts),
                        "attempts_in_window": count,
                        "target_users": sorted(
                            {event["user"] for event in window_events}
                        ),
                        "first_attempt": window_events[0]["timestamp"].isoformat(),
                        "last_attempt": window_events[-1]["timestamp"].isoformat(),
                    }
                )
                break

    return sorted(
        alerts,
        key=lambda alert: alert["total_failures"],
        reverse=True,
    )


def build_report(
    events: list[dict],
    alerts: list[dict],
    threshold: int,
    window_min: int,
) -> dict:
    """Формує JSON-звіт."""
    failed = [event for event in events if event["status"] == "Failed"]
    accepted = [event for event in events if event["status"] == "Accepted"]

    return {
        "analysis": {
            "total_events": len(events),
            "failed_attempts": len(failed),
            "accepted_attempts": len(accepted),
            "threshold": threshold,
            "window_minutes": window_min,
            "time_range": {
                "from": (events[0]["timestamp"].isoformat() if events else None),
                "to": (events[-1]["timestamp"].isoformat() if events else None),
            },
        },
        "bruteforce_alerts": alerts,
        "blocklist": [alert["ip"] for alert in alerts],
    }


def save_json(report: dict, path: Path) -> None:
    """Зберігає звіт у JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
        )


def configure_logging() -> None:
    """Налаштовує logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )


def analyze(
    auth_log: Path,
    threshold: int = 5,
    window_min: int = 5,
    output_json: Path = Path("labs/lab02/data/blocklist_ips.json"),
) -> None:
    """Аналізує auth.log та виявляє brute-force."""
    configure_logging()

    LOGGER.info(
        "Analyzing authentication events in %s...",
        auth_log,
    )

    events, total_lines = read_auth_log(auth_log)

    LOGGER.info(
        "Processed %d lines, parsed %d authentication events.",
        total_lines,
        len(events),
    )

    alerts = detect_bruteforce(
        events,
        threshold,
        window_min,
    )

    for alert in alerts:
        LOGGER.error(
            "Bruteforce detected from %s: %d failed attempts.",
            alert["ip"],
            alert["total_failures"],
        )

    report = build_report(
        events,
        alerts,
        threshold,
        window_min,
    )

    save_json(report, output_json)

    print("\n=== SSH Bruteforce Detection Results ===")
    print(f"Failed Attempts Threshold: >{threshold} attempts in {window_min} minutes")
    print(f"Total Authentication Events: {len(events)}")
    print(
        "Failed Attempts:",
        sum(event["status"] == "Failed" for event in events),
    )
    print(
        "Accepted Attempts:",
        sum(event["status"] == "Accepted" for event in events),
    )

    print("\n=== Detected Bruteforce Attacks ===")

    if not alerts:
        print("No brute-force attacks detected.")
    else:
        for alert in alerts:
            print(
                f"[ALERT] Bruteforce Detected! "
                f"IP: {alert['ip']} | "
                f"Total Failures: {alert['total_failures']} | "
                f"Attempts in Window: {alert['attempts_in_window']} | "
                f"Target Users: {', '.join(alert['target_users'])}"
            )

        print("\n=== Recommended Blocklist (IPs) ===")

        for alert in alerts:
            print(alert["ip"])

    LOGGER.info(
        "Exported analysis report to %s",
        output_json,
    )


def main() -> None:
    """CLI точка входу."""
    parser = argparse.ArgumentParser(description="SSH authentication log analyzer")

    parser.add_argument(
        "--auth-log",
        type=Path,
        required=True,
        help="Path to auth.log",
    )

    parser.add_argument(
        "--threshold",
        type=int,
        default=5,
        help="Brute-force threshold",
    )

    parser.add_argument(
        "--window-min",
        type=int,
        default=5,
        help="Time window in minutes",
    )

    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("labs/lab02/data/blocklist_ips.json"),
        help="Path to JSON report",
    )

    args = parser.parse_args()

    if args.threshold <= 0:
        parser.error("--threshold must be greater than 0")

    if args.window_min <= 0:
        parser.error("--window-min must be greater than 0")

    try:
        analyze(
            args.auth_log,
            args.threshold,
            args.window_min,
            args.output_json,
        )
    except OSError as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
