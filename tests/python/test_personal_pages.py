"""dice.html / calendar.html: logic in personal-apps.js, run under real node."""
import json
import re
import subprocess

from conftest import REPO

LIB = REPO / "personal-apps.js"


def js(expr):
    """Evaluate `expr` with the library bound to PA; return parsed JSON."""
    code = f"const PA = require({json.dumps(str(LIB))});\nprocess.stdout.write(JSON.stringify({expr}));"
    out = subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_extract_keeps_only_official_dice_links():
    text = ("Free dice! https://mply.io/AbC123. also https://www.mply.io/xyz?x=1 "
            "dup https://mply.io/AbC123 fake https://mply.io.evil.com/abc "
            "https://monopolygo-free.example/mply.io/abc bare https://mply.io/ "
            "javascript:alert(1)")
    assert js(f"PA.extractDiceLinks({json.dumps(text)})") == [
        "https://mply.io/AbC123", "https://mply.io/xyz?x=1"]


def test_merge_keeps_claimed_state_and_sorts_newest_first():
    existing = [{"url": "https://mply.io/a", "added_at": "2026-10-01T00:00:00Z",
                 "claimed_at": "2026-10-01T01:00:00Z"}]
    r = js(f"PA.mergeLinks({json.dumps(existing)}, "
           f"['https://mply.io/a', 'https://mply.io/b'], '2026-10-02T00:00:00Z')")
    assert r["added"] == 1
    assert [l["url"] for l in r["links"]] == ["https://mply.io/b", "https://mply.io/a"]
    assert r["links"][1]["claimed_at"] == "2026-10-01T01:00:00Z"


def test_partition_uses_owner_cutoff():
    links = [
        {"url": "u1", "added_at": "2026-10-24T00:00:00.000Z", "claimed_at": None},
        {"url": "u2", "added_at": "2026-10-10T00:00:00.000Z", "claimed_at": None},
        {"url": "u3", "added_at": "2026-10-24T00:00:00.000Z", "claimed_at": "2026-10-24T01:00:00Z"},
    ]
    p = js(f"PA.partitionLinks({json.dumps(links)}, '2026-10-25T00:00:00.000Z', 3)")
    assert [l["url"] for l in p["open"]] == ["u1"]
    assert [l["url"] for l in p["old"]] == ["u2"]
    assert [l["url"] for l in p["claimed"]] == ["u3"]


def test_safe_url_blocks_script_and_http():
    got = js("['javascript:alert(1)', 'data:text/html,x', 'http://calendly.com/x', "
             "' https://calendly.com/me ', 'not a url'].map(PA.safeHttpsUrl)")
    assert got == [None, None, None, "https://calendly.com/me", None]


def test_calendar_embed_url_is_encoded():
    url = js("PA.buildCalendarEmbedUrl('me+x@gmail.com', 'America/Chicago', 'month')")
    assert url.startswith("https://calendar.google.com/calendar/embed?")
    assert "src=me%2Bx%40gmail.com" in url and "mode=MONTH" in url
    assert "ctz=America%2FChicago" in url
    assert js("[PA.buildCalendarEmbedUrl('', 'UTC'), PA.buildCalendarEmbedUrl('a b', 'UTC')]") == [None, None]


def test_pages_load_no_external_script_and_publish_no_address():
    for page in ("dice.html", "calendar.html"):
        text = (REPO / page).read_text()
        srcs = re.findall(r'<script[^>]*\bsrc="([^"]+)"', text)
        assert srcs == ["personal-apps.js"], page
        # The calendar ID is entered at runtime; a real address committed
        # here would publish it on a public site.
        emails = set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text)) - {"you@gmail.com"}
        assert emails == set(), page
        assert "localStorage" in text and "catch (e)" in text, page
