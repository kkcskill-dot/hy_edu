"""2026 소식지 핵심노트·문제은행 만들기 — web_builder.py 가 부릅니다.

1) tools/webzine_items.py 의 문장·목록·제목을 소식지 텍스트(data/extracted/webzine/*.txt)와 대조합니다.
   하나라도 원문에 없으면 빌드를 멈춥니다(띄어쓰기·따옴표·가운뎃점·하이픈 차이는 무시).
2) summary/09 호별 핵심노트 · summary/10 주제별 모아보기 · quiz/08 문제은행(quiz/w01.json) ·
   original/webzine_2026_전체색인.md 를 새로 씁니다.
"""
import hashlib
import html
import json
import re
from collections import defaultdict
from pathlib import Path

from kichul_build import item_html as kc_item_html
from kichul_build import load_sources, norm
from kichul_items import ITEMS as KC_ITEMS
from webzine_items import CATS, CORE, DECOYS, DONATIONS, IMG_OK, NEWS, NO_NOT, OCR_FIX, RESEARCH, SHORT

BLANK = re.compile(r"\[\[(.+?)\]\]")


def wnorm(s):
    """띄어쓰기·따옴표·가운뎃점에 더해 하이픈도 무시 (줄 끝에서 끊긴 SEVER-ANCE, Cap-off 등)"""
    return norm(s).replace("-", "")


def plain(s):
    return BLANK.sub(r"\1", s)


def page_text(pages, no, p):
    src = pages.get((f"webzine-{no}", p))
    if src is None:
        return None
    for wrong, right in OCR_FIX.get((no, p), []):
        src = src.replace(wrong, right)
    # 단 사이에 끼어든 지면 머리글(제977호 2026년 1월 5일 · 2 연세의료원소식 주요뉴스 …)은 빼고 대조
    src = re.sub(r"\n(\d\s*연세의료원소식[^\n]*제\s*\d+호\s*2026년\s*\d+월\s*\d+일|제\s*\d+호[^\n]*연세의료원소식\s*\d|제\s*\d+호\n2026년 \d+월 \d+일)\n", "\n", src)
    # 같은 줄에 기사 제목이 이어지는 머리글(6 연세의료원소식 홍용우 동문 …)은 머리글 부분만 뺌
    src = re.sub(r"(?m)^\d\s*연세의료원소식\s*", "", src)
    # 사진 위치 표시(<사진 왼쪽>)는 빼고 대조
    src = re.sub(r"<\s*사진[^>]*>", "", src)
    return wnorm(src)


def missing(pages, no, p, text):
    src = page_text(pages, no, p)
    if src is None:
        return [f"{no}호 p.{p} 원문 없음"]
    ok = {wnorm(x) for x in IMG_OK.get((no, p), [])}
    segs = [s for s in plain(text).split(" … ") if wnorm(s)]
    return [s for s in segs if wnorm(s) not in src and wnorm(s) not in ok]


