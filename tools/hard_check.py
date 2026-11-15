"""고난도 세트(tools/hard_*.py) 검사 — 원문 대조 · 형식 · 정답 일관성(truth) · 찍기 방지.

사용: python3 tools/hard_check.py                 # 전체
      python3 tools/hard_check.py hard_u03        # 파일 하나 (여러 개 가능)

찍기 방지 검사 (공부 안 하고 맞히는 단서를 막음)
- 보기 다수결: 복합 보기·빈칸 짝짓기·순서 배열에서 다른 보기와 가장 많이 겹치는 보기가 정답이면 실패
- 모든 보기에 들어간 진술(판단할 필요 없음)이 있으면 실패
- 정답 보기만 유난히 긴 경우(나머지 최장의 1.25배 초과) 실패
- 단정어(반드시·모든·항상…)·부정어(않·없)가 틀린 진술에만 있으면 실패
- 정답 번호·유형 비율이 한쪽으로 쏠리면 실패
"""
import importlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hard_schema import FORMATS  # noqa: E402
import exam_check  # noqa: E402
from kichul_build import load_sources  # noqa: E402
import webzine_build  # noqa: E402

BASE = Path(__file__).resolve().parents[1]
# 모듈 → (세트들, 세트당 목표 문항 수, 번호 범위)
TEXT = {
    "hard_u01": (["u01"], 15, range(1, 100)), "hard_u02": (["u02"], 15, range(1, 100)),
    "hard_u03": (["u03"], 20, range(1, 100)),
    "hard_u04a": (["u04"], 15, range(1, 100)), "hard_u04b": (["u04"], 15, range(101, 200)),
    "hard_u05": (["u05"], 20, range(1, 100)),
    "hard_u06a": (["u06"], 15, range(1, 100)), "hard_u06b": (["u06"], 15, range(101, 200)),
    "hard_u07": (["u07"], 20, range(1, 100)),
}
NEWS = {
    "hard_n977_979": ([f"n{i}" for i in range(977, 980)], 8, range(1, 100)),
    "hard_n980_982": ([f"n{i}" for i in range(980, 983)], 8, range(1, 100)),
    "hard_n983_985": ([f"n{i}" for i in range(983, 986)], 8, range(1, 100)),
    "hard_n986_988": ([f"n{i}" for i in range(986, 989)], 8, range(1, 100)),
    "hard_n989_991": ([f"n{i}" for i in range(989, 992)], 8, range(1, 100)),
    "hard_n992_995": ([f"n{i}" for i in range(992, 996)], 8, range(1, 100)),
}
MODULES = {**TEXT, **NEWS}

NEG = re.compile(r"틀린|옳지 않은|아닌 것|해당하지 않는|포함되지 않는|없는 것|적절하지 않은")
ABS = re.compile(r"반드시|모든|항상|절대|오직|전혀|무조건|일체|어떠한")
NOT = re.compile(r"않|없|못하|아니")
LABELS = ("가", "나", "다", "라", "마")
COUNT_SETS = (["1개", "2개", "3개", "4개", "5개"], ["0개", "1개", "2개", "3개", "4개"])
NEG_OK = ("틀린 설명", "개수 판단", "복합 보기", "사례 적용")


def statements(passage):
    out = []
    for line in (passage or "").split("\n"):
        m = re.match(r"\s*([ㄱ-ㅎ])\.\s*(.+)", line)
        if m:
            out.append((m.group(1), m.group(2).strip()))
    return out


def blanks(choice):
    parts = re.split(r"\((가|나|다|라|마)\)", choice)
    return {parts[i]: re.sub(r"[\s,·/]+$", "", parts[i + 1]).strip() for i in range(1, len(parts) - 1, 2)}


def centroid_is_answer(features, ans):
    """다른 보기와 겹치는 정도가 가장 큰 보기(유일)가 정답이면 True — 보기만 보고 고를 수 있음"""
    n = len(features)
    scores = [sum(1 for d, v in enumerate(f) for j in range(n) if j != i and features[j][d] == v)
              for i, f in enumerate(features)]
    best = max(scores)
    return scores[ans] == best and scores.count(best) == 1


