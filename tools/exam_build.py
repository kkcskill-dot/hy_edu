"""문제풀이 공간(/exam) 데이터 만들기 — web_builder.py 가 부릅니다.

- 기본강의: tools/exam_u0N*.py 의 교본 문항을 교본 원문과 대조(tools/exam_check.py)한 뒤 단원별로 발행
- 소식지: 원문 대조를 마친 기본 문항(tools/news_basic_*.py)과 심화 문항(tools/news2026_*·ai2026_*)을
  호별로 다시 묶어 발행 (심화 문항은 첫 근거 지면의 호에 넣음)
- 고난도: tools/hard_*.py 의 중·상 난이도 문항을 검사(tools/hard_check.py)한 뒤 교본 단원별·소식지 호별로 발행

출력: exam/data/index.json · exam/data/unitNN.json · exam/data/newsNNN.json
      · exam/data/hard-unitNN.json · exam/data/hard-newsNNN.json
"""
import copy
import json
import re
from collections import Counter
from pathlib import Path

import exam_check

OUT = Path("exam/data")
ISSUES = range(977, 996)


def unit_titles(base):
    titles = {}
    for md in sorted((base / "original").glob("0[1-7]_*.md")):
        first = md.read_text(encoding="utf-8").splitlines()[0]
        m = re.match(r"#\s*\S*\s*제(\d+)단원 교본 원본:\s*(.+)", first)
        titles[int(m.group(1))] = m.group(2).strip()
    return titles


def textbook(base):
    items, sections = exam_check.load()
    errors = exam_check.verify(items, sections)
    if errors:
        raise ValueError("문제풀이 교본 문항 검증 실패:\n" + "\n".join(errors))
    titles = unit_titles(base)
    units = []
    for unit in sorted(titles):
        qs = sorted((q for q in items if q["unit"] == unit), key=lambda q: q["id"])
        if not qs:
            continue
        order = {s: i for i, s in enumerate(sections[unit])}
        qs.sort(key=lambda q: (order[q["section"]], q["quotes"][0]["p"], q["id"]))
        for q in qs:
            q["level"] = "기본"
        used = [s for s in sections[unit] if any(q["section"] == s for q in qs)]
        units.append({"id": f"unit{unit:02d}", "kind": "unit", "no": unit,
                      "title": titles[unit], "label": f"제{unit}강",
                      "sections": used, "questions": qs})
    return units


def issue_heads(base):
    """호 → 발행일(label)·대표 기사 제목(headline) — 소식지·고난도 세트가 함께 씀"""
    from webzine_items import NEWS

    meta = {x["issue"]: x for x in json.loads((base / "data/2026_webzine/metadata.json").read_text(encoding="utf-8"))}
    heads = {}
    for a in NEWS:
        heads.setdefault(a["no"], re.sub(r"\s*\([^()]*\)$", "", a["head"]))
    return {issue: {"label": meta[issue]["date"].replace("-", ".") + ". 발행", "headline": heads.get(issue, "")}
            for issue in ISSUES}


def news(base):
    from news_basic_build import load_items as basic_items, verify as basic_verify
    import news2026_build

    basic = copy.deepcopy(basic_items())
    deep_items = copy.deepcopy(news2026_build.ITEMS)
    errors = basic_verify(base, basic) + news2026_build.verify(base, deep_items)
    if errors:
        raise ValueError("소식지 문항 검증 실패:\n" + "\n".join(errors))
    heads = issue_heads(base)
    issues = []
    for issue in ISSUES:
        doc = f"webzine-{issue}"
        qs = []
        for q in basic:
            if q["quotes"][0]["doc"] == doc:
                qs.append(dict(q, level="기본", section="기본"))
        for q in deep_items:
            if q["quotes"][0]["doc"] == doc:
                qs.append(dict(q, level="심화", section="심화"))
        sections = [s for s in ("기본", "심화") if any(q["section"] == s for q in qs)]
        issues.append({"id": f"news{issue}", "kind": "news", "no": issue, "title": f"{issue}호",
                       **heads[issue], "sections": sections, "questions": qs})
    return issues