def verify(base: Path):
    pages, memo = load_sources(base)
    errors = []

    def chk(tag, no, p, text):
        for seg in missing(pages, no, p, text):
            errors.append(f"{tag}: {no}호 p.{p} 원문에 없음 → {seg}")

    for i, a in enumerate(NEWS, 1):
        tag = f"기사 {i} ({a['no']}호 {a['head'][:20]})"
        if a["cat"] not in CATS:
            errors.append(f"{tag}: 분류 오류 {a['cat']}")
        # 제목 뒤 ' (… · …)' 는 지면 문구로 붙인 꼬리표 — 조각마다 같은 쪽에서 대조
        m = re.match(r"(.+?)(?: \(([^()]+)\))?$", a["head"])
        chk(tag, a["no"], a["p"], m.group(1))
        for piece in (m.group(2) or "").split(" · "):
            if piece:
                chk(tag + " 꼬리표", a["no"], a["p"], piece)
        for f in a["facts"]:
            chk(tag, a["no"], a["p"], f)
        for lst in a["lists"]:
            for it in lst["items"]:
                chk(tag + " 목록", a["no"], a["p"], it)
            if lst["intro"]:
                chk(tag + " 목록 소개", a["no"], a["p"], lst["intro"])
    for r in RESEARCH:
        chk(f"연구 {r['no']}호", r["no"], r["p"], r["head"])
        chk(f"연구 {r['no']}호 연구팀", r["no"], r["p"], r["team"])
    for d in DONATIONS:
        chk(f"기부 {d['no']}호", d["no"], d["p"], d["head"])
    names = {l["name"]: (a, l) for a in NEWS for l in a["lists"]}
    for name, spec in DECOYS.items():
        if name not in names:
            errors.append(f"오답 보기: 목록 이름 없음 → {name}")
        elif spec[0] == "text":
            chk(f"오답 보기({name})", spec[1], spec[2], spec[3])
        elif spec[1] not in names or spec[2] >= len(names[spec[1]][1]["items"]):
            errors.append(f"오답 보기: 다른 목록 항목 없음 → {spec}")
    for name, labels in SHORT.items():
        a, _ = names[name]
        for x in labels:
            chk(f"짧은 이름({name})", a["no"], a["p"], x)
    memo_n = wnorm(re.sub(r"=== \[페이지 \d+ / \d+\] ===", "", memo))
    for no, p, q, choices, ans, quotes in CORE:
        if len(choices) != 5 or len(set(choices)) != 5 or not 1 <= ans <= 5:
            errors.append(f"핵심 문항 보기·정답 오류 → {q}")
        for t in quotes:
            if isinstance(t, tuple):
                if wnorm(t[2]) not in memo_n:
                    errors.append(f"핵심 문항 근거가 기출 메모에 없음 → {t[2]}")
            else:
                chk(f"핵심 문항({q[:15]})", no, p, t)
    return errors


# ───────────────────────── 화면 만들기 ─────────────────────────
NOTE_PAGE = "summary/09_2026_소식지_핵심노트.md"
THEME_PAGE = "summary/10_2026_소식지_주제별_모아보기.md"
QUIZ_PAGE = "quiz/08_2026_소식지_문제은행.md"
QUIZ_JSON = "quiz/w01.json"
INDEX_PAGE = "original/webzine_2026_전체색인.md"
CAT_ICON = {"의료원": "⛪", "평가": "🏅", "진료": "🩺", "기관": "🏥", "AI": "🤖",
            "수상": "🏆", "기부": "🎁", "협력": "🤝", "교육": "🎓", "인사": "👥"}
GEN = "<!-- 이 문서는 web_builder.py 가 tools/webzine_items.py 로 만듭니다. 고칠 때는 tools/webzine_items.py 를 고치세요. -->"


def esc(s):
    return html.escape(s, quote=False)


def rich(s):
    """[[굵게]] → <b>, 나머지는 HTML 이스케이프"""
    out, last = [], 0
    for m in BLANK.finditer(s):
        out.append(esc(s[last:m.start()]) + "<b>" + esc(m.group(1)) + "</b>")
        last = m.end()
    return "".join(out) + esc(s[last:])


def head_md(s):
    """마크다운 제목에 넣을 글자 (취소선·굵게로 바뀌는 기호는 문자 참조로)"""
    return esc(s).replace("~", "&#126;").replace("*", "&#42;").replace("_", "&#95;")


def src(no, p, label=None):
    return f'<a class="src" href="reader.html?doc=webzine-{no}&p={p}">{label or f"{no}호 p.{p}"}</a>'


def load_meta(base):
    meta = json.loads((base / "data" / "2026_webzine" / "metadata.json").read_text(encoding="utf-8"))
    return {x["issue"]: x for x in meta}


def kdate(d, short=False):
    y, m, dd = (int(x) for x in d.split("-"))
    return f"{m}.{dd}." if short else f"{y}년 {m}월 {dd}일"


def art_id(a):
    return f"wz-{a['no']}-{NEWS.index(a) + 1}"


def disp(x):
    """목록 글머리 기호(▲)만 빼고 보여 줌"""
    return re.sub(r"\s*▲\s*", " ", x).strip()


def list_html(lst, no=None, p=None, show_src=False):
    items = "".join(f"<li>{esc(disp(x))}</li>" for x in lst["items"])
    where = f" {src(no, p)}" if show_src else ""
    intro = f'<p class="wz-intro">원문 “{esc(lst["intro"])}”</p>' if lst["intro"] else ""
    return (f'<div class="wz-list"><div class="wz-list-name">📋 {esc(lst["name"])} '
            f'<span class="wz-n">{len(lst["items"])}개</span>{where}</div><ol>{items}</ol>{intro}</div>')


