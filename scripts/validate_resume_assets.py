#!/usr/bin/env python3
"""Validate the resume builder's committed assets.

resume.html applies these rules in the browser, so a malformed rules file
degrades silently: a bad regex or a duplicated taxonomy term produces wrong
keyword-coverage numbers rather than an error the user would notice. This
validator runs in CI so the failure is loud instead.

It also enforces the privacy invariant the builder is built around: the
repository is public, so the committed template must stay a placeholder.
If a filled profile is ever pasted over it, check_template_has_no_pii()
fails the build before the data reaches a public commit.
"""

import json
import os
import re
import sys

RULES_PATH = "assets/resume-rules.json"
TEMPLATE_PATH = "assets/resume-template.json"

REQUIRED_RULE_KEYS = (
    "version", "sections", "banned_glyphs", "date_formats", "lint",
    "weak_openers", "strong_verbs", "stopwords", "taxonomy",
)
REQUIRED_LINT_KEYS = (
    "max_resume_chars", "max_summary_chars", "min_summary_chars",
    "max_bullet_chars", "min_bullet_chars", "min_bullets_per_role",
    "max_bullets_per_role", "min_quantified_ratio", "min_skills",
    "max_skills", "target_coverage",
)
RATIO_KEYS = ("min_quantified_ratio", "target_coverage")
REQUIRED_CONTACT_KEYS = ("name", "headline", "email", "phone", "location")

# A placeholder email must be unmistakably fake. RFC 2606 reserves these.
PLACEHOLDER_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Ten digits with common separators, e.g. (555) 010-0199 or 555-010-0199.
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}")


