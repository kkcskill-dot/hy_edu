"""기출 페이지 만들기 — web_builder.py 가 부릅니다.

1) tools/kichul_items.py 의 메모를 기출 메모 원문(data/extracted/kichul_2023-2025.txt)과,
   2026 근거 원문을 교본(original/0N_*.md)·소식지(data/extracted/webzine/*.txt) 텍스트와 대조합니다.
   하나라도 원문에 없으면 빌드를 멈춥니다(띄어쓰기·따옴표·가운뎃점 차이는 무시).
2) summary/08_역대기출분석_및_실전합격가이드.md 를 새로 씁니다.
"""
import html
import re
from collections import Counter
from pathlib import Path

from kichul_items import AREAS, IMG_OK, ITEMS, MEMO_END, OCR_FIX, SECTIONS

UNIT_PAGES = {
    1: "summary/01_연세대학교_의료원_현황_및_주요_현안.md",
    2: "summary/02_연세대학교_의료원_역사_및_가치.md",
    3: "summary/03_보건의료_정책_변화.md",
    4: "summary/04_인사규정_및_상벌규정.md",
    5: "summary/05_자산관리규정.md",
    6: "summary/06_의료법.md",
    7: "summary/07_국민건강보험법_및_요양급여기준.md",
}
AREA_CLASS = {"NEWS": "news", "HIST": "hist", "LABOR": "labor", "HEALTH": "health", "MGMT": "mgmt", "ETC": "etc"}
OUT_NAME = "summary/08_역대기출분석_및_실전합격가이드.md"
_STRIP = re.compile(r"[\s'\"‘’“”「」『』•·‧∙・✓※]")


def norm(s):
    return _STRIP.sub("", s)


def load_sources(base: Path):
    pages = {}
    for md in sorted((base / "original").glob("0[1-7]_*.md")):
        unit = int(md.name[:2])
        parts = re.split(r"=== \[PDF (\d+)쪽 / 총 \d+쪽\] ===", md.read_text(encoding="utf-8"))
        for i in range(1, len(parts), 2):
            pages[(f"unit{unit:02d}", int(parts[i]))] = parts[i + 1]
    for txt in sorted((base / "data" / "extracted" / "webzine").glob("*.txt")):
        issue = txt.name[:3]
        parts = re.split(r"=== \[페이지 (\d+) / \d+\] ===", txt.read_text(encoding="utf-8"))
        for i in range(1, len(parts), 2):
            pages[(f"webzine-{issue}", int(parts[i]))] = parts[i + 1]
    memo = (base / "data" / "extracted" / "kichul_2023-2025.txt").read_text(encoding="utf-8")
    return pages, memo


def verify(base: Path):
    pages, memo = load_sources(base)
    memo_n = norm(re.sub(r"=== \[페이지 \d+ / \d+\] ===", "", memo))
    errors, seen = [], set()
    for year, no, text, mpage, area, refs in ITEMS:
        key = (year, no)
        if key in seen:
            errors.append(f"{year} {no}번: 번호 중복")
        seen.add(key)
        if norm(text) not in memo_n:
            errors.append(f"{year} {no}번: 메모 원문에 없음 → {text}")
        if area not in AREAS:
            errors.append(f"{year} {no}번: 영역 코드 오류 {area}")
        for doc, page, quote, kind in refs:
            src = pages.get((doc, page))
            if src is None:
                errors.append(f"{year} {no}번: {doc} p.{page} 원문 없음")
                continue
            for wrong, right in OCR_FIX.get((doc, page), []):
                src = src.replace(wrong, right)
            src_n = norm(src)
            img_ok = {norm(x) for x in IMG_OK.get((doc, page), [])}
            for seg in re.split(r" … | → | · ", quote):
                if norm(seg) and norm(seg) not in src_n and norm(seg) not in img_ok:
                    errors.append(f"{year} {no}번: {doc} p.{page} 원문에 없는 조각 → {seg}")
            if kind not in ("same", "rel"):
                errors.append(f"{year} {no}번: 근거 종류 오류 {kind}")
    if norm(MEMO_END[0]) not in memo_n:
        errors.append("메모 끝 문구가 원문에 없음")
    return errors


def esc(s):
    return html.escape(s, quote=False)


