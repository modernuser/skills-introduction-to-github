#!/usr/bin/env python3
"""Post an alert to Slack via incoming webhook — inert until configured.

The webhook URL comes ONLY from the SLACK_WEBHOOK_URL environment
variable (a GitHub Actions secret; never a file). When the variable is
absent this script exits 0 silently, so the pipeline ships with Slack
support that costs nothing and does nothing until the owner adds the
secret. A Slack failure never fails the calling workflow, and the URL is
never printed.

Usage: notify_slack.py <kind> [text-file]
  kind: briefing | moves | failure
  text-file: markdown body to summarize (briefing/moves); for failure,
             the text is taken from FAILURE_CONTEXT env or a default.
"""

import json
import os
import sys
import urllib.request

MAX_LEN = 2800  # keep well under Slack's block text limit

HEADERS = {
    "briefing": ":coffee: Pre-market briefing",
    "moves": ":warning: Significant moves",
    "failure": ":rotating_light: Pipeline failure",
}


def build_payload(kind: str, body: str) -> dict:
    header = HEADERS.get(kind, "Wolf of Fairhope Avenue")
    if len(body) > MAX_LEN:
        body = body[:MAX_LEN] + "\n… (truncated — full text in the GitHub issue)"
    return {
        "blocks": [
            {"type": "header",
             "text": {"type": "plain_text", "text": header, "emoji": True}},
            {"type": "section",
             "text": {"type": "mrkdwn", "text": body or "(no details)"}},
            {"type": "context", "elements": [{
                "type": "mrkdwn",
                "text": ("Wolf of Fairhope Avenue · data display, not advice · "
                         "<https://modernuser.github.io/skills-introduction-to-github/tracker.html|tracker>")}]},
        ]
    }


def main() -> int:
    url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not url:
        print("SLACK_WEBHOOK_URL not set; Slack notification skipped")
        return 0
    if not url.startswith("https://hooks.slack.com/"):
        print("SLACK_WEBHOOK_URL does not look like a Slack webhook; skipped",
              file=sys.stderr)
        return 0

    kind = sys.argv[1] if len(sys.argv) > 1 else "failure"
    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        with open(sys.argv[2]) as f:
            body = f.read()
    else:
        body = os.environ.get("FAILURE_CONTEXT",
                              "A scheduled workflow failed — see the GitHub issue.")

    payload = build_payload(kind, body)
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        print(f"Slack notification sent ({kind})")
    except Exception as exc:
        # Never leak the URL; never fail the pipeline over a chat message.
        print(f"Slack notification failed ({type(exc).__name__}); continuing",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