def article_html(a, compact=False):
    star = '<span class="wz-star">★ 핵심</span>' if a["star"] else ""
    facts = "".join(f"<li>{rich(f)}</li>" for f in a["facts"])
    body = f'<ul class="wz-facts">{facts}</ul>' if facts else ""
    body += "".join(list_html(lst) for lst in a["lists"])
    if compact:
        return (f'<li class="wz-c" id="{art_id(a)}-t"><div class="wz-c-head"><b>{esc(a["head"])}</b> {star} {src(a["no"], a["p"])}</div>'
                f'{body}</li>')
    return (f'<div class="wz-item{" is-star" if a["star"] else ""}" id="{art_id(a)}">'
            f'<div class="wz-meta"><span class="wz-cat">{CAT_ICON[a["cat"]]} {CATS[a["cat"]]}</span>{star}</div>{body}</div>')


def by_issue(rows):
    out = defaultdict(list)
    for r in rows:
        out[r["no"]].append(r)
    for v in out.values():
        v.sort(key=lambda r: r["p"])
    return out


def kichul_news():
    """2023–2025 기출 가운데 '의료원 소식' 영역이거나 2026 소식지를 근거로 단 문항"""
    return [it for it in KC_ITEMS if it[4] == "NEWS" or any(r[0].startswith("webzine-") for r in it[5])]


def render_note(base, meta):
    news, res, don = by_issue(NEWS), by_issue(RESEARCH), by_issue(DONATIONS)
    n_list = sum(len(a["lists"]) for a in NEWS)
    out = [GEN,
           '<div class="lecture-header-box">',
           '  <span class="lecture-badge">특강 • 2026 소식지 18개 호</span>',
           "  <h2>📰 2026 연세의료원 소식지 핵심노트</h2>",
           f"  <p>제977호(2026.1.5.)~제994호(2026.10.26.) · 주요 기사 {len(NEWS)}건 · 목록 {n_list}개 · 연구 성과 {len(RESEARCH)}건 · 기부 {len(DONATIONS)}건 — "
           "문장은 모두 소식지 원문 그대로이며, 쪽 번호를 누르면 e-book 원본 지면이 열립니다.</p>",
           "</div>", "",
           "# 2026 소식지 핵심노트 (호별)", "",
           '<div class="note-key"><ul>'
           "<li><b>★ 핵심</b>: 1면 기사, 목록이 있는 기사, 간호 관련 기사입니다.</li>"
           "<li><b>📋 목록</b>: ‘다음 중 아닌 것은?’ 대비입니다. 항목과 개수를 함께 외우세요. 모든 목록은 "
           f'<a href="#/{THEME_PAGE}">주제별 모아보기 › 📋 목록 암기</a>에 모았습니다.</li>'
           f'<li><b>굵은 글씨</b>는 <a href="#/{QUIZ_PAGE}">소식지 문제은행</a>의 빈칸으로 나오는 곳입니다.</li>'
           "<li>쪽 번호(예: 977호 p.1)를 누르면 e-book 원본 지면이 열립니다. 글자 인식 과정에서 띄어쓰기가 다른 곳이 있을 수 있으니 이상하면 지면으로 확인하세요.</li>"
           "</ul></div>", ""]
    months = defaultdict(list)
    for no in sorted(meta):
        months[int(meta[no]["date"][5:7])].append(no)
    for mon in sorted(months):
        nos = months[mon]
        out += [f"## {mon}월 · " + "·".join(f"{n}호" for n in nos), ""]
        for no in nos:
            d = meta[no]["date"]
            out += [f"### 제{no}호 · {kdate(d)} {src(no, 1, '1면 보기')}", ""]
            for a in news.get(no, []):
                out += [f"#### {head_md(a['head'])} {src(no, a['p'])}", "", article_html(a), ""]
            if res.get(no):
                rows = "".join(f"<li>{esc(r['head'])} <span class=\"wz-team\">— {esc(r['team'])}</span> {src(no, r['p'], f'p.{r[chr(112)]}')}</li>"
                               for r in res[no])
                out += [f'<div class="wz-sub"><div class="wz-sub-name">🔬 {no}호 연구 성과 {len(res[no])}건</div><ul>{rows}</ul></div>', ""]
            if don.get(no):
                rows = "".join(f"<li>{esc(x['head'])} {src(no, x['p'], f'p.{x[chr(112)]}')}</li>" for x in don[no])
                out += [f'<div class="wz-sub"><div class="wz-sub-name">🎁 {no}호 기부 {len(don[no])}건</div><ul>{rows}</ul></div>', ""]
    kc = kichul_news()
    out += [f"## 🎯 기출 연결 (2023–2025 · {len(kc)}문항)", "",
            '<div class="kc-list kc-unit-block"><p class="kc-intro">기출 메모 가운데 의료원 소식을 다룬 문항입니다. 메모는 그대로 두고 2026 소식지·교본 원문을 붙였습니다. '
            "본문 쪽 번호 옆 <b>기출</b> 표시를 누르면 해당 문항으로 옵니다. "
            '<a href="#/summary/08_역대기출분석_및_실전합격가이드.md">기출 전체 보기</a></p>']
    out += [kc_item_html(*it, with_year=True) for it in kc]
    out += ["</div>", "",
            '<div class="lesson-footer-nav">',
            f'  <a class="complete-btn secondary" href="#/{THEME_PAGE}">🗂️ 주제별 모아보기</a>',
            f'  <a class="complete-btn" href="#/{QUIZ_PAGE}">✍️ 소식지 문제은행 ➔</a>',
            "</div>", ""]
    (base / NOTE_PAGE).write_text("\n".join(out), encoding="utf-8")


