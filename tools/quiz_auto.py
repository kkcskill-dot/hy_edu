"""단원평가 문제은행 확장 — 교본 원문의 완결된 문장에서 문항을 자동으로 만듭니다(quiz_build.py 가 부름).

원칙
- 문장은 교본 텍스트(original/0N_*.md) 그대로만 씁니다. OCR 이 망가뜨린 흔적이 있는 문장, 앞뒤 문맥이 있어야
  뜻이 통하는 문장(단, / 이 경우 / 다음 각 호 …), 슬라이드 제목·목록이 섞인 문장은 버립니다.
- 중요한 항목 = 숫자(기간·비율·금액·인원 등) 또는 결정 주체(보건복지부장관, 주관부서 …).
  같은 항목이 문장에 두 번 나오면(정답이 보이므로) 그 항목은 쓰지 않습니다.
- 한 문장에서 빈칸 · O/X · 5지선다를 하나씩 만듭니다.
  O/X 는 원문 그대로(O) 또는 그 항목만 바꾼 문장(X, 해설에 원문), 5지선다는 같은 단위의 다른 값이나
  같은 종류의 다른 주체가 오답 보기입니다.
- 같은 입력이면 늘 같은 결과(빌드할 때마다 문항 id 가 바뀌지 않게).
"""
import hashlib
import re
from statistics import quantiles

from quiz_items import B, CL, O, X

JUNK = re.compile(r"연세대학교\s*의료원|인재경영|인재개발|이재경영|인재가업|인재기업|인재장선|YONS|UNIV|MEALT|HEALTH|"
                  r"S[1I]S|STST|SYSTEM|RSITY|SEVERANCE|^2026\s*3급|^\(?\s*\d{2,3}\s*\)?$|^[)|]$|OCR")
BROKEN = re.compile(r"개전으|요정하는|사처의|업무정치|책임김|바당|핵신|수령한다|붙량|외료원|블라스|븐란스|부란슨|간호힉|"
                    r"outcomel|P의료급여|꽃페|\(초\)|의뢰사|\(\*률\)|5t\)|[®©|]|[A-Za-z]{2,}|(^|\s)[A-Za-z](\s|$)|\d\s\d|"
                    r"\s\d{1,2}\s[가-힣]|^\d{1,2}\s|세정체류|\.\.|,,|\(\s*\)|오의|"
                    r"[一-龥]|[^\w\s가-힣.,·•:;()\[\]~%/\-'\"‘’“”「」『』<>①-⑳※✓→]")
NEEDS_CONTEXT = re.compile(r"^(단[,\s]|다만|이 경우|이때|또한|그러나|그 밖|전\s?각\s?항|전\s?\d\s?항|전\s?호|같은 조|제\d+항에|위\s|아래|"
                           r"구청장|군수|비속|도지사|자치구)|"
                           r"다음 각 호|다음과 같|다음의|아래와 같|각 호의|이 규정|전항|동항|그 기간|그 결과|해당 기간|"
                           r"개정|시행한다|시행 한다|삭제|부칙|제\d+장|(^|\s)[가나다라마바사]\.\s|.\s제\d+조\s?\(")
END = re.compile(r"(함|음|됨|다|것|없음|가능|불가|금지|있음|못함|아니함|아니 됨|안 됨)\.?$")

