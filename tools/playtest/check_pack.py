#!/usr/bin/env python3
"""Device Playtest Pack coverage (T1): docs/PLAYTEST_PACK.md must cover every runtime test the plan still owes.

Usage: python3 tools/playtest/check_pack.py [repo]            check the real plan and pack
       python3 tools/playtest/check_pack.py [repo] --self-test also prove the checks fail on broken copies
                                                              (made in memory; no file is written)

The plan (docs/WRIKSHAGANDHA_MASTER_PRODUCTION_PLAN.md) is authoritative. A milestone is *owed a runtime test* when
the plan marks it `[~]` (implemented, needs runtime testing) in its table row or on its bold heading, when it is the
open playtest gate (`[ ]` with "PLAYTEST REQUIRED", i.e. M01.6), or when it is an organic-world stage marked `[~]`
("**Stage B0 — …** `[~]`"). Milestone ids are Mpp.n (with an optional letter), E<n>, W<n> and the stages B<n>[.<n>].

The pack's ```playtest-coverage block lists one milestone per line followed by the tests that cover it
(S<n> or S<n>.<m>, separated by spaces or commas). Checked:
  1. every milestone the plan owes a runtime test is listed;
  2. every listed milestone exists in the plan (any status);
  3. every line names at least one test, and every named test exists in the pack — a session heading (S<n> at the
     start of a Markdown heading) or a test heading (S<n>.<m> at the start of a Markdown heading or a bold line);
     no milestone is listed twice.
Only those structures are read — wording and other Markdown formatting are free to change.

This is documentation coverage only: it never marks a milestone verified (only the developer's reported device
results do, plan §7). Limitation: a status is read only in the plan's own convention — the backticked markers of plan
§6 (`[~]`, `[ ]`, `[x]`, `[!]`) on a milestone's table row or heading line; a marker written another way is not seen.
"""
import os, re, sys

ID = r"(?:M\d{2}\.\d+[a-z]?|E\d+|W\d+)"
PLAN = os.path.join("docs", "WRIKSHAGANDHA_MASTER_PRODUCTION_PLAN.md")
PACK = os.path.join("docs", "PLAYTEST_PACK.md")

def plan_ids(text):
    """(every milestone id the plan defines, the ids it still owes a runtime test)."""
    defined, owed = set(), set()
    for m in re.finditer(r"^\|\s*(%s)\s*\|(.*)$" % ID, text, re.M):         # table rows
        defined.add(m.group(1))
        if "`[~]`" in m.group(2):
            owed.add(m.group(1))
    for m in re.finditer(r"^(?:#{1,6}\s+|\*\*)(%s)\b[^\n]*$" % ID, text, re.M):  # milestone headings (bold or #)
        defined.add(m.group(1))
        line = m.group(0)
        if "`[~]`" in line or ("`[ ]`" in line and "PLAYTEST REQUIRED" in line):
            owed.add(m.group(1))
    for m in re.finditer(r"^(?:#{1,6}\s+|\*\*)Stage (B\d+(?:\.\d+)?)\b[^\n]*$", text, re.M):  # organic-world stages
        defined.add(m.group(1))
        if "`[~]`" in m.group(0):
            owed.add(m.group(1))
    return defined, owed

