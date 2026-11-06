"""18개 호의 원문 표현 중심 기본 문제와 9회 모의고사를 발행한다."""
import copy
import json
import random
import re
from collections import Counter
from html import escape
from pathlib import Path

from kichul_build import load_sources
from news_basic_schema import TOPICS, FORMATS
from practice_types import practice_type
from webzine_build import missing

OUT = Path("practice/news-basic")
ISSUES = range(977, 995)
ROUNDS = 9
SIZE = 30
HEADER = "<!-- tools/news_basic_build.py에서 생성. 문항 수정: tools/news_basic_977_982.py · tools/news_basic_983_988.py · tools/news_basic_989_994.py -->\n"


def load_items():
    from news_basic_977_982 import ITEMS as first
    from news_basic_983_988 import ITEMS as middle
    from news_basic_989_994 import ITEMS as last
    return first + middle + last


def verify(base, items):
    pages, _ = load_sources(base)
    errors, ids, stems = [], set(), set()
    issues = Counter()
    for q in items:
        key = q.get("id", "ID 없음")
        stem = re.sub(r"[\s*]", "", q.get("q", ""))
        if key in ids or stem in stems:
            errors.append(f"{key}: ID 또는 발문 중복")
        ids.add(key)
        stems.add(stem)
        if not re.fullmatch(r"basic26-\d{3}-\d{2}", key):
            errors.append(f"{key}: ID 형식 오류")
        if q.get("type") != "mc" or practice_type(q) != "mc" or q.get("unit") != 8:
            errors.append(f"{key}: 일반 객관식만 허용")
        if q.get("difficulty") != "기본" or q.get("format") not in FORMATS or q.get("topic") not in TOPICS:
            errors.append(f"{key}: 기본 난이도·유형·주제 확인 필요")
        if q.get("passage"):
            errors.append(f"{key}: 기본 모의고사에는 복합 보기를 사용하지 않음")
        choices = q.get("choices", [])
        if len(choices) != 5 or len(set(choices)) != 5 or not all(isinstance(c, str) and c.strip() for c in choices):
            errors.append(f"{key}: 서로 다른 보기 5개 필요")
        if type(q.get("answer")) is not int or q["answer"] not in range(1, 6):
            errors.append(f"{key}: 정답 번호 오류")
        if not stem or not q.get("tag") or not q.get("explain") or len(q.get("quotes", [])) != 1:
            errors.append(f"{key}: 발문·주제·해설·단일 지면 근거 필요")
        if re.search(r"[①②③④⑤]|[1-5]번\s*(?:보기|선지)", q.get("explain", "")):
            errors.append(f"{key}: 해설의 보기 번호 참조 금지")
        for ref in q.get("quotes", []):
            doc, page = ref.get("doc", ""), ref.get("p")
            if not re.fullmatch(r"webzine-\d{3}", doc) or type(page) is not int or not ref.get("text"):
                errors.append(f"{key}: 근거 형식 오류")
                continue
            issue = int(doc[-3:])
            issues[issue] += 1
            if issue not in ISSUES or not key.startswith(f"basic26-{issue}-"):
                errors.append(f"{key}: 호수·ID 불일치")
            errors.extend(f"{key}: {doc} p.{page} 원문 불일치 → {text}"
                          for text in missing(pages, issue, page, ref["text"]))
            meta = base / "ebook" / doc / "meta.json"
            if not meta.exists() or not 1 <= page <= json.loads(meta.read_text())["pages"]:
                errors.append(f"{key}: 원문 지면 없음")
    if issues != Counter({issue: 15 for issue in ISSUES}):
        errors.append(f"18개 호마다 15문항 필요: {dict(issues)}")
    if set(q.get("topic") for q in items) != set(TOPICS):
        errors.append("7개 주제를 모두 포함해야 함")
    if set(q.get("format") for q in items) != set(FORMATS):
        errors.append("기본 문항 유형 4종을 모두 포함해야 함")
    return errors


