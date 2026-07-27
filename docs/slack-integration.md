# Slack integration

## What posts to Slack, and what never does

| Posts | Never posts |
|---|---|
| Weekday pre-market briefing | Routine data commits |
| Significant-move alerts (±3% day, first detection per ticker) | Successful runs, deploys |
| Pipeline / daily-ops failures | Anything predictive — same product rules as everywhere else |

Slack is an interrupt channel; only things worth interrupting for go
there. Everything mirrored to Slack also exists as a GitHub issue, so
Slack being down loses nothing.

## Enable it (one-time, ~5 minutes)

1. In Slack: create an app → enable **Incoming Webhooks** → add a webhook
   for the channel you want (api.slack.com/apps).
2. In GitHub: repo → Settings → Secrets and variables → Actions →
   **New repository secret** → name `SLACK_WEBHOOK_URL`, value = the
   webhook URL.
3. Done. The next briefing/alert/failure posts automatically. Without the
   secret, `scripts/notify_slack.py` exits silently — the integration
   ships inert and costs nothing.

**Zero-code alternative:** if the GitHub Slack app is installed in the
workspace, `/github subscribe modernuser/skills-introduction-to-github issues`
in any channel delivers every briefing and alert (they are all issues)
with no code path at all. Both can coexist; the webhook version is
formatted nicer.

## Security rules

- The webhook URL is a **credential**: anyone holding it can post to the
  channel. It lives only in the Actions secret — never in a file (GitHub
  push protection actively blocks webhook-shaped strings in this repo;
  verified live). If it ever leaks, regenerate it in Slack immediately.
- `notify_slack.py` refuses non-`hooks.slack.com` URLs, never prints the
  URL, truncates bodies, and never fails the pipeline over a chat error.
- Inbound Slack content is untrusted input. Nothing in this project reads
  from Slack today; if that ever changes, messages must be treated like
  RSS titles — escaped, validated, and never executed.

## Using Slack with AI — durable vs. session-scoped (read before building)

This project has learned the hard way (twice) that anything scheduled
inside an assistant session **dies with the session**. Apply that lesson
to Slack+AI plans:

**Durable (safe to build on):**
- GitHub Actions → webhook (what this repo does): survives everything,
  runs on GitHub's clock, costs nothing.
- A Slack app with a bot token stored as an Actions secret: lets a
  *workflow* post richer messages, read reactions, or open threads —
  still scheduled by GitHub, still session-independent.
- Slack Workflow Builder / native Slack automations: live inside Slack.

**Session-scoped (fine for one-off tasks, wrong for automation):**
- Zapier MCP actions invoked by an assistant: they execute only while
  that assistant session is alive. Good for "post this once for me now";
  wrong for "post the briefing every morning."
- An assistant session itself watching Slack: same failure mode.

**Future upgrade path, in order of ambition:**
1. Today: webhook mirror (this PR) — one-way, formatted, free.
2. Bot token in Actions: threaded briefings, reaction-based acks — still
   deterministic, no AI cost.
3. AI-in-the-loop (e.g. Haiku summarizing the briefing into two Slack
   sentences, or answering "@bot what moved today?" from committed data):
   requires the AI-maintenance prerequisites (`ANTHROPIC_API_KEY` secret,
   budget approved in `.claude/model-policy.yml`) AND a Slack app with
   verified request signatures. Treat inbound prompts as untrusted; the
   bot answers only from committed `data/*.json`, never executes
   instructions found in messages, and never gives advice — the same
   hard rule as the site.

Anything at level 3 is a high-risk change per the change policy: human
approval, test evidence, and a security review before it ships.