def quote_errors(pages, key, doc, p, text):
    if doc.startswith("webzine-"):
        return [f"{key}: {doc} p.{p} 원문 불일치 → {s}" for s in webzine_build.missing(pages, int(doc[-3:]), p, text)]
    src = exam_check.page_text(pages, doc, p)
    if src is None:
        return [f"{key}: {doc} p.{p} 원문 쪽 없음"]
    ok = {exam_check.wnorm(x) for x in exam_check.IMG_OK.get((doc, p), [])}
    return [f"{key}: {doc} p.{p} 원문에 없는 조각 → {seg}" for seg in text.split(" … ")
            if exam_check.wnorm(seg) and exam_check.wnorm(seg) not in src and exam_check.wnorm(seg) not in ok]


def load(names=None):
    found = {}
    for name in names or MODULES:
        try:
            found[name] = importlib.import_module(name).ITEMS
        except ModuleNotFoundError as e:
            if e.name != name:
                raise
    return found


def check_item(q, sections, pages):
    key = q.get("id", "ID 없음")
    errs = []
    m = re.fullmatch(r"hd-(u0[1-7]|n9\d\d)-(\d{3})", key)
    if not m or m.group(1) != q.get("key"):
        errs.append(f"{key}: ID 형식 오류")
        return errs
    kind, stem, choices, ans = q.get("format"), q.get("q", ""), q.get("choices", []), q.get("answer")
    neg = bool(NEG.search(stem))
    if q["key"].startswith("u"):
        if q.get("section") not in sections.get(int(q["key"][1:]), []):
            errs.append(f"{key}: 그 단원 SECTIONS에 없는 소단원 {q.get('section')}")
    elif not q.get("section"):
        errs.append(f"{key}: 소식지 문항은 section에 기사 꼬리표 필요")
    if kind not in FORMATS:
        errs.append(f"{key}: 유형 오류 {kind}")
        return errs
    if len(choices) != 5 or len(set(c.strip() for c in choices)) != 5 or not all(isinstance(c, str) and c.strip() for c in choices):
        errs.append(f"{key}: 서로 다른 보기 5개 필요")
        return errs
    if type(ans) is not int or ans not in range(1, 6):
        errs.append(f"{key}: 정답 번호 오류")
        return errs
    a = ans - 1
    if neg and kind not in NEG_OK:
        errs.append(f"{key}: 부정형 발문은 {NEG_OK} 유형만")
    if kind == "틀린 설명" and not neg:
        errs.append(f"{key}: '틀린 설명'인데 발문에 부정어 없음")
    if kind == "옳은 설명" and neg:
        errs.append(f"{key}: '옳은 설명'인데 발문이 부정형")
    if not stem.strip() or not q.get("explain"):
        errs.append(f"{key}: 발문·해설 필요")
    if re.search(r"[①②③④⑤]|[1-5]번\s*(?:보기|선지)|보기\s*[1-5]", q.get("explain", "")):
        errs.append(f"{key}: 해설에 보기 번호 참조 금지")
    quotes = q.get("quotes", [])
    if not 1 <= len(quotes) <= 6:
        errs.append(f"{key}: 근거 1~6개 필요")
    home = "unit" + q["key"][1:] if q["key"].startswith("u") else "webzine-" + q["key"][1:]
    if quotes and quotes[0]["doc"] != home:
        errs.append(f"{key}: 첫 근거는 {home} 지면이어야 함")
    for r in quotes:
        meta = BASE / "ebook" / r["doc"] / "meta.json"
        if not meta.exists() or type(r["p"]) is not int or not 1 <= r["p"] <= json.loads(meta.read_text())["pages"]:
            errs.append(f"{key}: e-book 지면 없음 {r['doc']} p.{r['p']}")
            continue
        errs += quote_errors(pages, key, r["doc"], r["p"], r["text"])

    truth, sts = q.get("truth"), statements(q.get("passage"))
    want = not neg   # 찾는 진술: 옳은 것(True) 또는 옳지 않은 것(False)
    if kind in ("개수 판단", "복합 보기"):
        letters = [x for x, _ in sts]
        if len(sts) not in (4, 5) or letters != list("ㄱㄴㄷㄹㅁ"[:len(sts)]):
            errs.append(f"{key}: passage에 ㄱ.부터 차례로 진술 4~5개 필요")
            return errs
        if not isinstance(truth, list) or len(truth) != len(sts) or not all(isinstance(t, bool) for t in truth):
            errs.append(f"{key}: truth에 진술마다 True/False 필요")
            return errs
        false_letters = [x for x, t in zip(letters, truth) if not t]
        missing_expl = [x for x in false_letters if x not in q.get("explain", "")]
        if missing_expl:
            errs.append(f"{key}: 해설에 틀린 진술 {','.join(missing_expl)}의 원문 표현 필요")
        target = {x for x, t in zip(letters, truth) if t == want}
        if kind == "개수 판단":
            if choices not in COUNT_SETS:
                errs.append(f"{key}: 개수 판단 보기는 {COUNT_SETS[0]} 또는 {COUNT_SETS[1]}")
            elif choices[a] != f"{len(target)}개":
                errs.append(f"{key}: truth로 센 개수 {len(target)}개 ≠ 정답 보기 {choices[a]}")
        else:
            sets = [set(re.findall(r"[ㄱ-ㅎ]", c)) for c in choices]
            if any(not s or not s <= set(letters) for s in sets):
                errs.append(f"{key}: 복합 보기 보기는 passage의 ㄱ·ㄴ… 조합이어야 함")
            elif sets[a] != target or sets.count(target) != 1:
                errs.append(f"{key}: truth로 정한 답 {','.join(sorted(target))} ≠ 정답 보기 {choices[a]}")
            else:
                for x in letters:
                    n = sum(x in s for s in sets)
                    if n == 5:
                        errs.append(f"{key}: 진술 {x}가 모든 보기에 있음 (판단할 필요 없음)")
                if centroid_is_answer([tuple(x in s for x in letters) for s in sets], a):
                    errs.append(f"{key}: 보기 다수결(겹침이 가장 많은 보기)로 정답 추론 가능 — 오답 보기 구성 바꾸기")
        tx = [s for (_, s), t in zip(sts, truth) if t]
        fx = [s for (_, s), t in zip(sts, truth) if not t]
        if fx and tx and all(ABS.search(s) for s in fx) and not any(ABS.search(s) for s in tx):
            errs.append(f"{key}: 단정어가 틀린 진술에만 있음")
        if fx and tx and all(NOT.search(s) for s in fx) and not any(NOT.search(s) for s in tx):
            errs.append(f"{key}: 부정어(않·없)가 틀린 진술에만 있음")
    elif kind in ("옳은 설명", "틀린 설명") or (kind == "사례 적용" and truth is not None):
        if not isinstance(truth, list) or len(truth) != 5 or not all(isinstance(t, bool) for t in truth):
            errs.append(f"{key}: truth에 보기마다 True/False 필요")
            return errs
        hits = [i for i, t in enumerate(truth) if t == want]
        if hits != [a]:
            errs.append(f"{key}: truth상 {'옳은' if want else '틀린'} 보기가 정답 하나뿐이어야 함 (truth {truth}, 정답 {ans})")
        others = [c for i, c in enumerate(choices) if i != a]
        if len(choices[a]) > 1.25 * max(len(c) for c in others):
            errs.append(f"{key}: 정답 보기만 유난히 김")
        if kind == "틀린 설명" and ABS.search(choices[a]) and not any(ABS.search(c) for c in others):
            errs.append(f"{key}: 단정어가 정답(틀린 보기)에만 있음")
        if kind == "틀린 설명" and NOT.search(choices[a]) and not any(NOT.search(c) for c in others):
            errs.append(f"{key}: 부정어(않·없)가 정답(틀린 보기)에만 있음")
        if kind == "옳은 설명" and not ABS.search(choices[a]) and sum(bool(ABS.search(c)) for c in others) >= 2:
            errs.append(f"{key}: 단정어가 오답 보기에만 몰려 있음")
    elif kind == "빈칸 짝짓기":
        labels = [x for x in LABELS if f"({x})" in q.get("passage", "")]
        if len(labels) < 2:
            errs.append(f"{key}: passage에 (가)(나)… 빈칸 2개 이상 필요")
        else:
            parsed = [blanks(c) for c in choices]
            if any(sorted(p) != sorted(labels) for p in parsed):
                errs.append(f"{key}: 보기마다 {''.join('(' + x + ')' for x in labels)} 모두 필요")
            elif centroid_is_answer([tuple(p[x] for x in labels) for p in parsed], a):
                errs.append(f"{key}: 보기 다수결(겹침이 가장 많은 보기)로 정답 추론 가능 — 오답 보기 구성 바꾸기")
    elif kind == "순서 배열":
        letters = [x for x, _ in sts]
        orders = [re.findall(r"[ㄱ-ㅎ]", c) for c in choices]
        if len(letters) < 4 or any(sorted(o) != sorted(letters) or "→" not in c for o, c in zip(orders, choices)):
            errs.append(f"{key}: 순서 배열은 진술 4개 이상, 보기는 그 진술 전부를 → 로 나열")
        elif centroid_is_answer([tuple(o) for o in orders], a):
            errs.append(f"{key}: 보기 다수결(겹침이 가장 많은 보기)로 정답 추론 가능 — 오답 보기 구성 바꾸기")
    elif kind == "사례 적용" and not q.get("passage"):
        errs.append(f"{key}: 사례 적용은 passage에 사례 필요")
    return errs


