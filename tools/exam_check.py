"""교본 문항(tools/exam_u0N*.py) 원문 대조·형식 검증.

사용: python3 tools/exam_check.py            # 전체
      python3 tools/exam_check.py exam_u04a  # 파일 하나
"""
import importlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exam_schema import FORMATS  # noqa: E402
from kichul_build import load_sources, norm  # noqa: E402
import kichul_items  # noqa: E402
import quiz_items  # noqa: E402

BASE = Path(__file__).resolve().parents[1]
MODULES = ("exam_u01", "exam_u02", "exam_u03", "exam_u04a", "exam_u04b",
           "exam_u05", "exam_u06a", "exam_u06b", "exam_u07")
# 문제풀이 공간 문항에서 새로 확인한 OCR 오타 (쪽 이미지 기준) — 문서, 쪽 → (OCR, 실제)
OCR_FIX = {("unit06", 3): [("제5창", "제5장")], ("unit07", 5): [("항복", "항목")], ("unit07", 15): [("업무정치", "업무정지")]}
IMG_OK = {}
for src in (quiz_items, kichul_items):
    for k, v in src.OCR_FIX.items():
        OCR_FIX.setdefault(k, []).extend(v)
    for k, v in src.IMG_OK.items():
        IMG_OK.setdefault(k, []).extend(v)


def wnorm(s):
    return norm(s).replace("-", "").replace("–", "").replace("~", "∼").replace("∼", "~")


def page_text(pages, doc, p):
    src = pages.get((doc, p))
    if src is None:
        return None
    for wrong, right in OCR_FIX.get((doc, p), []):
        src = src.replace(wrong, right)
    return wnorm(src)


def load(names=MODULES):
    items, sections = [], {}
    for name in names:
        try:
            mod = importlib.import_module(name)
        except ModuleNotFoundError:
            continue
        items += mod.ITEMS
        unit = mod.ITEMS[0]["unit"] if mod.ITEMS else None
        if unit:
            sections.setdefault(unit, [])
            sections[unit] += [s for s in mod.SECTIONS if s not in sections[unit]]
    return items, sections


def verify(items, sections, pages=None):
    if pages is None:
        pages, _ = load_sources(BASE)
    errors, ids, stems = [], set(), set()
    for q in items:
        key = q.get("id", "ID 없음")
        stem = re.sub(r"[\s*]", "", q.get("q", ""))
        if key in ids:
            errors.append(f"{key}: ID 중복")
        if stem in stems:
            errors.append(f"{key}: 발문 중복")
        ids.add(key)
        stems.add(stem)
        unit = q.get("unit")
        if not re.fullmatch(rf"ex-u{unit:02d}-\d{{3}}", key):
            errors.append(f"{key}: ID 형식 오류")
        if q.get("section") not in sections.get(unit, []):
            errors.append(f"{key}: SECTIONS에 없는 소단원 {q.get('section')}")
        if q.get("format") not in FORMATS:
            errors.append(f"{key}: 유형 오류 {q.get('format')}")
        neg = re.search(r"틀린|옳지 않은|아닌 것|해당하지 않는|포함되지 않는|없는 것", q.get("q", ""))
        if neg and q.get("format") != "틀린 설명":
            errors.append(f"{key}: 부정형 발문은 유형 '틀린 설명'")
        if q.get("format") == "틀린 설명" and not neg:
            errors.append(f"{key}: '틀린 설명' 유형인데 발문에 부정어 없음")
        choices = q.get("choices", [])
        if len(choices) != 5 or len(set(map(str.strip, choices))) != 5 or not all(isinstance(c, str) and c.strip() for c in choices):
            errors.append(f"{key}: 서로 다른 보기 5개 필요")
        if type(q.get("answer")) is not int or q["answer"] not in range(1, 6):
            errors.append(f"{key}: 정답 번호 오류")
        if not stem or not q.get("explain") or not 1 <= len(q.get("quotes", [])) <= 3:
            errors.append(f"{key}: 발문·해설·근거(1~3개) 필요")
        if re.search(r"[①②③④⑤]|[1-5]번\s*(?:보기|선지)|보기\s*[1-5]", q.get("explain", "")):
            errors.append(f"{key}: 해설에 보기 번호 참조 금지")
        for ref in q.get("quotes", []):
            doc, p = ref["doc"], ref["p"]
            src = page_text(pages, doc, p)
            if src is None:
                errors.append(f"{key}: {doc} p.{p} 원문 쪽 없음")
                continue
            meta = BASE / "ebook" / doc / "meta.json"
            if not meta.exists() or not 1 <= p <= json.loads(meta.read_text())["pages"]:
                errors.append(f"{key}: e-book 지면 없음 {doc} p.{p}")
            ok = {wnorm(x) for x in IMG_OK.get((doc, p), [])}
            for seg in ref["text"].split(" … "):
                if wnorm(seg) and wnorm(seg) not in src and wnorm(seg) not in ok:
                    errors.append(f"{key}: {doc} p.{p} 원문에 없는 조각 → {seg}")
    return errors


if __name__ == "__main__":
    names = sys.argv[1:] or MODULES
    items, sections = load(names)
    errs = verify(items, sections)
    from collections import Counter
    print(f"{len(items)}문항 · 유형 {dict(Counter(q['format'] for q in items))} · 정답 {dict(sorted(Counter(q['answer'] for q in items).items()))}")
    print("\n".join(errs) if errs else "✅ 원문 대조·형식 검증 통과")
    sys.exit(1 if errs else 0)