def no_label(no):
    if no.startswith("·"):
        return "번호 없음"
    if no.startswith("+"):
        return f"50번 다음 {no[1:]}번"
    return f"{no}번"


def item_id(year, no):
    return f"kc-{year}-" + no.replace("·", "x").replace("+", "b")


def ref_html(doc, page, quote, kind):
    if doc.startswith("unit"):
        unit = int(doc[4:])
        tag = "📘 2026 교본" if kind == "same" else "🔎 참고 · 2026 교본"
        label = f"{unit}강 p.{page}"
    else:
        issue = doc.split("-")[1]
        tag = f"📰 2026 소식지 {issue}호" if kind == "same" else f"🔎 참고 · 2026 소식지 {issue}호"
        label = f"{issue}호 p.{page}"
    return (f'<div class="kc-ref {kind}"><span class="kc-ref-tag">{tag}</span>'
            f'<span class="kc-q">“{esc(quote)}”</span> '
            f'<a class="src" href="reader.html?doc={doc}&amp;p={page}">{label}</a></div>')


def item_html(year, no, text, mpage, area, refs, with_year=False):
    cls = f"u{area}" if isinstance(area, int) else AREA_CLASS[area]
    label = (f"{year} · " if with_year else "") + no_label(no)
    head = (f'<div class="kc-top"><span class="kc-no">{label}</span>'
            f'<span class="kc-area {cls}">{esc(AREAS[area])}</span>'
            f'<a class="kc-memo-src" href="reader.html?doc=kichul&amp;p={mpage}">메모 p.{mpage}</a></div>')
    body = f'<div class="kc-memo">{esc(text)}</div>'
    if refs:
        body += "".join(ref_html(*r) for r in refs)
    else:
        body += '<div class="kc-ref none">2026 교본·소식지에서 관련 내용을 찾지 못했습니다</div>'
    kind = "is-unit" if isinstance(area, int) else ("is-etc" if area == "ETC" else "is-out")
    return f'<div class="kc-item {kind}" id="{item_id(year, no)}">{head}{body}</div>'


