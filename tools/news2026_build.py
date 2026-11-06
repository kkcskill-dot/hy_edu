"""별도 소식지 심화 학습: 수작업 문항을 원문 검증 후 퀴즈·모의고사로 발행."""
import copy
import json
import random
import re
from collections import Counter
from itertools import zip_longest
from pathlib import Path

from ai2026_core import ITEMS as CORE
from ai2026_expanded import ITEMS as EXPANDED
from news2026_first_half import ITEMS as FIRST, COVERAGE as FIRST_COVERAGE
from news2026_second_half import ITEMS as SECOND, COVERAGE as SECOND_COVERAGE
from kichul_build import load_sources
from webzine_build import missing

TOPICS = {
    "prism": "의료기기정보 통합 플랫폼 · 프리즘",
    "aicc": "미래형 스마트 고객센터 · AICC",
    "yaid": "AI 에이전트 플랫폼 · Y-Aid",
    "clinical": "진료·기록 지원 AI",
    "operations": "업무·데이터 활용",
    "strategy": "AI 전환·연구",
    "care": "진료·환자안전",
    "research": "연구·성과 해석",
    "education": "교육·간호",
    "projects": "주요 사업·운영",
    "collaboration": "협력·지역사회",
    "values": "의료원 방향·제도",
}
FORMATS = ("옳은 설명", "틀린 설명", "명칭·기능", "사례 적용", "비교·연결", "복합 보기")
OUT = Path("practice/news2026")
HEADER = "<!-- tools/news2026_build.py에서 생성. 문항 수정: tools/ai2026_core.py · tools/ai2026_expanded.py · tools/news2026_first_half.py · tools/news2026_second_half.py -->\n"


def verify(base, items):
    pages, _ = load_sources(base)
    errors, ids, stems = [], set(), set()
    for q in items:
        key = q.get("id", "ID 없음")
        if key in ids or q.get("q") in stems:
            errors.append(f"{key}: ID 또는 발문 중복")
        ids.add(key)
        stems.add(q.get("q"))
        if not re.fullmatch(r"(?:ai26-[a-z]+|news26-\d{3})-\d{2}", key):
            errors.append(f"{key}: 문항 ID 형식 오류")
        if q.get("topic") not in TOPICS or q.get("difficulty") not in ("중", "상") or q.get("format") not in FORMATS:
            errors.append(f"{key}: 주제·난이도·유형 오류")
        if q.get("unit") != 8 or q.get("type") != "mc":
            errors.append(f"{key}: 문항 형식 오류")
        choices = q.get("choices", [])
        if len(choices) != 5 or len(set(choices)) != 5 or not all(isinstance(c, str) and c.strip() for c in choices):
            errors.append(f"{key}: 서로 다른 5개 보기 필요")
        if type(q.get("answer")) is not int or not 1 <= q["answer"] <= 5:
            errors.append(f"{key}: 정답 번호 오류")
        if not q.get("q") or not q.get("explain") or not q.get("quotes"):
            errors.append(f"{key}: 발문·해설·근거 필수")
        # 보기 순서가 바뀌어도 해설의 의미가 유지되어야 한다.
        if re.search(r"[①②③④⑤]|[1-5]번\s*보기", q.get("explain", "")):
            errors.append(f"{key}: 해설에서 보기 번호 대신 내용을 지칭해야 함")
        for ref in q.get("quotes", []):
            doc = ref.get("doc", "")
            if not re.fullmatch(r"webzine-\d{3}", doc) or not isinstance(ref.get("p"), int) or not ref.get("text"):
                errors.append(f"{key}: 근거 형식 오류")
                continue
            errors.extend(f"{key}: {doc} p.{ref['p']} 원문 불일치 → {s}" for s in missing(pages, int(doc[-3:]), ref["p"], ref["text"]))
            meta_path = base / "ebook" / doc / "meta.json"
            if not meta_path.exists() or not 1 <= ref["p"] <= json.loads(meta_path.read_text())["pages"]:
                errors.append(f"{key}: e-book 근거 페이지 없음")
    expected = {k: 12 if k in ("prism", "aicc", "yaid") else 8 if k in ("clinical", "operations", "strategy") else 10 for k in TOPICS}
    if Counter(q.get("topic") for q in items) != expected:
        errors.append("주제별 문항 수: AI 핵심 3주제 각 12개, AI 확장 3주제 각 8개, 소식지 6주제 각 10개 필요")
    if sum(q.get("difficulty") == "상" for q in items) < len(items) // 2:
        errors.append("상 난이도 문항이 절반 이상이어야 함")
    if set(q.get("format") for q in items) != set(FORMATS):
        errors.append("6가지 문항 유형을 모두 포함해야 함")
    coverage = FIRST_COVERAGE + SECOND_COVERAGE
    if Counter(x['issue'] for x in coverage) != Counter(range(977, 995)):
        errors.append("18개 호 전체 검토 기록 필요")
    for issue in range(977, 995):
        if sum(any(r['doc'] == f'webzine-{issue}' for r in q['quotes']) for q in items) < 2:
            errors.append(f"{issue}호: 근거 문항 최소 2개 필요")
    return errors