STREAK = re.compile(r"연속|최초|처음|첫 |첫\]|세계 첫|국내 첫")


def render_theme(base, meta):
    out = [GEN,
           '<div class="lecture-header-box">',
           '  <span class="lecture-badge">특강 • 2026 소식지 주제별</span>',
           "  <h2>🗂️ 2026 소식지 주제별 모아보기</h2>",
           "  <p>18개 호의 기사를 주제별로 다시 모았습니다. ‘다음 중 아닌 것은?’에 대비한 목록 암기, 연속·최초 기록, 연구 성과·기부 표를 탭으로 나눠 봅니다.</p>",
           "</div>", "",
           "# 2026 소식지 주제별 모아보기", "",
           '<div data-tabs="panels" hidden></div>', ""]
    lists = [(a, l) for a in NEWS for l in a["lists"]]
    lists.sort(key=lambda x: (x[0]["no"], x[0]["p"]))
    out += [f"## 📋 목록 암기 ({len(lists)})", "",
            '<p class="wz-lead">시험에서는 보기 5개 중 <b>아닌 것</b>을 고르게 냅니다. 항목 이름과 개수를 함께 외우세요. 쪽 번호를 누르면 원본 지면이 열립니다.</p>', ""]
    for no in sorted({a["no"] for a, _ in lists}):
        out += [f"### {no}호 · {kdate(meta[no]['date'], short=True)}", ""]
        for a, l in lists:
            if a["no"] == no:
                out += [f'<p class="wz-from">{esc(a["head"])}</p>' + list_html(l, a["no"], a["p"], show_src=True), ""]
    streak = [(a, f) for a in NEWS for f in a["facts"] if STREAK.search(plain(f))]
    out += [f"## 🔢 연속·최초 ({len(streak)})", "",
            '<p class="wz-lead">‘N년 연속’, ‘국내·세계 최초’ 문장만 모았습니다. 숫자와 기관 이름을 바꿔 내기 좋은 문장들입니다.</p>', "",
            '<ul class="wz-flat">' + "".join(f"<li>{rich(f)} {src(a['no'], a['p'])}</li>" for a, f in streak) + "</ul>", ""]
    for cat in CATS:
        rows = [a for a in NEWS if a["cat"] == cat]
        rows.sort(key=lambda a: (a["no"], a["p"]))
        out += [f"## {CAT_ICON[cat]} {CATS[cat]} ({len(rows)})", "",
                '<ul class="wz-compact">' + "".join(article_html(a, compact=True) for a in rows) + "</ul>", ""]
    rs = sorted(RESEARCH, key=lambda r: (r["no"], r["p"]))
    out += [f"## 🔬 연구 성과 ({len(rs)})", "",
            '<p class="wz-lead">기출 예: ‘올해 세브란스 연구로 해당하지 않는 것은?’ — 연구 제목을 훑어 두세요.</p>', "",
            '<ul class="wz-flat">' + "".join(f"<li><b>{esc(r['head'])}</b> <span class=\"wz-team\">— {esc(r['team'])}</span> {src(r['no'], r['p'])}</li>" for r in rs) + "</ul>", ""]
    ds = sorted(DONATIONS, key=lambda d: (d["no"], d["p"]))
    big = [a for a in NEWS if a["cat"] == "기부" and a["star"]]
    out += [f"## 🎁 기부 ({len(ds)})", ""]
    for a in big:
        out += [f"#### {head_md(a['head'])} {src(a['no'], a['p'])}", "", article_html(a), ""]
    out += ['<ul class="wz-flat">' + "".join(f"<li>{esc(d['head'])} {src(d['no'], d['p'])}</li>" for d in ds) + "</ul>", "",
            '<div class="lesson-footer-nav">',
            f'  <a class="complete-btn secondary" href="#/{NOTE_PAGE}">📰 호별 핵심노트</a>',
            f'  <a class="complete-btn" href="#/{QUIZ_PAGE}">✍️ 소식지 문제은행 ➔</a>',
            "</div>", ""]
    (base / THEME_PAGE).write_text("\n".join(out), encoding="utf-8")