def render():
    years = [2023, 2024, 2025]
    order = list(range(1, 8)) + ["NEWS", "HIST", "LABOR", "HEALTH", "MGMT", "ETC"]
    count = Counter((y, a) for y, _, _, _, a, _ in ITEMS)
    total = Counter(y for y, *_ in ITEMS)
    n_all = len(ITEMS)
    n_unit = sum(1 for it in ITEMS if isinstance(it[4], int))
    n_same = sum(1 for it in ITEMS if any(r[3] == "same" for r in it[5]))
    n_none = sum(1 for it in ITEMS if not it[5])

    out = [
        "<!-- 이 문서는 web_builder.py 가 tools/kichul_items.py 로 만듭니다. 고칠 때는 tools/kichul_items.py 를 고치세요. -->",
        '<div class="lecture-header-box">',
        '  <span class="lecture-badge">오리엔테이션 • 기출 복원</span>',
        "  <h2>🎯 2023–2025 기출 × 2026 교본</h2>",
        f"  <p>기출 복원 메모 {n_all}문항을 연도별로 그대로 옮기고, 문항마다 2026 교본·소식지 원문을 붙였습니다</p>",
        "</div>",
        "",
        "# 2023–2025 기출 복원 · 2026 교본 기준",
        "",
        '<div class="note-key"><ul>'
        "<li><b>기출 메모</b>는 받은 메모 그대로입니다. 오타·줄임말도 고치지 않았습니다. "
        '<a href="reader.html?doc=kichul">메모 원본(e-book)</a></li>'
        "<li><b>📘 2026 교본</b>은 같은 내용을 다루는 2026 교본 원문, <b>🔎 참고</b>는 관련 내용입니다. "
        "과거 기준과 달라졌을 수 있으니 <b>2026 교본 문장이 기준</b>입니다.</li>"
        "<li><b>📰 2026 소식지</b>는 같은 주제를 다룬 2026 연세의료원 소식 기사입니다.</li>"
        "<li>교본·소식지에서 찾지 못한 문항은 그렇게 표시했습니다. 답을 지어 넣지 않았습니다.</li>"
        f"<li>메모 끝 문구: “{esc(MEMO_END[0])}” (메모 p.{MEMO_END[1]})</li>"
        "</ul></div>",
        "",
        '<div class="page-tabs-extra kc-filter" role="group" aria-label="영역 필터">'
        '<button type="button" data-f="all" class="is-active">전체</button>'
        '<button type="button" data-f="unit">교본 1~7강</button>'
        '<button type="button" data-f="out">교본 밖</button>'
        '<button type="button" data-f="etc">메모 불명확</button></div>',
        '<div data-tabs="panels" hidden></div>',
        "",
        "## 한눈에 보기",
        "",
        f"- 전체 **{n_all}문항** 중 2026 교본 1~7강 주제 **{n_unit}문항**, 교본 밖 영역 **{n_all - n_unit}문항**",
        f"- 2026 교본·소식지에 같은 내용이 있는 문항 **{n_same}문항**, 관련 내용도 찾지 못한 문항 **{n_none}문항**",
        "",
        "| 영역 | 2023 | 2024 | 2025 | 합계 |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for area in order:
        cells = [count[(y, area)] for y in years]
        name = AREAS[area]
        if isinstance(area, int):
            name = f"[{name}]({UNIT_PAGES[area]})"
        out.append(f"| {name} | " + " | ".join(str(c) for c in cells) + f" | **{sum(cells)}** |")
    out.append("| **합계** | " + " | ".join(f"**{total[y]}**" for y in years) + f" | **{n_all}** |")
    out.append("")
    for y in years:
        rows = [it for it in ITEMS if it[0] == y]
        out += ["", f"## {y}년 기출 ({len(rows)}문항)", "", '<div class="kc-list">']
        for it in rows:
            sec = SECTIONS.get((y, it[1]))
            if sec:
                out.append(f'<div class="kc-sec">{esc(sec)}</div>')
            out.append(item_html(*it))
        out.append("</div>")
    out += ["", "---", "",
            "출처: 2023–2025 기출 복원 메모(받은 메모 9쪽) · 2026년도 3급 승진교육 교본 1~7 · 2026 연세의료원 소식(977~994호)", ""]
    return "\n".join(out)


START, END = "<!-- kichul:start -->", "<!-- kichul:end -->"


def unit_block(u):
    """핵심노트 끝의 '기출 체크': 이 단원 주제이거나 이 단원 교본을 근거로 단 기출 문항."""
    doc = f"unit{u:02d}"
    its = [it for it in ITEMS if it[4] == u or any(r[0] == doc for r in it[5])]
    rows = [START, "", f"## 🎯 기출 체크 (2023–2025 · {len(its)}문항)", "",
            '<div class="kc-list kc-unit-block">'
            '<p class="kc-intro">이 단원 주제로 나온 2023–2025 기출 메모입니다. 메모는 그대로 두고, 아래에 2026 교본 원문을 붙였습니다. '
            '본문 쪽 번호 옆 <b>기출</b> 표시를 누르면 해당 문항으로 옵니다. '
            f'<a href="#/{OUT_NAME}">기출 전체 보기</a></p>']
    rows += [item_html(*it, with_year=True) for it in its]
    rows += ["</div>", "", END]
    return "\n".join(rows), len(its)


def inject(base: Path):
    total = 0
    for u, rel in UNIT_PAGES.items():
        path = base / rel
        text = path.read_text(encoding="utf-8")
        block, n = unit_block(u)
        total += n
        if START in text:
            text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, text, flags=re.S)
        else:
            # 핵심노트 끝의 '🧠' 암기표 바로 앞에 넣음
            assert "\n## 🧠" in text, rel
            text = text.replace("\n## 🧠", "\n" + block + "\n\n## 🧠", 1)
        path.write_text(text, encoding="utf-8")
    return total


def build(base: Path):
    errors = verify(base)
    if errors:
        raise SystemExit("❌ 기출 데이터 대조 실패:\n  " + "\n  ".join(errors))
    (base / OUT_NAME).write_text(render(), encoding="utf-8")
    print(f"🎯 단원 핵심노트 '기출 체크': {inject(base)}문항 연결")
    n_ref = sum(len(it[5]) for it in ITEMS)
    print(f"🎯 기출 페이지: {len(ITEMS)}문항 · 2026 근거 {n_ref}개 원문 대조 통과 → {OUT_NAME}")
