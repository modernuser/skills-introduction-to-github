from conftest import fabricated_quotes, load


HOSTILE_FREE_NEWS = {
    "NVDA": [
        {"title": "Nvidia announces $50 billion data center expansion in Texas",
         "link": "https://reuters.com/a"},
        {"title": "Nvidia to build $50 billion Texas data center campus",
         "link": "https://cnbc.com/b"},
        {"title": "Why Nvidia Stock Is Set to Soar Next Month",
         "link": "https://fool.com/c"},
    ],
    "MU": [{"title": "Micron raises quarterly guidance on memory pricing",
            "link": "https://bloomberg.com/d"}],
}


def test_corroboration_tags(workdir):
    mb = load("morning_briefing")
    md = mb.build_briefing(fabricated_quotes(),
                           {s: list(v) for s, v in HOSTILE_FREE_NEWS.items()})
    assert md.count("corroborated (2 outlets)") == 2
    assert md.count("single source — unconfirmed") == 2
    assert "not investment advice" in md
    assert "Leaders" in md and "Laggards" in md


def test_flagged_core_included_quiet_core_excluded(workdir):
    mb = load("morning_briefing")
    md = mb.build_briefing(fabricated_quotes(flagged={"AAPL"}), {})
    assert "| AAPL |" in md
    assert "| GOOGL |" not in md


def test_no_news_still_produces_briefing(workdir):
    mb = load("morning_briefing")
    md = mb.build_briefing(fabricated_quotes(), {})
    assert "Headline fetch failed" in md
    assert "Prior close" in md