# ───────────────────────── 문제은행 ─────────────────────────
NUM = re.compile(r"^(\d[\d,.]*)\s*(.*)$")


def h(key):
    return int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)


def qid(kind, key):
    return f"w-{kind}-{hashlib.md5(key.encode('utf-8')).hexdigest()[:8]}"


def q_quote(a, text, label=None):
    q = {"text": text, "doc": f"webzine-{a['no']}", "p": a["p"]}
    if label:
        q["label"] = label
    return q


def answers_for(t):
    alts = [t]
    m = NUM.match(t)
    if m:
        alts.append(m.group(1))
    base = re.sub(r"\s*\([^)]*\)", "", t).strip()
    if base and base != t:
        alts.append(base)
    inner = re.findall(r"\(([^)]*)\)", t)
    alts += [x for x in inner if len(x) >= 2]
    return list(dict.fromkeys(alts))


def num_unit(t):
    m = NUM.match(t)
    if not m:
        return None
    unit = m.group(2).strip()
    return unit if not re.search(r"\d", unit) else None


def build_quiz():
    parts = {"core": [], "star": [], "list": [], "ox": [], "num": [], "blank": []}
    pool = defaultdict(set)  # 단위 → 숫자 표현들 (보기·바꾼 문장용)
    for a in NEWS:
        for f in a["facts"]:
            for m in BLANK.finditer(f):
                u = num_unit(m.group(1))
                if u is not None:
                    pool[u].add(m.group(1))

    def tag(a):
        return f"{a['no']}호"

    for a in NEWS:
        for fi, f in enumerate(a["facts"]):
            marks = list(BLANK.finditer(f))
            text = plain(f)
            key = f"{a['no']}-{a['p']}-{text}"
            if marks:
                pick = marks if len(marks) <= 2 else sorted(marks, key=lambda m: h(key + m.group(1)))[:2]
                pick = sorted(pick, key=lambda m: m.start())
                q, last, answers = "", 0, []
                for m in pick:
                    q += plain(f[last:m.start()]) + "{{%d}}" % len(answers)
                    answers.append(answers_for(m.group(1)))
                    last = m.end()
                q += plain(f[last:])
                item = {"id": qid("b", key), "type": "blank", "unit": "W", "tag": tag(a), "q": q,
                        "answers": answers, "quotes": [q_quote(a, text)]}
                parts["star" if a["star"] else "blank"].append(item)
            # O/X — 원문 그대로(O) 또는 숫자 하나를 다른 기사 숫자로 바꾼 문장(X)
            nums = [m for m in marks if num_unit(m.group(1)) is not None]
            if nums and h(key) % 2:
                m = nums[h(key + "x") % len(nums)]
                others = sorted(pool[num_unit(m.group(1))] - {m.group(1)})
                if others:
                    wrong = others[h(key + "w") % len(others)]
                    stmt = plain(f[:m.start()]) + wrong + plain(f[m.end():])
                    parts["ox"].append({"id": qid("x", key), "type": "ox", "unit": "W", "tag": tag(a), "q": stmt,
                                        "choices": ["O", "X"], "answer": 2,
                                        "explain": "소식지 원문과 다른 부분이 있습니다. 원문을 확인하세요.",
                                        "quotes": [q_quote(a, text)]})
                    continue
            parts["ox"].append({"id": qid("o", key), "type": "ox", "unit": "W", "tag": tag(a), "q": text,
                                "choices": ["O", "X"], "answer": 1, "explain": "소식지 원문 그대로입니다.",
                                "quotes": [q_quote(a, text)]})
            # 5지선다 — ( ) 안에 들어갈 숫자
            for m in nums[:1]:
                others = sorted(pool[num_unit(m.group(1))] - {m.group(1)}, key=lambda x: h(key + x))[:4]
                if len(others) < 4:
                    continue
                choices = sorted(others + [m.group(1)], key=lambda x: h(key + "c" + x))
                passage = plain(f[:m.start()]) + "(          )" + plain(f[m.end():])
                parts["num"].append({"id": qid("n", key), "type": "mc", "unit": "W", "tag": tag(a),
                                     "q": "다음 ( ) 안에 들어갈 말로 옳은 것은?", "passage": passage,
                                     "choices": choices, "answer": choices.index(m.group(1)) + 1,
                                     "quotes": [q_quote(a, text)]})
    # 목록 — '다음 중 아닌 것은?' (보기 4개는 목록 그대로, 오답 1개는 헷갈리기 쉬운 다른 원문 항목)
    lists = [(a, l) for a in NEWS for l in a["lists"]]
    by_name = {l["name"]: (a, l) for a, l in lists}
    for a, l in lists:
        if len(l["items"]) < 4 or l["name"] in NO_NOT:
            continue
        key = f"{a['no']}-{l['name']}"
        shown = SHORT.get(l["name"], [disp(x) for x in l["items"]])
        rights = sorted(shown, key=lambda x: h(key + x))[:4]
        mine = wnorm(" ".join(l["items"]))
        spec = DECOYS.get(l["name"])
        if spec and spec[0] == "text":
            b = {"no": spec[1], "p": spec[2]}
            decoy, why = spec[3], f"오답 보기의 원문 ({spec[1]}호)"
        elif spec:
            b, m = by_name[spec[1]]
            decoy, why = disp(m["items"][spec[2]]), f"오답 보기는 {b['no']}호 ‘{m['name']}’의 항목"
        else:
            avg = sum(len(x) for x in shown) / len(shown)

            def ok(x):
                return wnorm(x) not in mine and not re.search(r"다\.$|했다|됐다", x) and 0.5 * avg <= len(x) <= 2 * avg

            tiers = [[(b, m, x) for b, m in lists if b is a and m is not l for x in m["items"]],
                     [(b, m, x) for b, m in lists if b is not a and b["no"] == a["no"] and b["p"] == a["p"] for x in m["items"]],
                     [(b, m, x) for b, m in lists if b is not a and b["cat"] == a["cat"] for x in m["items"]],
                     [(b, m, x) for b, m in lists if m is not l for x in m["items"]]]
            cands = next((t for t in ([c for c in tier if ok(c[2])] for tier in tiers) if t), [])
            if not cands:
                continue
            cands.sort(key=lambda c: (abs(len(c[2]) - avg), h(key + c[2])))
            b, m, decoy = cands[0]
            decoy = disp(decoy)
            why = f"오답 보기는 {b['no']}호 ‘{m['name']}’의 항목"
        choices = sorted(rights + [decoy], key=lambda x: h(key + "c" + x))
        parts["list"].append({"id": qid("l", key), "type": "mc", "unit": "W", "tag": tag(a),
                              "q": f"다음 중 ‘{l['name']}’에 해당하지 않는 것은?",
                              "choices": choices, "answer": choices.index(decoy) + 1,
                              "quotes": [q_quote(a, " · ".join(l["items"]), f"{a['no']}호 목록"),
                                         q_quote(b, decoy, why)]})
        # 짧은 항목은 빈칸으로도
        short = [x for x in l["items"] if len(x) <= 14]
        if short:
            x = short[h(key + "b") % len(short)]
            shown = " · ".join("{{0}}" if y == x else y for y in l["items"])
            parts["list"].append({"id": qid("lb", key), "type": "blank", "unit": "W", "tag": tag(a),
                                  "q": f"{l['name']} ({len(l['items'])}개): {shown}", "answers": [answers_for(x)],
                                  "quotes": [q_quote(a, " · ".join(l["items"]), f"{a['no']}호 목록")]})
    # 핵심 기출형 — 직접 고른 5지선다
    for no, p, q, choices, ans, quotes in CORE:
        a = {"no": no, "p": p}
        qs = [q_quote(a, t) if not isinstance(t, tuple) else {"text": t[2], "doc": "kichul", "p": t[1], "label": "2023–2025 기출 메모"}
              for t in quotes]
        order = sorted(range(5), key=lambda i: h(q + str(i)))
        parts["core"].append({"id": qid("c", q), "type": "mc", "unit": "W", "tag": f"{no}호", "q": q,
                              "choices": [choices[i] for i in order], "answer": order.index(ans - 1) + 1, "quotes": qs})
    return parts