def check_module(name, items):
    errs = []
    sets, target, nos = MODULES[name]
    by = Counter(q.get("key") for q in items)
    for s in sets:
        if name in NEWS and by[s] != target:
            errs.append(f"{name}: {s} {by[s]}문항 (호마다 {target}문항)")
        if name in TEXT and not target - 2 <= by[s] <= target + 3:
            errs.append(f"{name}: {s} {by[s]}문항 (목표 {target}±2)")
    extra = set(by) - set(sets)
    if extra:
        errs.append(f"{name}: 범위 밖 세트 {extra}")
    for q in items:
        m = re.search(r"-(\d{3})$", q.get("id", ""))
        if m and int(m.group(1)) not in nos:
            errs.append(f"{q['id']}: 이 파일의 번호 범위 {nos.start}~{nos.stop - 1} 밖")
    n = len(items)
    if not n:
        return errs
    pos = Counter(q.get("answer") for q in items)
    lo, hi = n / 5 - max(2, math.ceil(n * .07)), n / 5 + max(2, math.ceil(n * .07))
    bad = {k: pos[k] for k in range(1, 6) if not lo <= pos[k] <= hi}
    if bad:
        errs.append(f"{name}: 정답 번호 쏠림 {dict(sorted(pos.items()))} (번호마다 {lo:.0f}~{hi:.0f}개)")
    f = Counter(q.get("format") for q in items)
    need = {"개수 판단": math.ceil(n * .2), "복합 보기": math.ceil(n * .2), "빈칸 짝짓기": math.ceil(n * .1)}
    for k, v in need.items():
        if f[k] < v:
            errs.append(f"{name}: {k} {f[k]}개 (최소 {v}개)")
    if f["옳은 설명"] + f["틀린 설명"] > math.floor(n * .3):
        errs.append(f"{name}: 옳은 설명+틀린 설명 {f['옳은 설명'] + f['틀린 설명']}개 (최대 {math.floor(n * .3)}개)")
    if f["틀린 설명"] > math.floor(n * .15):
        errs.append(f"{name}: 틀린 설명 {f['틀린 설명']}개 (최대 {math.floor(n * .15)}개)")
    return errs


