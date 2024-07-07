import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
import yaml
from bs4 import BeautifulSoup


WATCHLIST_PATH = "watchlist.yml"
STATE_PATH = "state.json"

USER_AGENT = "CourseWatch/1.0 (GitHub Actions; respectful polling)"
REQUEST_TIMEOUT = 20
DELAY_BETWEEN_REQUESTS_SEC = 2  # polite delay


@dataclass
class WatchResult:
    value: Optional[int]
    available: Optional[bool]
    error: Optional[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f) or {}
        except json.JSONDecodeError:
            return {}


def save_state(path: str, state: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def fetch_html(url: str) -> str:
    r = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.text


def extract_keyword_number(html: str, keyword: str) -> Optional[int]:
    """
    MVP extractor:
    - Converts HTML -> visible text
    - Finds a number near the keyword like:
        'Availability no: 1'
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)

    kw = re.escape(keyword)
    patterns = [
        rf"{kw}\s*[:#]?\s*([0-9]+)",
        rf"Availability\s*no\s*[:#]?\s*([0-9]+)",
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))

    for line in text.splitlines():
        if keyword.lower() in line.lower():
            m = re.search(r"([0-9]+)", line)
            if m:
                return int(m.group(1))

    return None


def eval_condition(value: int, op: str, rhs: int) -> bool:
    if op == ">":
        return value > rhs
    if op == ">=":
        return value >= rhs
    if op == "==":
        return value == rhs
    if op == "!=":
        return value != rhs
    if op == "<":
        return value < rhs
    if op == "<=":
        return value <= rhs
    raise ValueError(f"Unsupported op: {op}")


def get_watch_result(watch: Dict[str, Any]) -> WatchResult:
    try:
        html = fetch_html(watch["url"])
        extract = watch.get("extract", {})
        if extract.get("type") == "keyword_number":
            keyword = extract.get("keyword", "Availability no")
            value = extract_keyword_number(html, keyword)
        else:
            return WatchResult(None, None, f"Unsupported extract type: {extract.get('type')}")

        if value is None:
            return WatchResult(None, None, "Could not extract availability number")

        cond = watch.get("condition", {"op": ">", "value": 0})
        available = eval_condition(value, cond["op"], int(cond["value"]))
        return WatchResult(value=value, available=available, error=None)

    except requests.RequestException as e:
        return WatchResult(None, None, f"Request error: {e}")
    except Exception as e:
        return WatchResult(None, None, f"Unexpected error: {e}")


def github_api_headers() -> Dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN env var (provided automatically in Actions).")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }


def find_issue_by_title(repo: str, title: str) -> Optional[int]:
    url = f"https://api.github.com/repos/{repo}/issues"
    r = requests.get(
        url,
        headers=github_api_headers(),
        params={"state": "all", "per_page": 100},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    issues = r.json()
    for it in issues:
        if it.get("title") == title:
            return int(it.get("number"))
    return None


def create_or_comment_issue(repo: str, title: str, body: str) -> None:
    issue_num = find_issue_by_title(repo, title)
    if issue_num is None:
        url = f"https://api.github.com/repos/{repo}/issues"
        r = requests.post(
            url,
            headers=github_api_headers(),
            json={"title": title, "body": body},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
    else:
        url = f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments"
        r = requests.post(
            url,
            headers=github_api_headers(),
            json={"body": body},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()


def main() -> int:
    watchlist = load_yaml(WATCHLIST_PATH)
    watches = watchlist.get("watches", [])
    if not isinstance(watches, list) or not watches:
        print("No watches found in watchlist.yml")
        return 0

    state = load_state(STATE_PATH)

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        print("Warning: GITHUB_REPOSITORY not set (local run). Issues won't be created.")

    state_changed = False
    watchlist_changed = False

    for w in watches:
        if not w.get("enabled", True):
            continue

        wid = w.get("id")
        label = w.get("label", wid or "Unnamed watch")
        url = w.get("url")

        if not wid or not url:
            print(f"Skipping invalid watch (missing id/url): {w}")
            continue

        print(f"\nChecking: {label}\nURL: {url}")
        res = get_watch_result(w)

        prev = state.get(wid, {})
        prev_available = prev.get("available", None)
        prev_value = prev.get("value", None)

        state.setdefault(wid, {})
        state[wid]["last_checked_utc"] = utc_now_iso()
        state[wid]["label"] = label
        state[wid]["url"] = url

        if res.error:
            print(f"  ERROR: {res.error}")
            state[wid]["error"] = res.error
            state_changed = True
            time.sleep(DELAY_BETWEEN_REQUESTS_SEC)
            continue

        print(f"  Extracted availability number: {res.value} | available_now={res.available}")
        state[wid]["value"] = res.value
        state[wid]["available"] = res.available
        state[wid].pop("error", None)
        state_changed = True

        triggered = (prev_available is False or prev_available is None) and (res.available is True)

        if triggered:
            title = f"Seat available: {label}"
            body = (
                f"✅ **Seat appears available** for:\n\n"
                f"- **Watch:** {label}\n"
                f"- **URL:** {url}\n"
                f"- **Availability no:** {res.value}\n"
                f"- **Checked (UTC):** {state[wid]['last_checked_utc']}\n\n"
                f"Mode: `{w.get('mode','once')}`\n\n"
                f"Note: This tool reads publicly available information only and does not automate enrolment."
            )

            if repo:
                create_or_comment_issue(repo, title, body)
                print("  NOTIFIED via GitHub Issue.")
            else:
                print("  (Local run) Would notify via GitHub Issue:", title)

            mode = (w.get("mode") or "once").lower()
            if mode == "once":
                w["enabled"] = False
                watchlist_changed = True
                print("  Auto-disabled this watch (mode=once).")
        else:
            if prev_value is not None and prev_value != res.value:
                print(f"  Value changed: {prev_value} -> {res.value}")
            else:
                print("  No trigger (no Full->Available transition).")

        time.sleep(DELAY_BETWEEN_REQUESTS_SEC)

    if watchlist_changed:
        save_yaml(WATCHLIST_PATH, watchlist)
    if state_changed:
        save_state(STATE_PATH, state)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