PART_TITLES = [("core", "⓪ 핵심 기출형"), ("list", "① 목록 · ‘아닌 것은?’"), ("star", "② 빈칸 — ★ 핵심 기사"),
               ("num", "③ 5지선다 — 숫자·연도"), ("ox", "④ O/X"), ("blank", "⑤ 빈칸 — 전체 기사")]


def render_quiz(base):
    parts = build_quiz()
    data = {"id": "w01", "title": "2026 소식지 문제은행", "parts": parts}
    (base / QUIZ_JSON).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    total = sum(len(v) for v in parts.values())
    out = [GEN,
           '<div class="lecture-header-box">',
           '  <span class="lecture-badge">문제은행 • 2026 소식지</span>',
           "  <h2>✍️ 2026 소식지 문제은행</h2>",
           f"  <p>소식지 18개 호 원문으로 만든 {total}문항 · 파트마다 20문항씩 열 때마다 새로 섞어 내고, 채점하면 정답과 소식지 원문·쪽이 표시됩니다. 푼 기록은 이 기기에 저장됩니다.</p>",
           "</div>", "",
           "# 2026 소식지 문제은행", "",
           '<div class="note-key"><ul>'
           "<li><b>빈칸</b>: 소식지 원문 문장의 굵은 글씨(핵심노트와 같은 곳)가 빈칸입니다. 띄어쓰기·쉼표는 채점에 영향을 주지 않습니다.</li>"
           "<li><b>핵심 기출형</b>: 기출에 나온 주제(의료선교의 달 주제, 기부금, N년 연속 1위, 기관장 등)를 2026 소식지 기준으로 낸 문항입니다. 오답 보기에는 기출 메모의 옛 답도 섞었습니다.</li>"
           "<li><b>목록 · 아닌 것은?</b>: 보기 4개는 그 목록의 원문 항목이고, 오답 1개는 <b>헷갈리기 쉬운 다른 원문 항목</b>(같은 기사의 다른 목록, 비슷한 다른 기사)입니다. 채점하면 오답 보기의 출처가 나옵니다.</li>"
           "<li><b>숫자·연도 5지선다</b>: 오답 보기는 다른 기사에 나온 같은 단위의 숫자입니다.</li>"
           "<li><b>O/X</b>: 원문 그대로면 O, 숫자 하나를 다른 기사 숫자로 바꿨으면 X입니다.</li>"
           f'<li>내용은 <a href="#/{NOTE_PAGE}">소식지 핵심노트</a>에서 먼저 읽고 오세요. 쪽 번호를 누르면 e-book 지면이 열립니다.</li>'
           "</ul></div>", "",
           '<div data-tabs="panels" hidden></div>', ""]
    for key, title in PART_TITLES:
        out += [f"## {title} ({len(parts[key])})", "", f'<div class="mock-exam" data-src="{QUIZ_JSON}" data-part="{key}"></div>', ""]
    out += ['<div class="lesson-footer-nav">',
            f'  <a class="complete-btn secondary" href="#/{NOTE_PAGE}">📰 소식지 핵심노트</a>',
            f'  <a class="complete-btn" href="#/{THEME_PAGE}">🗂️ 주제별 모아보기 ➔</a>',
            "</div>", ""]
    (base / QUIZ_PAGE).write_text("\n".join(out), encoding="utf-8")
    return {k: len(v) for k, v in parts.items()}


