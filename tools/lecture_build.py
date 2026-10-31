"""슬라이드 강의 데이터 만들기 — web_builder.py 가 부릅니다.

교본 지면 이미지(ebook/unitNN/pNNN.webp)는 한 쪽에 슬라이드 2장(위·아래)이 들어 있습니다.
ebook/page_types.json: 쪽마다 '2'(슬라이드 2장) · '1'(위 1장) · '.'(표지·규정 원문 등 쪽 전체) — 이미지의 상자 테두리로 판별해 둔 값.

강의 한 장 = 교본 슬라이드 1장(또는 쪽 전체) + 그 쪽을 근거로 단 핵심노트 줄(문장 그대로).
위·아래 슬라이드 중 어디에 붙일지는 그 줄의 낱말이 교본 텍스트(OCR)의 앞쪽·뒤쪽 중 어디에 많이 나오는지로 정합니다.
"""
import html
import json
import re
from pathlib import Path

from kichul_build import UNIT_PAGES, load_sources, norm
from kichul_items import ITEMS as KC_ITEMS
from quiz_auto import JUNK

SRC = re.compile(r'<a class="src" href="reader\.html\?doc=unit0(\d)&p=(\d+)">p\.\d+</a>')
# 아래 슬라이드 시작 표시: 로고 줄(JUNK) 또는 슬라이드 머리글 — 본문의 '1. …' 같은 번호 줄은 제외
TITLE = re.compile(r"^(0\d\.\s?\S|제\s?\d+\s?장|CHAPTER|\[|SEVERANCE)")
STOP = {"있음", "없음", "경우", "하는", "있는", "또는", "등의", "위한", "따라", "대한", "에서", "으로", "하여", "해야", "하고", "것을", "모든"}


def inline(s):
    """핵심노트 한 줄 → 화면용 HTML(굵게만 살림, 쪽 링크·다른 태그 제거)."""
    s = SRC.sub("", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"\s+", " ", s.replace("`", "")).strip(" ·-")


def notes_of(md, unit):
    """핵심노트 → ([(장 이름, 쪽, html)], [[장 이름, 시작 쪽]]) — 🧠 암기표·기출 체크 앞까지.
    쪽 번호가 없는 줄(표의 행, 번호 목록 등)은 바로 위에서 나온 쪽을 이어받습니다. 맨 위 '시험 포인트' 상자는 뺍니다."""
    out, chapters = [], []
    chapter, page, in_key, table_row = "들어가며", None, False, 0
    for line in md.split("\n"):
        s = line.strip()
        if s.startswith("## 🧠") or s.startswith("<!-- kichul:start"):
            break
        if s.startswith('<div class="note-key"'):
            in_key = True
        if in_key:
            if s.startswith("</div>"):
                in_key = False
            continue
        if s.startswith("## "):
            chapter = re.sub(r"\s+", " ", SRC.sub("", s[3:])).strip()
            pgs = [int(p) for u, p in SRC.findall(s) if int(u) == unit]
            page = pgs[0] if pgs else None
            chapters.append([chapter, page])
            table_row = 0
            continue
        if not s.startswith("|"):
            table_row = 0
        if not s or s.startswith(("<", "---", "> 모든 내용은", "#### ", "# ")):
            continue
        pgs = [int(p) for u, p in SRC.findall(s) if int(u) == unit]
        if pgs:
            page = pgs[0]
        if page is None:
            continue
        if s.startswith("|"):
            table_row += 1
            cells = [c.strip() for c in s.strip("|").split("|")]
            if table_row == 1 or all(set(c) <= set(":- ") for c in cells):
                continue
            cells = [c for c in cells if SRC.sub("", c).strip()]
            if not cells:
                continue
            head = inline(cells[0])
            h = ('<span class="lv-k">' + head + "</span> " + inline(" · ".join(cells[1:]))) if len(cells) > 1 else head
        elif s.startswith("### "):
            h = '<span class="lv-h">' + inline(s[4:]) + "</span>"
        else:
            h = inline(re.sub(r"^([-*]|>)\s+", "", s))
        if len(re.sub(r"<[^>]+>", "", h)) >= 4:
            out.append((chapter, page, h))
            if chapters and chapters[-1][1] is None and chapters[-1][0] == chapter:
                chapters[-1][1] = page
    return out, chapters


