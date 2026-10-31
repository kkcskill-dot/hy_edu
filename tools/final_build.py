"""파이널 숫자 암기노트 만들기 — web_builder.py 가 부릅니다.

7개 핵심노트(summary/01~07)의 '🧠 숫자 암기표'(문장마다 교본 쪽 링크가 있는 표)를 그대로 모아
summary/00_간호사_승급시험_최종합격_핵심요약집.md 를 새로 씁니다. 핵심노트를 고치면 다음 빌드에 함께 바뀝니다.
"""
import re
from pathlib import Path

from kichul_build import UNIT_PAGES
from quiz_build import PAGE_NAMES, UNIT_TITLES

OUT_NAME = "summary/00_간호사_승급시험_최종합격_핵심요약집.md"


def number_table(md_text):
    lines = md_text.split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("## 🧠"))
    table = []
    for l in lines[start + 1:]:
        if l.startswith("| "):
            table.append(l)
        elif table:
            break
    return table


def build(base: Path):
    out = [
        "<!-- 이 문서는 web_builder.py 가 핵심노트(summary/01~07)의 '🧠 숫자 암기표'로 만듭니다. 고칠 때는 각 핵심노트를 고치세요. -->",
        '<div class="lecture-header-box">',
        '  <span class="lecture-badge">파이널 • 숫자 암기노트</span>',
        "  <h2>🧠 파이널 숫자 암기노트</h2>",
        "  <p>7개 단원 핵심노트의 숫자 암기표를 한곳에 모았습니다. 쪽 번호를 누르면 2026 교본 원본 지면이 열립니다.</p>",
        "</div>",
        "",
        "# 파이널 숫자 암기노트 (2026 교본 기준)",
        "",
        '<div class="note-key"><ul>'
        "<li>각 표는 해당 단원 핵심노트의 '🧠 숫자 암기표'와 같습니다. 모든 줄에 2026 교본 쪽 번호가 있습니다.</li>"
        "<li>문제로 확인하려면 단원평가(빈칸·O/X·5지선다), 실전 모의고사, 2023–2025 기출 복원을 이용하세요.</li>"
        "</ul></div>",
        "",
        '<div data-tabs="panels" hidden></div>',
    ]
    rows = 0
    for u in range(1, 8):
        table = number_table((base / UNIT_PAGES[u]).read_text(encoding="utf-8"))
        if not table or not all("reader.html?doc=unit" in l for l in table[2:]):
            raise SystemExit(f"❌ 파이널 암기노트: {u}강 숫자 암기표를 찾지 못했거나 쪽 링크가 없는 줄이 있습니다")
        rows += len(table) - 2
        short = {1: "현황", 2: "역사·가치", 3: "보건의료 정책", 4: "인사·상벌", 5: "자산관리", 6: "의료법", 7: "건강보험법"}[u]
        out += ["", f"## {u}강 {short}", "", *table, "",
                f'<p><a href="#/{UNIT_PAGES[u]}">📘 {u}강 핵심노트</a> · <a href="#/quiz/{PAGE_NAMES[u]}">✍️ {u}강 단원평가</a></p>']
    out += ["", '<div class="lesson-footer-nav">',
            '  <a class="complete-btn secondary" href="#/summary/08_역대기출분석_및_실전합격가이드.md">🎯 2023–2025 기출 복원</a>',
            '  <a class="complete-btn" href="#/mock/01_실전모의고사_1회.md">실전 모의고사 1회 ➔</a>',
            "</div>", ""]
    (base / OUT_NAME).write_text("\n".join(out), encoding="utf-8")
    print(f"🧠 파이널 숫자 암기노트: 7개 단원 {rows}줄 (모두 교본 쪽 링크) → {OUT_NAME}")