# ───────────────────────── 전 권 색인 ─────────────────────────
SKIP_TOC = re.compile(r"the FIRST|가장 신뢰받는|PDF 파일 보기|Adobe|COPYRIGHT|서대문구 연세로|^\[2026년|^『?\[?게시판")


def render_index(base, meta):
    pages, _ = load_sources(base)
    heads = {(a["no"], wnorm(re.sub(r" \([^()]*\)$", "", a["head"]))[:10]): a for a in NEWS}
    out = [GEN,
           "# 📰 2026 연세의료원 소식지 전 권 색인 (제977호~제994호)", "",
           '<div class="note-key"><ul>'
           "<li>18개 호의 기사 제목(세브란스 뉴스 웹진 목차 기준)을 호별로 모았습니다. <b>쪽 번호</b>를 누르면 e-book 지면이, <b>핵심노트</b>를 누르면 정리해 둔 기사가 열립니다.</li>"
           f'<li>내용 정리는 <a href="#/{NOTE_PAGE}">소식지 핵심노트(호별)</a> · <a href="#/{THEME_PAGE}">주제별 모아보기</a> · <a href="#/{QUIZ_PAGE}">문제은행</a>에 있습니다.</li>'
           "</ul></div>", "",
           "## Ⅰ. 호별 일람", "",
           "| 호 | 발행일 | 1면 핵심 기사 | 지면 |", "| :---: | :---: | :--- | :---: |"]
    for no in sorted(meta):
        p1 = [a for a in NEWS if a["no"] == no and a["p"] == 1]
        first = "<br>".join(esc(a["head"]) for a in p1[:3]) or "-"
        out.append(f"| **{no}호** | {meta[no]['date']} | {first} | {src(no, 1, 'e-book')} · <a href=\"{meta[no]['url']}\" target=\"_blank\">웹진</a> |")
    out += ["", "## Ⅱ. 호별 전체 기사 목록", ""]
    for no in sorted(meta):
        toc = [t.strip() for t in meta[no]["toc"] if t.strip() and not SKIP_TOC.search(t.strip())]
        toc = list(dict.fromkeys(toc))
        rows = []
        for t in toc:
            key = wnorm(t)[:10]
            p = next((pg for pg in range(1, 9) if len(key) >= 4 and key in (page_text(pages, no, pg) or "")), None)
            a = next((x for (n, k), x in heads.items() if n == no and k and (k in wnorm(t) or key in k)), None)
            link = src(no, p, f"p.{p}") if p else ""
            note = f' <a class="wz-to-note" href="#/{NOTE_PAGE}?id={art_id(a)}">핵심노트</a>' if a else ""
            rows.append(f"<li>{esc(t)} {link}{note}</li>")
        out += [f"### 제{no}호 · {kdate(meta[no]['date'])} {src(no, 1, 'e-book')}", "",
                f'<ul class="wz-toc">{"".join(rows)}</ul>', ""]
    (base / INDEX_PAGE).write_text("\n".join(out), encoding="utf-8")


def build(base: Path):
    errors = verify(base)
    if errors:
        raise SystemExit("❌ 소식지 데이터 대조 실패:\n  " + "\n  ".join(errors))
    meta = load_meta(base)
    render_note(base, meta)
    render_theme(base, meta)
    counts = render_quiz(base)
    render_index(base, meta)
    print(f"📰 소식지: 기사 {len(NEWS)}건 · 목록 {sum(len(a['lists']) for a in NEWS)}개 · 연구 {len(RESEARCH)} · 기부 {len(DONATIONS)} "
          f"→ 핵심노트·주제별·색인, 문제은행 {sum(counts.values())}문항 {counts}")


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    errs = verify(base)
    print("\n".join(errs) or "OK")
    print(len(NEWS), "기사", len(RESEARCH), "연구", len(DONATIONS), "기부")
