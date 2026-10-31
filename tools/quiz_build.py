"""단원평가 만들기 — web_builder.py 가 부릅니다.

1) tools/quiz_items.py 의 문장·근거를 교본 텍스트와 대조합니다(하나라도 없으면 빌드 중단).
2) quiz/uNN.json (빈칸·O/X·5지선다) 과 quiz/0N_…_단원평가.md 를 만듭니다.
"""
import hashlib
import json
import re
from pathlib import Path

from kichul_build import UNIT_PAGES, load_sources, norm
from quiz_items import IMG_OK, OCR_FIX, QUIZ

UNIT_TITLES = {
    1: "연세대학교 의료원 현황 및 주요 현안", 2: "연세대학교 의료원 역사 및 가치", 3: "보건의료 정책 변화",
    4: "인사규정 및 상벌규정", 5: "자산관리규정", 6: "의료법", 7: "국민건강보험법 및 요양급여기준",
}
PAGE_NAMES = {
    1: "01_의료원현황_단원평가.md", 2: "02_역사및가치_단원평가.md", 3: "03_보건의료정책_단원평가.md",
    4: "04_인사상벌규정_단원평가.md", 5: "05_자산관리규정_단원평가.md", 6: "06_의료법_단원평가.md",
    7: "07_국민건강보험법_단원평가.md",
}
PARTS = [("blank", "① 빈칸 채우기"), ("ox", "② O/X"), ("mc", "③ 5지선다")]
SEP = re.compile(r" … | · | — | → ")
BLANK = re.compile(r"\[\[(.+?)\]\]")


def fill(s):
    return BLANK.sub(r"\1", s)


def missing(pages, doc, p, text):
    src = pages.get((doc, p))
    if src is None:
        return [f"{doc} p.{p} 원문 없음"]
    for wrong, right in OCR_FIX.get((doc, p), []):
        src = src.replace(wrong, right)
    src_n = norm(src)
    ok = {norm(x) for x in IMG_OK.get((doc, p), [])}
    return [seg for seg in SEP.split(text) if norm(seg) and norm(seg) not in src_n and norm(seg) not in ok]


def verify(base: Path):
    pages, _ = load_sources(base)
    errors = []
    for u, parts in QUIZ.items():
        doc = f"unit{u:02d}"
        for part, items in parts.items():
            for i, it in enumerate(items, 1):
                tag = f"{u}강 {part} {i}번"
                t = it["t"]

                def chk(p, text):
                    for seg in missing(pages, doc, p, text):
                        errors.append(f"{tag}: p.{p} 원문에 없음 → {seg}")

                if t in ("blank", "cl"):
                    n = len(BLANK.findall(it["s"]))
                    if n < 1 or (t == "cl" and n != 1):
                        errors.append(f"{tag}: 빈칸 표시 [[ ]] 개수 오류")
                    chk(it["p"], fill(it["s"]))
                    if t == "cl":
                        ans = BLANK.search(it["s"]).group(1)
                        if len(it["wrong"]) != 4 or len(set(it["wrong"] + [ans])) != 5:
                            errors.append(f"{tag}: 오답 보기는 정답과 다른 4개여야 함")
                elif t == "ox":
                    if it["orig"] is None:
                        chk(it["p"], it["s"])
                    else:
                        chk(it["p"], it["orig"])
                        if norm(it["s"]) == norm(it["orig"]):
                            errors.append(f"{tag}: X 문장이 원문과 같음")
                elif t == "mc":
                    if len(it["choices"]) != 5 or len(set(it["choices"])) != 5 or not 1 <= it["answer"] <= 5:
                        errors.append(f"{tag}: 보기 5개·정답 번호 오류")
                    for p, text in it["quotes"]:
                        chk(p, text)
                elif t == "not":
                    if len(it["rights"]) != 4:
                        errors.append(f"{tag}: 옳은 보기는 4개여야 함")
                    for p, text in it["rights"]:
                        chk(p, text)
                    p, stmt, orig = it["wrong"]
                    chk(p, orig)
                    if norm(stmt) == norm(orig):
                        errors.append(f"{tag}: 바꾼 보기가 원문과 같음")
    return errors


def place(key, correct, others):
    """정답 위치를 문항마다 고정된 값으로 섞음(빌드할 때마다 같은 순서)."""
    pos = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % (len(others) + 1)
    return others[:pos] + [correct] + others[pos:], pos + 1


def quote(doc, p, text, label=None):
    q = {"text": text, "doc": doc, "p": p}
    if label:
        q["label"] = label
    return q