UNITS = r"(개월|개년|년|일|시간|주|회|명|인|개|병상|%p|%|만원|억원|천만원|원|배|층|평|건|례|대|위|세|종)"
NUM = re.compile(r"(?<![\d,.])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s?" + UNITS)
LADDER = {
    "일": [3, 5, 7, 10, 14, 15, 20, 30, 60, 90], "개월": [1, 2, 3, 6, 9, 12], "년": [1, 2, 3, 5, 7, 10], "개년": [1, 2, 3, 5],
    "시간": [12, 24, 48, 72], "주": [1, 2, 4, 8], "회": [1, 2, 3, 4, 5], "명": [3, 5, 7, 9, 12, 15, 20, 30, 50, 90],
    "인": [3, 5, 7, 9, 12, 15], "개": [3, 5, 7, 9, 10, 20, 30, 50, 100], "병상": [30, 50, 100, 300, 500],
    "%": [5, 10, 15, 20, 30, 40, 50, 60, 70], "%p": [5, 10, 15, 20], "만원": [30, 50, 100, 200, 300, 500],
    "억원": [1, 3, 5, 10, 20, 50], "천만원": [1, 2, 3, 5], "원": [100000, 300000, 500000, 1000000, 2000000],
    "배": [2, 3, 5, 10], "층": [3, 5, 7, 9, 11, 13], "대": [1, 2, 3, 4], "위": [1, 2, 3, 5, 10], "종": [3, 4, 5, 6, 7],
}
ROLES = [
    ["보건복지부장관", "질병관리청장", "시·도지사", "국민건강보험공단 이사장", "건강보험심사평가원장"],
    ["대통령령", "보건복지부령", "총리령"],
    ["주관부서", "사용부서", "기술부서", "검수부서"],
    ["의료원장", "단위기관장", "부서장", "주관부서장"],
    ["인사위원회", "징계위원회", "포상위원회"],
    ["경찰서장", "보건소장", "시장·군수·구청장"],
]
ROLE_OF = {r: fam for fam in ROLES for r in fam}
ROLE_RE = re.compile("|".join(sorted((re.escape(r).replace("·", "[·•]\\s?") for r in ROLE_OF), key=len, reverse=True)))
PARTICLES = ("하", "한", "할", "함", "해", "했", "되", "된", "될", "됨", "을", "를", "은", "는", "이", "가", "의", "에", "로",
             "와", "과", "도", "만", "까지", "부터", "에서", "에게", "여", "야", "고", "며", "면", "서", "다", "음")


def h(s):
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)


_PREFIX = {}


def prefix_count(vocab, p):
    """교본 전체에서 p 로 시작하는 낱말 수(줄바꿈으로 끊긴 낱말을 붙일지 판단할 때 씀)."""
    if not _PREFIX:
        for w, c in vocab.items():
            for k in range(2, min(5, len(w)) + 1):
                _PREFIX[w[:k]] = _PREFIX.get(w[:k], 0) + c
    return _PREFIX.get(p, 0)


def statements(txt, vocab):
    """쪽 텍스트 → 완결된 문장들. 줄 끝에서 끊긴 낱말은 줄 길이·낱말 빈도로 붙일지 판단."""
    raw = [l.strip() for l in txt.split("\n") if l.strip()]
    lines = [l for l in raw if not JUNK.search(l)]
    if not lines:
        return []
    wide = quantiles([len(l) for l in lines], n=10)[-1] if len(lines) >= 4 else max(len(l) for l in lines)
    # 로고·쪽번호 같은 줄을 지나면 문장을 끊음(원문에서 떨어진 글을 잇지 않도록)
    blocks, flat, prev = [], "", ""
    for l in raw:
        if JUNK.search(l):
            if flat:
                blocks.append(flat)
            flat, prev = "", ""
            continue
        if not flat:
            flat, prev = l, l
            continue
        a = re.search(r"([가-힣]+)$", flat)
        b = re.match(r"^([가-힣]+)", l)
        glue = False
        if a and b and len(prev) >= 0.6 * wide:
            head, tail = a.group(1), b.group(1)
            if tail.startswith(PARTICLES) and len(tail) <= 2:
                glue = True
            elif vocab.get(head + tail, 0) > 0 or prefix_count(vocab, head + tail[:1]) > 2 * vocab.get(head, 0):
                glue = True
        flat += ("" if glue else " ") + l
        prev = l
    if flat:
        blocks.append(flat)
    parts = []
    for block in blocks:
        parts += re.split(r"\s*(?:✓|•|※|ㆍ|>|〉)\s*|\s(?=[①-⑳]\s?)|\s(?=\d{1,2}\.\s?[가-힣])|(?<=[함음됨다])\.\s+|\s(?=-\s[가-힣])", block)
    out = []
    for p in parts:
        p = re.sub(r"^[①-⑳]\s?|^\d{1,2}\.\s?|^-\s", "", p.strip(" -·")).strip()
        if 22 <= len(p) <= 150 and END.search(p) and not BROKEN.search(p) and not NEEDS_CONTEXT.search(p) \
                and p.count("(") == p.count(")"):
            out.append(p)
    return out


