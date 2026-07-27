"""Tests for the resume asset validator.

Every test runs against a temp copy of the *real* committed assets, so the
suite tracks the actual rules file rather than a fixture that can drift from
it. Test one asserts the shipped assets pass; the rest corrupt one field at a
time and assert the validator rejects them.
"""

import json
import shutil
from pathlib import Path

import pytest

from conftest import load

REPO = Path(__file__).resolve().parents[2]
RULES = "assets/resume-rules.json"
TEMPLATE = "assets/resume-template.json"


@pytest.fixture
def assets(tmp_path, monkeypatch):
    """Chdir into a temp copy of the committed resume assets."""
    (tmp_path / "assets").mkdir()
    for name in ("resume-rules.json", "resume-template.json"):
        shutil.copy(REPO / "assets" / name, tmp_path / "assets" / name)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, payload):
    Path(path).write_text(json.dumps(payload), encoding="utf-8")


def run():
    """Run the validator, returning its exit code instead of raising."""
    module = load("validate_resume_assets")
    try:
        return module.main()
    except SystemExit as exc:
        return exc.code


def mutate_rules(fn):
    rules = read(RULES)
    fn(rules)
    write(RULES, rules)


def mutate_template(fn):
    template = read(TEMPLATE)
    fn(template)
    write(TEMPLATE, template)


def test_accepts_committed_assets(assets):
    assert run() == 0


def test_rejects_missing_rules_file(assets):
    Path(RULES).unlink()
    assert run() == 1


def test_rejects_unparseable_json(assets):
    Path(RULES).write_text("{not json", encoding="utf-8")
    assert run() == 1


def test_rejects_missing_top_level_key(assets):
    mutate_rules(lambda r: r.pop("taxonomy"))
    assert run() == 1


# ── Taxonomy ────────────────────────────────────────────────────────────────

def test_rejects_duplicate_taxonomy_id(assets):
    def dupe(r):
        r["taxonomy"][1]["id"] = r["taxonomy"][0]["id"]
    mutate_rules(dupe)
    assert run() == 1


def test_rejects_term_claimed_by_two_groups(assets):
    def dupe(r):
        r["taxonomy"][1]["terms"].append(r["taxonomy"][0]["terms"][0])
    mutate_rules(dupe)
    assert run() == 1


def test_rejects_term_that_is_a_stopword(assets):
    def stopword_term(r):
        r["taxonomy"][0]["terms"].append(r["stopwords"][0])
    mutate_rules(stopword_term)
    assert run() == 1


def test_rejects_uppercase_term(assets):
    def shout(r):
        r["taxonomy"][0]["terms"].append("Windows Server 2022")
    mutate_rules(shout)
    assert run() == 1


def test_rejects_term_with_stray_whitespace(assets):
    def padded(r):
        r["taxonomy"][0]["terms"].append(" trailing space ")
    mutate_rules(padded)
    assert run() == 1


def test_rejects_empty_taxonomy(assets):
    mutate_rules(lambda r: r.__setitem__("taxonomy", []))
    assert run() == 1


# ── Date formats ────────────────────────────────────────────────────────────

def test_rejects_invalid_regex(assets):
    def broken(r):
        r["date_formats"][0]["pattern"] = "^[unclosed"
    mutate_rules(broken)
    assert run() == 1


def test_rejects_format_that_fails_its_own_example(assets):
    def mismatch(r):
        r["date_formats"][0]["example"] = "not a date"
    mutate_rules(mismatch)
    assert run() == 1


# ── Lint thresholds ─────────────────────────────────────────────────────────

def test_rejects_ratio_above_one(assets):
    def bad_ratio(r):
        r["lint"]["min_quantified_ratio"] = 1.5
    mutate_rules(bad_ratio)
    assert run() == 1


def test_rejects_inverted_min_max(assets):
    def inverted(r):
        r["lint"]["min_skills"] = r["lint"]["max_skills"] + 1
    mutate_rules(inverted)
    assert run() == 1


def test_rejects_non_numeric_threshold(assets):
    def not_a_number(r):
        r["lint"]["max_bullet_chars"] = "240"
    mutate_rules(not_a_number)
    assert run() == 1


# ── Sections and glyphs ─────────────────────────────────────────────────────

def test_rejects_synonym_for_unknown_section(assets):
    def orphan(r):
        r["sections"]["synonyms"]["Hobbies"] = ["pastimes"]
    mutate_rules(orphan)
    assert run() == 1


def test_rejects_multi_character_glyph(assets):
    def wide(r):
        r["banned_glyphs"][0]["char"] = "ab"
    mutate_rules(wide)
    assert run() == 1


def test_rejects_glyph_replacing_itself(assets):
    def circular(r):
        r["banned_glyphs"][0]["replacement"] = r["banned_glyphs"][0]["char"]
    mutate_rules(circular)
    assert run() == 1


# ── Template shape ──────────────────────────────────────────────────────────

def test_rejects_template_missing_contact_field(assets):
    mutate_template(lambda t: t["contact"].pop("email"))
    assert run() == 1


def test_rejects_template_date_in_unknown_format(assets):
    def odd_date(t):
        t["experience"][0]["start"] = "sometime in 2019"
    mutate_template(odd_date)
    assert run() == 1


def test_rejects_template_role_without_bullets(assets):
    def empty(t):
        t["experience"][0]["bullets"] = []
    mutate_template(empty)
    assert run() == 1


# ── Privacy guard: the repository is public ─────────────────────────────────

def test_rejects_real_email_in_template(assets):
    def leak(t):
        t["contact"]["email"] = "christian.parker@gmail.com"
    mutate_template(leak)
    assert run() == 1


def test_rejects_real_phone_in_template(assets):
    def leak(t):
        t["contact"]["phone"] = "(251) 401-1413"
    mutate_template(leak)
    assert run() == 1


def test_rejects_pii_buried_in_a_nested_bullet(assets):
    def leak(t):
        t["experience"][0]["bullets"].append(
            "Reach me any time at 251-555-0142 to discuss the role.")
    mutate_template(leak)
    assert run() == 1


def test_accepts_placeholder_contact_details(assets):
    def placeholders(t):
        t["contact"]["email"] = "you@example.com"
        t["contact"]["phone"] = "(000) 000-0000"
    mutate_template(placeholders)
    assert run() == 0