def to_json(u, part, it):
    doc = f"unit{u:02d}"
    t = it["t"]
    if t == "blank":
        answers, k = [], [0]

        def mark(m):
            ans = m.group(1)
            nxt = re.match(r"[^\s,.()/·~\[\]]+", it["s"][m.end():])
            alts = [ans] + ([ans + nxt.group(0)] if nxt else []) + it["alts"]
            answers.append(alts)
            k[0] += 1
            return "{{%d}}" % (k[0] - 1)

        text = BLANK.sub(mark, it["s"])
        return {"type": "blank", "unit": u, "q": text, "answers": answers, "quotes": [quote(doc, it["p"], fill(it["s"]))]}
    if t == "ox":
        is_o = it["orig"] is None
        return {"type": "ox", "unit": u, "q": it["s"], "choices": ["O", "X"], "answer": 1 if is_o else 2,
                "explain": "교본 원문 그대로입니다." if is_o else "교본 원문과 다른 부분이 있습니다. 원문을 확인하세요.",
                "quotes": [quote(doc, it["p"], it["orig"] or it["s"])]}
    if t == "cl":
        ans = BLANK.search(it["s"]).group(1)
        choices, answer = place(it["s"], ans, list(it["wrong"]))
        return {"type": "mc", "unit": u, "q": "다음 ( ) 안에 들어갈 말로 옳은 것은?",
                "passage": BLANK.sub("(          )", it["s"]), "choices": choices, "answer": answer,
                "quotes": [quote(doc, it["p"], fill(it["s"]))]}
    if t == "mc":
        return {"type": "mc", "unit": u, "q": it["q"], "choices": it["choices"], "answer": it["answer"],
                "quotes": [quote(doc, p, text) for p, text in it["quotes"]]}
    if t == "not":
        p, stmt, orig = it["wrong"]
        choices, answer = place(it["q"] + stmt, stmt, [s for _, s in it["rights"]])
        return {"type": "mc", "unit": u, "q": it["q"], "choices": choices, "answer": answer,
                "quotes": [quote(doc, p, orig, "옳지 않은 보기의 교본 원문")]}
    raise ValueError(t)


def page_md(u, counts):
    title = UNIT_TITLES[u]
    nxt = (f'<a class="complete-btn" href="#/quiz/{PAGE_NAMES[u + 1]}">제{u + 1}강 단원평가 ➔</a>' if u < 7
           else '<a class="complete-btn" href="#/mock/01_실전모의고사_1회.md">실전 모의고사 1회 ➔</a>')
    out = [
        "<!-- 이 문서는 web_builder.py 가 tools/quiz_items.py 로 만듭니다. 고칠 때는 tools/quiz_items.py 를 고치세요. -->",
        '<div class="lecture-header-box">',
        f'  <span class="lecture-badge">단원평가 • 제{u}강</span>',
        f"  <h2>✍️ 제{u}강 {title}</h2>",
        f"  <p>빈칸 채우기 {counts['blank']} · O/X {counts['ox']} · 5지선다 {counts['mc']}문항 · 열 때마다 순서와 보기를 새로 섞어 출제하고, 채점하면 정답과 2026 교본 원문·쪽이 표시됩니다. 푼 기록은 이 기기에 저장됩니다.</p>",
        "</div>",
        "",
        f"# 제{u}강 단원평가",
        "",
        '<div class="note-key"><ul>'
        "<li><b>빈칸 채우기</b>: 교본 원문 문장의 중요한 항목이 빈칸입니다. 직접 입력하세요. 띄어쓰기·쉼표는 채점에 영향을 주지 않습니다. 입력 후 Enter를 누르면 다음 빈칸으로 넘어갑니다.</li>"
        "<li><b>O/X</b>: 교본 원문 그대로면 O, 한 곳이라도 바뀌었으면 X입니다.</li>"
        "<li><b>5지선다</b>: 근거는 모두 2026 교본 원문입니다. 오답 보기와 X 문장은 원문을 바꾼 것입니다.</li>"
        "<li>채점하면 문항마다 교본 원문과 쪽 번호가 나오고, 쪽 번호를 누르면 e-book 원본 지면이 열립니다.</li>"
        "</ul></div>",
        "",
        '<div data-tabs="panels" hidden></div>',
    ]
    for part, label in PARTS:
        out += ["", f"## {label} ({counts[part]}문항)", "",
                f'<div class="mock-exam" data-src="quiz/u{u:02d}.json" data-part="{part}"></div>']
    out += ["", '<div class="lesson-footer-nav">',
            f'  <a class="complete-btn secondary" href="#/{UNIT_PAGES[u]}">📘 제{u}강 핵심노트</a>',
            f"  {nxt}", "</div>", ""]
    return "\n".join(out)


def build(base: Path):
    errors = verify(base)
    if errors:
        raise SystemExit("❌ 단원평가 원문 대조 실패:\n  " + "\n  ".join(errors))
    out_dir = base / "quiz"
    out_dir.mkdir(exist_ok=True)
    total = 0
    for u, parts in QUIZ.items():
        data = {"id": f"u{u:02d}", "title": f"제{u}강 {UNIT_TITLES[u]} 단원평가", "parts": {}}
        for part, _ in PARTS:
            qs = []
            for it in parts[part]:
                q = to_json(u, part, it)
                key = json.dumps([q["q"], q.get("passage", ""), q["quotes"][0]["text"]], ensure_ascii=False)
                q = {"id": f"u{u:02d}-{part}-" + hashlib.md5(key.encode("utf-8")).hexdigest()[:8], **q}
                qs.append(q)
            ids = [q["id"] for q in qs]
            assert len(ids) == len(set(ids)), f"{u}강 {part}: 같은 문항이 두 번 있음"
            data["parts"][part] = qs
        (out_dir / f"u{u:02d}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        counts = {part: len(parts[part]) for part, _ in PARTS}
        (out_dir / PAGE_NAMES[u]).write_text(page_md(u, counts), encoding="utf-8")
        total += sum(counts.values())
    print(f"✍️ 단원평가: 7개 단원 {total}문항 원문 대조 통과 → quiz/")