def pack_coverage(text):
    """(coverage lines [(line, milestone, [tests])], the test labels the pack defines, problems found while reading)."""
    problems = []
    blocks = re.findall(r"^```playtest-coverage\n(.*?)^```", text, re.M | re.S)
    if len(blocks) != 1:
        return [], set(), [f"{PACK}: expected exactly one ```playtest-coverage block, found {len(blocks)}"]
    coverage, seen = [], set()
    for n, line in enumerate(blocks[0].splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        mid, *tests = [w for w in re.split(r"[\s,]+", line) if w]
        if mid in seen:
            problems.append(f"{PACK}: coverage line {n}: {mid} is listed twice")
        if not tests:
            problems.append(f"{PACK}: coverage line {n}: {mid} names no test")
        seen.add(mid)
        coverage.append((n, mid, tests))
    labels = set(re.findall(r"^#{1,6}\s+(S\d+)(?![.\d])", text, re.M)) \
        | set(re.findall(r"^(?:#{1,6}\s+|\*\*)(S\d+\.\d+)(?!\d)", text, re.M))
    return coverage, labels, problems

def check(plan_text, pack_text):
    """Every problem found, as messages (empty = the pack covers the plan)."""
    defined, owed = plan_ids(plan_text)
    coverage, labels, problems = pack_coverage(pack_text)
    listed = {mid for _, mid, _ in coverage}
    if not owed:
        problems.append(f"{PLAN}: no milestone owes a runtime test — the plan's status markers could not be read")
    for mid in sorted(owed - listed):
        problems.append(f"{PACK}: {mid} is marked as needing a runtime test in the plan but is missing from the coverage index")
    for mid in sorted(listed - defined):
        problems.append(f"{PACK}: {mid} is in the coverage index but the plan has no such milestone")
    for _, mid, tests in coverage:
        for t in tests:
            if not re.fullmatch(r"S\d+(?:\.\d+)?", t):
                problems.append(f"{PACK}: {mid}: '{t}' is not a test label (S<n> or S<n>.<m>)")
            elif t not in labels:
                problems.append(f"{PACK}: {mid}: test {t} does not exist in the pack")
    return problems, owed, listed

def self_test(plan_text, pack_text):
    """Broken copies of the real pack (in memory) must each fail with the matching message."""
    _, owed, _ = check(plan_text, pack_text)
    first = sorted(owed)[0]
    cases = [
        (f"a required milestone ({first}) removed from the index",
         re.sub(r"^%s .*\n" % re.escape(first), "", pack_text, count=1, flags=re.M), f"{first} is marked as needing"),
        ("an index entry for a milestone the plan lacks (M99.9)",
         pack_text.replace("```playtest-coverage\n", "```playtest-coverage\nM99.9 S1\n", 1), "M99.9 is in the coverage index but"),
        ("an index entry naming a test that doesn't exist (S9.9)",
         pack_text.replace("```playtest-coverage\n", "```playtest-coverage\n%s S9.9\n" % first, 1), "test S9.9 does not exist"),
        ("a test heading removed from the pack (S1.1)",
         re.sub(r"^\*\*S1\.1 ", "**", pack_text, count=1, flags=re.M), "test S1.1 does not exist"),
        ("the coverage block missing", pack_text.replace("```playtest-coverage", "```text", 1), "exactly one ```playtest-coverage block"),
    ]
    failed = 0
    for name, broken, expect in cases:
        problems, _, _ = check(plan_text, broken)
        ok = any(expect in p for p in problems)
        failed += not ok
        print(f"SELF-TEST {'PASS' if ok else 'FAIL'} {name}: {'caught' if ok else 'NOT caught'}")
    # Harmless reformatting must not fail.
    harmless = [
        ("test headings rewritten as Markdown headings",
         plan_text, re.sub(r"^\*\*(S\d+\.\d+) ([^*\n]*)\*\*", r"### \1 \2", pack_text, flags=re.M)),
        ("test headings with the label alone in bold",
         plan_text, re.sub(r"^\*\*(S\d+\.\d+) ([^*\n]*)\*\*", r"**\1** \2", pack_text, flags=re.M)),
        ("coverage lines with commas and extra spaces",
         plan_text, re.sub(r"^((?:M\d|E\d|W\d|B\d)\S*) (.+)$", lambda m: m.group(1) + "   " + ", ".join(m.group(2).split()),
                           pack_text.split("```playtest-coverage", 1)[0], flags=re.M) + "```playtest-coverage" +
         re.sub(r"^(\S+) (.+)$", lambda m: m.group(1) + "   " + ", ".join(m.group(2).split()),
                pack_text.split("```playtest-coverage", 1)[1].split("```", 1)[0], flags=re.M) +
         "```" + pack_text.split("```playtest-coverage", 1)[1].split("```", 1)[1]),
        ("plan table rows with extra spaces", re.sub(r"^\| (M\d{2}\.\d+[a-z]?|E\d+|W\d+) \|", r"|  \1  |", plan_text, flags=re.M), pack_text),
    ]
    for name, plan_v, pack_v in harmless:
        problems, owed2, _ = check(plan_v, pack_v)
        ok = not problems and owed2 == owed
        failed += not ok
        print(f"SELF-TEST {'PASS' if ok else 'FAIL'} {name}: {'no false failure' if ok else problems[:2] or 'owed set changed'}")
    return failed

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    repo = os.path.abspath(args[0]) if args else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    plan_text = open(os.path.join(repo, PLAN), encoding="utf-8").read()
    pack_text = open(os.path.join(repo, PACK), encoding="utf-8").read()
    problems, owed, listed = check(plan_text, pack_text)
    for p in problems:
        print(f"FAIL {p}")
    print(f"playtest pack: {len(owed)} milestones owe a runtime test in the plan; {len(listed)} listed in the coverage index; "
          f"{len(problems)} problem(s)")
    failed = bool(problems)
    if "--self-test" in sys.argv[1:]:
        before = [open(os.path.join(repo, f), "rb").read() for f in (PLAN, PACK)]
        failed = self_test(plan_text, pack_text) > 0 or failed
        unchanged = before == [open(os.path.join(repo, f), "rb").read() for f in (PLAN, PACK)]
        print(f"SELF-TEST {'PASS' if unchanged else 'FAIL'} the plan and the pack are unchanged on disk")
        failed = failed or not unchanged
    print("PLAYTEST PACK COVERAGE PASSED" if not failed else "PLAYTEST PACK COVERAGE FAILED")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