def verify(found, pages=None):
    if pages is None:
        pages, _ = load_sources(BASE)
    _, sections = exam_check.load()
    errs, ids, stems = [], Counter(), Counter()
    for name, items in found.items():
        errs += check_module(name, items)
        for q in items:
            ids[q.get("id")] += 1
            stems[re.sub(r"[\s*]", "", q.get("q", "") + q.get("passage", ""))] += 1
            errs += check_item(q, sections, pages)
    errs += [f"{k}: ID 중복" for k, v in ids.items() if v > 1]
    errs += [f"발문 중복: {k[:40]}" for k, v in stems.items() if v > 1]
    return errs


if __name__ == "__main__":
    names = sys.argv[1:] or list(MODULES)
    unknown = [x for x in names if x not in MODULES]
    if unknown:
        sys.exit(f"모르는 모듈: {unknown} (가능: {list(MODULES)})")
    found = load(names)
    errs = verify(found)
    items = [q for v in found.values() for q in v]
    print(f"{len(items)}문항 ({', '.join(f'{k} {len(v)}' for k, v in found.items())})")
    print(f"유형 {dict(Counter(q.get('format') for q in items))}")
    print(f"정답 {dict(sorted(Counter(q.get('answer') for q in items).items()))}")
    print("\n".join(errs) if errs else "✅ 원문 대조·형식·정답 일관성·찍기 방지 검사 통과")
    sys.exit(1 if errs else 0)