def mock_sets(items):
    """회차마다 전 18개 호를 포함하며, 270문항을 한 번씩 배정한다."""
    groups = [[] for _ in range(ROUNDS)]
    topics = [Counter() for _ in groups]
    formats = [Counter() for _ in groups]
    rng = random.Random(20261106)
    for issue_index, issue in enumerate(ISSUES):
        questions = sorted((q for q in items if q["id"].startswith(f"basic26-{issue}-")), key=lambda q: q["id"])
        rng.shuffle(questions)
        # 각 호는 6회차에 두 문항, 3회차에 한 문항. 18개 호를 돌면 회차당 30문항.
        quotas = [2 if (n - issue_index) % ROUNDS < 6 else 1 for n in range(ROUNDS)]
        for q in questions:
            candidates = [n for n in range(ROUNDS) if quotas[n]]
            chosen = min(candidates, key=lambda n: (topics[n][q["topic"]], formats[n][q["format"]], len(groups[n]), n))
            groups[chosen].append(copy.deepcopy(q))
            topics[chosen][q["topic"]] += 1
            formats[chosen][q["format"]] += 1
            quotas[chosen] -= 1
    for n, questions in enumerate(groups, 1):
        if len(questions) != SIZE:
            raise ValueError(f"기본 {n}회 문항 수 오류: {len(questions)}")
        rng = random.Random(2026270 + n)
        rng.shuffle(questions)
        positions = list(range(5)) * (SIZE // 5)
        rng.shuffle(positions)
        for q, position in zip(questions, positions):
            correct = q["choices"].pop(q["answer"] - 1)
            rng.shuffle(q["choices"])
            q["choices"].insert(position, correct)
            q["answer"] = position + 1
    return groups


def build(base):
    items = load_items()
    errors = verify(base, items)
    if errors:
        raise ValueError("소식지 기본 문제 검증 실패:\n" + "\n".join(errors))
    out = base / OUT
    out.mkdir(parents=True, exist_ok=True)

    def write(name, value):
        text = json.dumps(value, ensure_ascii=False, indent=2) + "\n" if isinstance(value, dict) else HEADER + value
        (out / name).write_text(text, encoding="utf-8")

    cards = "\n".join(f'''  <a class="course-card" href="#/practice/news-basic/mock{n}.md">
    <div><span class="card-tag">기본 · 5지선다 30문항</span><h4>소식지 기본 모의고사 {n}회</h4><p>18개 호에서 고르게 출제했습니다. 다른 회차와 중복 없이 원문 내용을 확인하세요.</p></div>
    <div class="card-footer"><span>원문 해설 · 이어 풀기</span><span>{n}회 응시 ➔</span></div>
  </a>''' for n in range(1, ROUNDS + 1))
    topic_counts = Counter(q["topic"] for q in items)
    rows = "\n".join(f"| {label} | {topic_counts[topic]}문항 |" for topic, label in TOPICS.items())
    write("README.md", f'''<div class="lecture-header-box">
  <span class="lecture-badge">2026 소식지 · 원문 표현 중심</span>
  <h2>소식지 기본 모의고사</h2>
  <p>제977~994호 전체 · 270문항 · 30문항씩 9회. 소식지에 나온 명칭·목적·기능·구성을 익히는 기본 객관식입니다.</p>
</div>

<div class="note-key"><p>소식지 문구를 최대한 살려 <b>옳은 내용, 틀린 내용, 주요 기능과 명칭</b>을 묻습니다. 한 기사에 나온 내용을 직접 확인하는 수준이며, 채점 후 해설과 소식지 원문·호수·쪽수를 볼 수 있습니다.</p></div>

## 회차 선택

<div class="course-grid">
{cards}
</div>

## 출제 범위

18개 호에서 각 15문항을 만들었습니다. 매 회차에 18개 호가 모두 포함되며, **1~9회끼리는 문항이 겹치지 않습니다.** AI·디지털 외에도 진료·연구·교육·사업·협력·비전 내용을 함께 다룹니다.

| 주제 | 문항 수 |
| --- | ---: |
{rows}

- 모든 문항은 **정답 하나를 고르는 5지선다**입니다.
- 소식지의 **각 기사 발행 당시 내용**을 기준으로 답하세요.
- 응답과 채점 기록은 회차별로 저장되어 이어 풀 수 있습니다. 기존 학습·심화 모의고사와 기록이 분리됩니다.
- [18개 호별 출제 범위와 원문 지면](#/practice/news-basic/coverage.md)

## 반복 학습

[기본 문제 30문항씩 랜덤 연습](#/practice/news-basic/quiz.md)에서 같은 270문항을 다시 섞어 풀 수 있습니다. [소식지 핵심노트](#/summary/09_2026_소식지_핵심노트.md)로 내용을 확인하거나, 학습 후 [심화문제](#/practice/news2026/README.md)로 이어가세요.
''')
    write("bank.json", {"id": "news-basic-2026-bank-v1", "title": "소식지 기본 문제 랜덤 연습",
                        "size": SIZE, "topicLabels": TOPICS, "pool": items})
    write("quiz.md", '''<div class="lecture-header-box">
  <span class="lecture-badge">2026 소식지 · 기본 문제 반복 학습</span>
  <h2>소식지 기본 문제 랜덤 연습</h2>
  <p>기본 모의고사 9회와 같은 270문항에서 30문항씩 섞어 풉니다. 채점 후 원문 해설을 확인하세요.</p>
</div>

<div class="mock-exam" data-src="practice/news-basic/bank.json"></div>

<div class="lesson-footer-nav"><a class="complete-btn secondary" href="#/practice/news-basic/README.md">기본 모의고사 메뉴</a><a class="complete-btn" href="#/practice/news-basic/mock1.md">기본 모의고사 1회 ➔</a></div>
''')
    for n, questions in enumerate(mock_sets(items), 1):
        write(f"mock{n}.json", {"id": f"news-basic-2026-mock{n}-v1", "title": f"소식지 기본 모의고사 {n}회",
                              "topicLabels": TOPICS, "questions": questions})
        next_path = f"mock{n + 1}" if n < ROUNDS else "quiz"
        next_label = f"기본 모의고사 {n + 1}회" if n < ROUNDS else "기본 문제 랜덤 연습"
        write(f"mock{n}.md", f'''<div class="lecture-header-box">
  <span class="lecture-badge">2026 소식지 · 기본 {n} / 9회</span>
  <h2>소식지 기본 모의고사 {n}회</h2>
  <p>소식지 원문 표현 중심 · 18개 호 종합 30문항 · 5지선다, 정답 하나입니다.</p>
</div>

<div class="note-key"><p><b>옳은 것 / 틀린 것</b>을 구별해 읽으세요. 각 기사 발행 당시 내용을 기준으로 답하며, 채점하면 해설과 원문 지면이 나옵니다. 회차별 답안과 기록이 저장됩니다.</p></div>

<div class="mock-exam" data-src="practice/news-basic/mock{n}.json"></div>

<div class="lesson-footer-nav"><a class="complete-btn secondary" href="#/practice/news-basic/README.md">기본 모의고사 메뉴</a><a class="complete-btn" href="#/practice/news-basic/{next_path}.md">{next_label} ➔</a></div>
''')
    coverage = []
    for issue in ISSUES:
        questions = [q for q in items if q["id"].startswith(f"basic26-{issue}-")]
        topics = " · ".join(TOPICS[t] for t in TOPICS if any(q["topic"] == t for q in questions))
        pages = sorted({r["p"] for q in questions for r in q["quotes"]})
        links = " · ".join(f'<a class="src" href="reader.html?doc=webzine-{issue}&amp;p={p}">p.{p}</a>' for p in pages)
        coverage.append(f"| {issue}호 | {escape(topics)} | {len(questions)} | {links} |")
    write("coverage.md", '''# 소식지 기본 모의고사 · 출제 범위

제977~994호 18개 호 전체의 기사 목록을 검토하고, 선정한 기사의 원문 지면에서 기본 문제를 작성했습니다. 각 호 15문항, 총 270문항입니다. 모든 기사를 한 문항씩 출제한 것은 아니며, 주요 사업·서비스의 명칭·목적·기능·구성을 중심으로 선정했습니다.

문항의 정답과 해설은 해당 기사 발행 당시의 내용에 근거합니다. 원문 표현을 최대한 살렸으며, 질문과 오답 보기는 학습용으로 작성했습니다.

| 소식지 | 출제 주제 | 문항 수 | 원문 지면 |
| --- | --- | ---: | --- |
''' + "\n".join(coverage) + '\n\n[기본 모의고사 메뉴](#/practice/news-basic/README.md) · [소식지 전 권 색인](#/original/webzine_2026_전체색인.md)\n')
    print(f"📝 소식지 기본: 18개 호 · 원문 검증 {len(items)}문항 · 모의고사 {ROUNDS}회 (각 {SIZE}문항)")


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