def num_alts(value, unit, n):
    """같은 단위의 자연스러운 다른 값 n개 — 아래·위 값을 번갈아(정수만, 원래 값과 너무 동떨어진 값 제외)."""
    v = float(value.replace(",", ""))
    ladder = [float(x) for x in LADDER.get(unit, []) if x != v and v / 10 <= x <= v * 10]
    below = sorted((x for x in ladder if x < v), reverse=True)
    above = sorted(x for x in ladder if x > v)
    pick = []
    while len(pick) < n and (below or above):
        for side in (below, above):
            if side and len(pick) < n:
                pick.append(side.pop(0))
    # 단위 표가 모자랄 때만: 2배·절반·3배 → ±1
    for x in (v * 2, round(v / 2), v * 3, v * 4, v + 1, v - 1, v + 2):
        if len(pick) >= n:
            break
        if x > 0 and float(x).is_integer() and x != v and x not in pick:
            pick.append(float(x))

    def fmt(x):
        x = int(x) if float(x).is_integer() else x
        return f"{x:,}" if ("," in value and isinstance(x, int)) else str(x)
    return sorted({fmt(x) for x in pick}, key=lambda t: float(t.replace(",", "")))


def pick_number(s):
    """빈칸으로 쓸 숫자: 연도·같은 문장에 또 나오는 값은 빼고, 1보다는 다른 값을 먼저."""
    cands = []
    for m in NUM.finditer(s):
        val, unit = m.group(1), m.group(2)
        if unit == "년" and 1900 <= float(val.replace(",", "")) <= 2100:
            continue
        if len(re.findall(r"(?<![\d,.])" + re.escape(val) + r"\s?" + unit, s)) > 1:
            continue
        cands.append(m)
    cands.sort(key=lambda m: (m.group(1) == "1", m.start()))
    return cands[0] if cands else None


def items_for(unit, pages, vocab, taken):
    """단원 하나의 자동 문항 {blank:[], ox:[], mc:[]}"""
    out = {"blank": [], "ox": [], "mc": []}
    seen = set()
    doc = f"unit{unit:02d}"
    for p in sorted(pg for (d, pg) in pages if d == doc):
        for s in statements(pages[(doc, p)], vocab):
            key = re.sub(r"\W", "", s)
            if key in seen or any(key in t or t in key for t in taken):
                continue
            seen.add(key)
            m = pick_number(s)
            if m:
                value, u_ = m.group(1), m.group(2)
                a, b = m.span(1)
                alts = num_alts(value, u_, 4)
                out["blank"].append(B(p, s[:a] + "[[" + value + "]]" + s[b:]))
                if h(s + "ox") % 2:
                    out["ox"].append(O(p, s))
                elif alts:
                    out["ox"].append(X(p, s[:a] + alts[h(s) % len(alts)] + s[b:], s))
                if len(alts) == 4:
                    out["mc"].append(CL(p, s[:a] + "[[" + value + u_ + "]]" + s[m.end(2):], [x + u_ for x in alts]))
                continue
            r = ROLE_RE.search(s)
            if not r:
                continue
            word = r.group(0)
            name = re.sub(r"[·•]\s?", "·", word)
            fam = ROLE_OF.get(name)
            if not fam or len(ROLE_RE.findall(s)) > 1 and sum(1 for x in ROLE_RE.findall(s) if re.sub(r"[·•]\s?", "·", x) == name) > 1:
                continue
            others = [x for x in fam if x != name]
            a, b = r.span()
            out["blank"].append(B(p, s[:a] + "[[" + word + "]]" + s[b:]))
            if h(s + "ox") % 2:
                out["ox"].append(O(p, s))
            else:
                out["ox"].append(X(p, s[:a] + others[h(s) % len(others)] + s[b:], s))
            if len(others) >= 4:
                out["mc"].append(CL(p, s[:a] + "[[" + word + "]]" + s[b:], others[:4]))
    return out