def split_at(text):
    """OCR 쪽 텍스트에서 아래 슬라이드가 시작되는 위치(공백 없앤 글자 수)."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    n = len(lines)
    cands = [i for i, l in enumerate(lines) if n * 0.3 <= i <= n * 0.75 and (JUNK.search(l) or TITLE.search(l))]
    k = cands[0] if cands else n // 2
    return len(norm("".join(lines[:k])))


def tokens(h):
    t = re.sub(r"<[^>]+>", " ", h)
    words = re.findall(r"\d[\d,.]*\s?[가-힣%]*|[가-힣]{2,}", t)
    return [norm(w) for w in words if norm(w) and norm(w) not in STOP]


def evidence(h, src, cut):
    """-1(위 슬라이드) ~ +1(아래 슬라이드): 줄의 10~24글자 조각이 OCR 텍스트의 어디에 그대로 나오는지,
    없으면 낱말이 앞·뒤 어느 쪽에 많은지."""
    plain = norm(re.sub(r"<[^>]+>", "", h))
    for size in (24, 16, 10):
        hits = [src.find(plain[i:i + size]) for i in range(0, max(1, len(plain) - size + 1), max(1, size // 2))]
        hits = [x for x in hits if x >= 0]
        if hits:
            return 2 * sum(1 for x in hits if x >= cut) / len(hits) - 1
    before = after = 0
    for t in tokens(h):
        for m in re.finditer(re.escape(t), src):
            if m.start() < cut:
                before += 1
            else:
                after += 1
    return (after - before) / (after + before) if after + before else 0


def split_notes(notes, page_text):
    """한 쪽의 핵심노트 줄(교본 순서대로 정리돼 있음)을 위·아래 슬라이드로: 순서를 지키는 한 지점에서 나눔."""
    src = norm(page_text)
    cut = split_at(page_text)
    ev = [evidence(h, src, cut) for h in notes]
    # 핵심노트의 소제목(### 또는 굵은 제목만 있는 줄)이 쪽 중간에 있으면 그 자리에서만 나눔
    heads = [i for i, h in enumerate(notes) if i > 0 and (h.startswith('<span class="lv-h">') or re.fullmatch(r"<b>[^<]+</b>", h))]
    cands = [0] + heads + [len(notes)] if heads else range(len(notes) + 1)
    best_j, best = 0, None
    for j in cands:
        val = -sum(ev[:j]) + sum(ev[j:])
        if best is None or val > best:
            best_j, best = j, val
    return notes[:best_j], notes[best_j:]


def build(base: Path):
    types = json.loads((base / "ebook" / "page_types.json").read_text(encoding="utf-8"))
    pages, _ = load_sources(base)
    out_dir = base / "lecture"
    out_dir.mkdir(exist_ok=True)
    total = 0
    for unit, rel in UNIT_PAGES.items():
        doc = f"unit{unit:02d}"
        kinds = types[doc]
        md = (base / rel).read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", md, re.M).group(1).strip()
        notes, chapters = notes_of(md, unit)
        steps, index = [], {}
        for p, k in enumerate(kinds, 1):
            parts = ["cover"] if p == 1 else (["top", "bottom"] if k == "2" else (["top"] if k == "1" else ["page"]))
            for part in parts:
                index[(p, part)] = len(steps)
                steps.append({"p": p, "part": part, "notes": []})
        by_page = {}
        for chapter, p, h in notes:
            if p <= len(kinds):
                by_page.setdefault(p, []).append(h)
        for p, hs in by_page.items():
            k = kinds[p - 1]
            if p == 1:
                steps[index[(p, "cover")]]["notes"] += hs
            elif k == "2":
                top, bottom = split_notes(hs, pages.get((doc, p), ""))
                steps[index[(p, "top")]]["notes"] += top
                steps[index[(p, "bottom")]]["notes"] += bottom
            else:
                steps[index[(p, "top" if k == "1" else "page")]]["notes"] += hs
        chs = []
        for name, p in chapters:
            if p is None:
                continue
            first = min((i for i, s in enumerate(steps) if s["p"] >= p), default=None)
            if first is not None and (not chs or first >= chs[-1]["step"]):
                chs.append({"name": name, "step": first})
        kc = {}
        for year, no, memo, mp, area, refs in KC_ITEMS:
            for d, p, quote, kind in refs:
                if d == doc:
                    label = f"{year} · " + (("번호 없음" if no.startswith("·") else f"50번 다음 {no[1:]}번") if not no[0].isdigit() else f"{no}번")
                    kc.setdefault(str(p), []).append({"label": label, "memo": memo, "quote": quote, "kind": kind})
                    break
        data = {"unit": unit, "doc": doc, "title": title, "steps": steps, "chapters": chs, "kichul": kc}
        (out_dir / f"u{unit:02d}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        total += len(steps)
    print(f"🎬 슬라이드 강의: 7개 단원 {total}장 (교본 슬라이드 + 핵심노트 줄) → lecture/")