def mock_questions(items, round_no):
    """주제별 배분 후 난이도를 균등하게 맞춘다. 4회에 120문항을 한 번씩 사용."""
    sets = [[] for _ in range(4)]
    planned = [0] * 4
    for topic in TOPICS:
        questions = sorted((q for q in items if q["topic"] == topic), key=lambda q: (q["difficulty"], q["id"]))
        quotas = [len(questions) // 4] * 4
        for i in sorted(range(4), key=lambda i: (planned[i], i))[:len(questions) % 4]:
            quotas[i] += 1
        counts = [0] * 4
        for q in questions:
            eligible = [i for i in range(4) if counts[i] < quotas[i]]
            chosen = min(eligible, key=lambda i: (counts[i], sum(x['difficulty'] == '상' for x in sets[i]), len(sets[i]), i))
            sets[chosen].append(q)
            counts[chosen] += 1
        planned = [a + b for a, b in zip(planned, quotas)]
    # 동일 주제의 상/중 문항 교환으로 주제 수를 보존하면서 회차별 난이도 차이를 1 이내로 맞춤.
    while True:
        highs = [sum(q['difficulty'] == '상' for q in group) for group in sets]
        high, low = highs.index(max(highs)), highs.index(min(highs))
        if highs[high] - highs[low] <= 1:
            break
        pair = next(((a, b) for a in sets[high] for b in sets[low]
                     if a['topic'] == b['topic'] and a['difficulty'] == '상' and b['difficulty'] == '중'), None)
        if pair is None:
            raise ValueError("모의고사 난이도 균등 배분 실패")
        a, b = pair
        ai, bi = sets[high].index(a), sets[low].index(b)
        sets[high][ai], sets[low][bi] = b, a
    groups = [[q for q in sets[round_no - 1] if q['topic'] == topic] for topic in TOPICS]
    selected = [copy.deepcopy(q) for row in zip_longest(*groups) for q in row if q]
    # 고정 모의고사는 재접속 시 동일 문항·보기. 정답 위치는 1~5에 고르게 배치한다.
    rng = random.Random(202600 + round_no)
    positions = list(range(5)) * (len(selected) // 5)
    rng.shuffle(positions)
    for q, position in zip(selected, positions):
        answer = q["choices"].pop(q["answer"] - 1)
        rng.shuffle(q["choices"])
        q["choices"].insert(position, answer)
        q["answer"] = position + 1
    return selected


def build(base):
    items = CORE + EXPANDED + FIRST + SECOND
    errors = verify(base, items)
    if errors:
        raise ValueError("소식지 심화 문제 검증 실패:\n" + "\n".join(errors))
    out = base / OUT
    out.mkdir(parents=True, exist_ok=True)

    def write(name, value):
        text = json.dumps(value, ensure_ascii=False, indent=2) + "\n" if isinstance(value, dict) else HEADER + value
        (out / name).write_text(text, encoding="utf-8")

    write("bank.json", {"id": "news2026-bank-v1", "title": "2026 소식지 심화 퀴즈", "filterable": True,
                        "size": 10, "topics": TOPICS, "topicLabels": TOPICS, "pool": items})
    counts = Counter(q["difficulty"] for q in items)
    topic_rows = "\n".join(f"| {label} | {sum(q['topic'] == key for q in items)}문항 |" for key, label in TOPICS.items())
    mock_cards = '\n'.join(f'<a class="course-card" href="#/practice/news2026/mock{n}.md"><span class="card-tag">12개 주제 종합 · 30문항</span><h4>심화 모의고사 {n}회</h4><p>기능·조건 판별과 비교·사례 적용을 점검합니다. 다른 회차와 중복 없이 구성했습니다.</p><div class="card-footer">{n}회 응시 ➔</div></a>' for n in range(1, 5))
    write("README.md", f'''<div class="lecture-header-box">
  <span class="lecture-badge">신규 문제 · 별도 학습</span>
  <h2>2026 소식지 심화문제</h2>
  <p>18개 호 전체에서 고른 12개 주제 · 5지선다 {len(items)}문항. AI·디지털부터 진료·연구·교육·운영·협력·제도까지 기존 학습과 별도로 연습합니다.</p>
</div>

[소식지 기본 모의고사](#/practice/news-basic/README.md)에서는 원문 표현 중심의 기본 객관식 270문항을 먼저 연습할 수 있습니다.

## 학습 방법 선택

<div class="course-grid">
  <a class="course-card" href="#/practice/news2026/quiz.md"><span class="card-tag">주제 · 난이도 · 유형 선택</span><h4>주제별 심화 퀴즈</h4><p>중 {counts['중']}문항 · 상 {counts['상']}문항. 10문항씩 풀거나 선택한 범위를 모두 풀 수 있습니다.</p><div class="card-footer">퀴즈 시작 ➔</div></a>
  {mock_cards}
</div>

## 출제 범위

| 주제 | 문항 수 |
| --- | ---: |
{topic_rows}

- **중**: 서비스 명칭과 기능, 원문에서 제시한 운영 방식과 범위를 구별합니다.
- **상**: 여러 조건을 함께 판단하거나, 사례·복합 보기·서로 다른 서비스를 비교합니다.
- **문항 유형**: 옳은 설명 · 틀린 설명 · 명칭·기능 · 사례 적용 · 비교·연결 · 복합 보기. 모두 정답을 하나 고릅니다.
- 채점 후 정답 해설과 **근거 소식지 호수·쪽수**를 확인할 수 있습니다.
- [18개 호별 출제 범위와 선정 주제](#/practice/news2026/coverage.md)를 확인하세요.

## 출제 기준과 기록

2026년 연세의료원 소식지 제977~994호 전체를 검토해 출제 가치가 있는 내용을 골라 작성한 학습용 창작 문제입니다. **각 기사 발행 당시의 내용**을 기준으로 하며, 운영 중인 기능과 향후 계획, 연구 결과와 해석의 범위를 구분합니다. 사례형은 해당 사실을 적용한 가상 업무 상황입니다.

퀴즈와 모의고사는 위 120문항을 공유합니다. 모의고사 1~4회끼리는 문항이 겹치지 않으며 각 회차의 주제·난이도·정답 위치를 고르게 배분했습니다. 새 문제의 응답·점수 기록은 기존 학습과 분리하여 이 기기에 저장하며, 퀴즈는 선택 범위별로 이어 풀 수 있습니다.

[소식지 주제별 원문 학습](#/summary/10_2026_소식지_주제별_모아보기.md) · [기존 학습 대시보드](#/README.md)
''')
    write("quiz.md", '''<div class="lecture-header-box">
  <span class="lecture-badge">2026 소식지 · 주제별 심화 퀴즈</span>
  <h2>주제별 심화 퀴즈</h2>
  <p>주제·난이도·유형을 선택해 10문항씩 연습하세요. 모든 문항은 정답이 하나입니다. 채점 후 해설과 근거 지면을 확인합니다.</p>
</div>

<div class="note-key"><p>기사 발행 당시의 내용이 기준입니다. <b>옳은 것 / 틀린 것</b>을 구별해 읽으세요. 상 난이도는 조건 비교·사례 적용·복합 판단을 포함합니다. 선택 범위별 응답과 기록이 저장됩니다.</p></div>

<div class="mock-exam" data-src="practice/news2026/bank.json"></div>

<div class="lesson-footer-nav"><a class="complete-btn secondary" href="#/practice/news2026/README.md">심화문제 메뉴</a><a class="complete-btn" href="#/practice/news2026/mock1.md">심화 모의고사 1회 ➔</a></div>
''')
    for n in range(1, 5):
        questions = mock_questions(items, n)
        write(f"mock{n}.json", {"id": f"news2026-mock{n}-v1", "title": f"2026 소식지 심화 모의고사 {n}회",
                              "topicLabels": TOPICS, "questions": questions})
        write(f"mock{n}.md", f'''<div class="lecture-header-box">
  <span class="lecture-badge">2026 소식지 · 별도 모의고사 {n}회</span>
  <h2>심화 모의고사 {n}회</h2>
  <p>12개 주제 종합 30문항 · 모든 문항은 5지선다, 정답 하나입니다. 채점 후 주제별 성적·해설·근거 지면을 확인하세요.</p>
</div>

<div class="note-key"><p>각 기사 발행 당시의 내용과 계획을 기준으로 답하세요. 주제별 퀴즈와 문항을 공유하며 1~4회끼리는 중복이 없습니다. 고른 답과 채점 기록은 기존 모의고사와 별도로 이 기기에 저장됩니다.</p></div>

<div class="mock-exam" data-src="practice/news2026/mock{n}.json"></div>

<div class="lesson-footer-nav"><a class="complete-btn secondary" href="#/practice/news2026/README.md">심화문제 메뉴</a><a class="complete-btn" href="#/practice/news2026/{'mock' + str(n + 1) if n < 4 else 'quiz'}.md">{'심화 모의고사 ' + str(n + 1) + '회' if n < 4 else '주제별 퀴즈'} ➔</a></div>
''')
    coverage = sorted(FIRST_COVERAGE + SECOND_COVERAGE, key=lambda x: x['issue'])
    rows = []
    for entry in coverage:
        no = entry['issue']
        qs = [q for q in items if any(r['doc'] == f'webzine-{no}' for r in q['quotes'])]
        pages = sorted({r['p'] for q in qs for r in q['quotes'] if r['doc'] == f'webzine-{no}'})
        links = ' · '.join(f'<a class="src" href="reader.html?doc=webzine-{no}&amp;p={p}">p.{p}</a>' for p in pages)
        rows.append(f"| {no}호 | {' · '.join(TOPICS.get(t, t) for t in entry['selected_topics'])} | {len(qs)} | {links} |")
    write('coverage.md', '''# 2026 소식지 전체 검토 · 출제 범위

제977~994호 **18개 호 전체**의 기사목록을 검토하고, 선정한 주제는 해당 원문 지면과 대조해 출제했습니다. 단순 행사 개최·기관명·수상자 이름보다 사업의 목적·구성·조건·차이·단계와 연구 근거의 의미에 중점을 둡니다.

아래는 호별로 선정한 대표 주제와 실제 문항 근거입니다. 하나의 문항이 여러 호를 비교할 수 있으므로 근거 문항 수의 합은 전체 문항 수와 다를 수 있습니다. 모든 기사를 한 문항씩 출제한 것은 아니며, 출제한 내용은 해당 호 발행 당시 기준입니다.

| 소식지 | 대표 선정 주제 | 근거 문항 수 | 원문 지면 |
| --- | --- | ---: | --- |
''' + '\n'.join(rows) + '\n\n[심화문제 메뉴](#/practice/news2026/README.md) · [소식지 전 권 색인](#/original/webzine_2026_전체색인.md)\n')
    print(f"🧠 소식지 심화: 18개 호 · 원문 검증 {len(items)}문항 · 모의고사 4회 (각 30문항)")


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