def fail(msg: str):
    print(f"VALIDATION FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


def load(path: str):
    if not os.path.exists(path):
        fail(f"{path} is missing")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")


def check_string_list(values, label, *, lowercase=True):
    if not isinstance(values, list) or not values:
        fail(f"{label} must be a non-empty list")
    seen = set()
    for item in values:
        if not isinstance(item, str) or not item.strip():
            fail(f"{label} contains an empty or non-string entry")
        if lowercase and item != item.lower():
            fail(f"{label} entry {item!r} must be lowercase")
        if item != item.strip():
            fail(f"{label} entry {item!r} has leading or trailing whitespace")
        if item in seen:
            fail(f"{label} contains duplicate entry {item!r}")
        seen.add(item)
    return seen


def check_sections(sections):
    canonical = sections.get("canonical")
    if not isinstance(canonical, list) or not canonical:
        fail("sections.canonical must be a non-empty list")
    canonical_set = set(canonical)
    if len(canonical_set) != len(canonical):
        fail("sections.canonical contains duplicates")
    synonyms = sections.get("synonyms", {})
    if not isinstance(synonyms, dict):
        fail("sections.synonyms must be an object")
    for name, alts in synonyms.items():
        if name not in canonical_set:
            fail(f"sections.synonyms key {name!r} is not a canonical section")
        check_string_list(alts, f"sections.synonyms[{name}]")


def check_banned_glyphs(glyphs):
    if not isinstance(glyphs, list) or not glyphs:
        fail("banned_glyphs must be a non-empty list")
    seen = set()
    for entry in glyphs:
        for key in ("char", "name", "replacement", "reason"):
            if key not in entry:
                fail(f"banned_glyphs entry missing {key!r}")
        char = entry["char"]
        if not isinstance(char, str) or len(char) != 1:
            fail(f"banned_glyphs char {char!r} must be exactly one character")
        if char in seen:
            fail(f"banned_glyphs lists {char!r} twice")
        if char == entry["replacement"]:
            fail(f"banned_glyphs {char!r} replaces itself")
        seen.add(char)


def check_date_formats(formats):
    if not isinstance(formats, list) or not formats:
        fail("date_formats must be a non-empty list")
    for entry in formats:
        for key in ("name", "pattern", "example"):
            if key not in entry:
                fail(f"date_formats entry missing {key!r}")
        try:
            pattern = re.compile(entry["pattern"])
        except re.error as exc:
            fail(f"date_formats {entry['name']!r} has an invalid regex: {exc}")
        # Self-check: a format whose own example fails its pattern is a bug
        # that would silently reject every real date the user types.
        if not pattern.match(entry["example"]):
            fail(f"date_formats {entry['name']!r} does not match its own "
                 f"example {entry['example']!r}")


def check_lint(lint):
    if not isinstance(lint, dict):
        fail("lint must be an object")
    for key in REQUIRED_LINT_KEYS:
        if key not in lint:
            fail(f"lint is missing {key!r}")
        if not isinstance(lint[key], (int, float)) or isinstance(lint[key], bool):
            fail(f"lint.{key} must be a number")
        if lint[key] < 0:
            fail(f"lint.{key} must not be negative")
    for key in RATIO_KEYS:
        if not 0 < lint[key] <= 1:
            fail(f"lint.{key} must be a ratio between 0 and 1")
    pairs = (
        ("min_summary_chars", "max_summary_chars"),
        ("min_bullet_chars", "max_bullet_chars"),
        ("min_bullets_per_role", "max_bullets_per_role"),
        ("min_skills", "max_skills"),
    )
    for low, high in pairs:
        if lint[low] >= lint[high]:
            fail(f"lint.{low} must be less than lint.{high}")


def check_taxonomy(taxonomy, stopwords):
    if not isinstance(taxonomy, list) or not taxonomy:
        fail("taxonomy must be a non-empty list")
    ids, terms = set(), {}
    for entry in taxonomy:
        for key in ("id", "label", "category", "terms"):
            if key not in entry:
                fail(f"taxonomy entry missing {key!r}")
        entry_id = entry["id"]
        if entry_id in ids:
            fail(f"taxonomy has duplicate id {entry_id!r}")
        ids.add(entry_id)
        for term in check_string_list(entry["terms"], f"taxonomy[{entry_id}].terms"):
            # A term claimed by two groups makes coverage scoring ambiguous:
            # the same JD word would credit two different skills.
            if term in terms:
                fail(f"taxonomy term {term!r} appears in both "
                     f"{terms[term]!r} and {entry_id!r}")
            # A term that is also a stopword is stripped before matching and
            # could never score, so it is dead weight that looks like coverage.
            if term in stopwords:
                fail(f"taxonomy term {term!r} in {entry_id!r} is a stopword "
                     "and would never match")
            terms[term] = entry_id
    return terms


def check_template(template, rules):
    for key in ("schema_version", "contact", "summary", "skills", "experience"):
        if key not in template:
            fail(f"{TEMPLATE_PATH} is missing {key!r}")
    contact = template["contact"]
    for key in REQUIRED_CONTACT_KEYS:
        if key not in contact:
            fail(f"template contact is missing {key!r}")
    if not isinstance(template["experience"], list) or not template["experience"]:
        fail("template experience must be a non-empty list")

    patterns = [re.compile(d["pattern"]) for d in rules["date_formats"]]
    for role in template["experience"]:
        for key in ("title", "organization", "start", "end", "bullets"):
            if key not in role:
                fail(f"template experience entry missing {key!r}")
        for key in ("start", "end"):
            value = role[key]
            if not any(p.match(value) for p in patterns):
                fail(f"template experience {key} {value!r} matches no "
                     "configured date format")
        if not role["bullets"]:
            fail("template experience entry has no bullets")


def walk_strings(node, path="$"):
    """Yield every (json_path, string) pair in the document."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_strings(value, f"{path}[{index}]")
    elif isinstance(node, str):
        yield path, node


def check_template_has_no_pii(template):
    """The repository is public; the committed template must stay a stub.

    This is the backstop for the builder's core promise. If a filled profile
    is ever written over the template, CI fails here rather than publishing
    a real name, phone number, and address to a public commit.
    """
    for path, value in walk_strings(template):
        for email in EMAIL_RE.findall(value):
            domain = email.rsplit("@", 1)[1].lower()
            if domain not in PLACEHOLDER_EMAIL_DOMAINS:
                fail(f"{path} contains a real-looking email address "
                     f"({email}); the committed template must use an "
                     "example.com placeholder")
        for phone in PHONE_RE.findall(value):
            if set(re.sub(r"\D", "", phone)) != {"0"}:
                fail(f"{path} contains a real-looking phone number "
                     f"({phone}); the committed template must use "
                     "(000) 000-0000")


def main() -> int:
    rules = load(RULES_PATH)
    template = load(TEMPLATE_PATH)

    for key in REQUIRED_RULE_KEYS:
        if key not in rules:
            fail(f"{RULES_PATH} is missing {key!r}")

    check_sections(rules["sections"])
    check_banned_glyphs(rules["banned_glyphs"])
    check_date_formats(rules["date_formats"])
    check_lint(rules["lint"])
    check_string_list(rules["weak_openers"], "weak_openers")
    check_string_list(rules["strong_verbs"], "strong_verbs")
    stopwords = check_string_list(rules["stopwords"], "stopwords")
    terms = check_taxonomy(rules["taxonomy"], stopwords)

    check_template(template, rules)
    check_template_has_no_pii(template)

    print(f"resume assets OK: {len(rules['taxonomy'])} skill groups, "
          f"{len(terms)} keywords, {len(rules['banned_glyphs'])} glyph rules, "
          f"template clean of personal data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