def hard(base):
    import hard_check

    found = hard_check.load()
    errors = hard_check.verify(found)
    if errors:
        raise ValueError("고난도 문항 검증 실패:\n" + "\n".join(errors))
    items = copy.deepcopy([q for name in found for q in found[name]])
    for q in items:
        q["level"] = "고난도"
    _, sections = exam_check.load()
    titles = unit_titles(base)
    sets = []
    for unit in range(1, 8):
        qs = [q for q in items if q["key"] == f"u{unit:02d}"]
        if not qs:
            continue
        order = {s: i for i, s in enumerate(sections[unit])}
        qs.sort(key=lambda q: (order[q["section"]], q["quotes"][0]["p"], q["id"]))
        used = [s for s in sections[unit] if any(q["section"] == s for q in qs)]
        sets.append({"id": f"hard-unit{unit:02d}", "kind": "unit", "no": unit,
                     "title": titles[unit], "label": f"제{unit}강",
                     "sections": used, "questions": qs})
    heads = issue_heads(base)
    for issue in ISSUES:
        # 소식지 문항의 기사 꼬리표(section)는 tag로 옮기고, 소단원 칸은 '고난도' 하나로 묶음
        qs = [dict(q, tag=q["section"], section="고난도") for q in items if q["key"] == f"n{issue}"]
        if not qs:
            continue
        qs.sort(key=lambda q: (q["quotes"][0]["p"], q["id"]))
        sets.append({"id": f"hard-news{issue}", "kind": "news", "no": issue, "title": f"{issue}호",
                     **heads[issue], "sections": ["고난도"], "questions": qs})
    return sets


def build(base):
    out = base / OUT
    out.mkdir(parents=True, exist_ok=True)
    # 세 묶음을 모두 만든 뒤에 아래에서 필드를 지움 (textbook()은 교본 문항 원본을 그대로 쓰고,
    # hard_check.verify()·hard()가 다시 부르는 exam_check.load()는 그 원본의 unit 값을 읽음)
    groups = [("textbook", "기본강의", "2026 교본 7개 단원", textbook(base)),
              ("news", "소식지", f"2026 소식지 {ISSUES.start}~{ISSUES.stop - 1}호", news(base)),
              ("hard", "고난도", f"중·상 난이도 · 교본 7개 단원 + 소식지 {len(ISSUES)}개 호", hard(base))]
    catalog = {"groups": []}
    written = set()
    for key, title, sub, sets in groups:
        entries = []
        for s in sets:
            qs = s["questions"]
            for q in qs:
                for k in ("type", "unit", "topic", "difficulty", "key", "truth"):
                    q.pop(k, None)
            name = f"{s['id']}.json"
            (out / name).write_text(json.dumps(s, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            written.add(name)
            entries.append({"id": s["id"], "kind": s["kind"], "no": s["no"], "title": s["title"],
                            "label": s["label"], "headline": s.get("headline", ""),
                            "count": len(qs), "ids": [q["id"] for q in qs], "levels": dict(Counter(q["level"] for q in qs)),
                            "sections": [{"name": sec, "count": sum(q["section"] == sec for q in qs)}
                                         for sec in s["sections"]]})
        catalog["groups"].append({"key": key, "title": title, "sub": sub,
                                  "count": sum(e["count"] for e in entries), "sets": entries})
    (out / "index.json").write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    for old in out.glob("*.json"):
        if old.name != "index.json" and old.name not in written:
            old.unlink()
    total = {g["title"]: g["count"] for g in catalog["groups"]}
    print(f"🧪 문제풀이 공간(/exam): " + " · ".join(f"{k} {v}문항" for k, v in total.items()))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    build(Path(__file__).resolve().parents[1])
