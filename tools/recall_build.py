"""기존 O/X와 모든 빈칸(입력형·선택형)을 별도 보관 메뉴에 연결한다."""
import json
from pathlib import Path

from practice_types import practice_type
from quiz_build import UNIT_TITLES

OUT = Path("practice/recall")
GEN = "<!-- tools/recall_build.py에서 생성합니다. 문항은 기존 quiz/*.json을 사용합니다. -->\n"


def widget(src, part, kind=None):
    extra = f' data-type="{kind}"' if kind else ""
    return f'<div class="mock-exam" data-src="{src}" data-part="{part}"{extra}></div>'


def build(base):
    units = {u: json.loads((base / f"quiz/u{u:02d}.json").read_text(encoding="utf-8")) for u in range(1, 8)}
    news = json.loads((base / "quiz/w01.json").read_text(encoding="utf-8"))
    questions = [q for data in [*units.values(), news] for pool in data['parts'].values() for q in pool]
    counts = {kind: sum(practice_type(q) == kind for q in questions) for kind in ('ox', 'blank')}
    out = base / OUT
    out.mkdir(parents=True, exist_ok=True)

    def write(name, text):
        (out / name).write_text(GEN + text, encoding="utf-8")

    write("README.md", f'''<div class="lecture-header-box">
  <span class="lecture-badge">보관 문제 · 선택 학습</span>
  <h2>O/X · 빈칸채우기 보관함</h2>
  <p>교본 7개 단원과 2026 소식지의 O/X·빈칸 문제를 모았습니다. 필요할 때 이 메뉴에서 따로 연습하세요.</p>
</div>

<div class="course-grid">
  <a class="course-card" href="#/practice/recall/ox.md"><span class="card-tag">교본 · 소식지</span><h4>O/X 문제</h4><p>원문과 비교해 맞는 설명과 틀린 설명을 판단합니다. 총 {counts['ox']}문항.</p><div class="card-footer">O/X 열기 ➔</div></a>
  <a class="course-card" href="#/practice/recall/blank.md"><span class="card-tag">직접 입력 · 보기 선택</span><h4>빈칸채우기</h4><p>입력형 빈칸과 숫자·용어를 보기에서 고르는 선택형 빈칸을 모두 보관했습니다. 총 {counts['blank']}문항.</p><div class="card-footer">빈칸채우기 열기 ➔</div></a>
</div>

원래 O/X·입력형 빈칸의 풀이 기록은 그대로 이어집니다. 객관식과 섞여 있던 선택형 빈칸·목록 빈칸은 분리된 범위에서 새로 연습하며, 이전에 저장한 기록을 삭제하지 않습니다.

[학습 대시보드로 돌아가기](#/README.md)
''')

    for kind, title in [('ox', 'O/X'), ('blank', '빈칸채우기')]:
        guide = ('원문 그대로면 O, 원문과 다른 설명이면 X를 고르세요.' if kind == 'ox' else
                 '직접 입력하는 빈칸과 보기에서 고르는 빈칸을 함께 모았습니다. 입력형은 띄어쓰기·쉼표를 무시해 채점합니다.')
        lines = [f'<div class="lecture-header-box"><span class="lecture-badge">보관 문제 · {title}</span>'
                 f'<h2>{title}</h2><p>{guide} 채점 후 원문과 쪽수를 확인하세요.</p></div>', '',
                 f'# {title} 보관 문제', '', '<div data-tabs="panels" hidden></div>', '']
        for u, data in units.items():
            parts = data['parts']
            lines += [f'## 제{u}강 · {UNIT_TITLES[u]}', '']
            if kind == 'ox':
                lines += [f"O/X {len(parts['ox'])}문항", '', widget(f'quiz/u{u:02d}.json', 'ox'), '']
            else:
                n = sum(practice_type(q) == 'blank' for q in parts['mc'])
                lines += [f"### 직접 입력 ({len(parts['blank'])}문항)", '', widget(f'quiz/u{u:02d}.json', 'blank'), '']
                if n:
                    lines += [f'### 보기 선택 ({n}문항)', '', widget(f'quiz/u{u:02d}.json', 'mc', 'blank'), '']
        lines += ['## 2026 소식지 · 977~994호', '']
        groups = [('ox', 'O/X', None)] if kind == 'ox' else [
            ('star', '직접 입력 · 핵심 기사', None), ('blank', '직접 입력 · 일반 기사', None),
            ('list', '직접 입력 · 목록', 'blank'), ('num', '보기 선택 · 숫자·연도', None)]
        for part, label, filtered in groups:
            n = sum(practice_type(q) == kind for q in news['parts'][part])
            lines += [f'### {label} ({n}문항)', '', widget('quiz/w01.json', part, filtered), '']
        lines += ['<div class="lesson-footer-nav"><a class="complete-btn secondary" href="#/practice/recall/README.md">보관함으로 돌아가기</a>'
                  '<a class="complete-btn" href="#/README.md">기본 학습 메뉴 ➔</a></div>', '']
        write(f'{kind}.md', '\n'.join(lines))
    print(f"🗃️ 별도 보관: O/X {counts['ox']}문항 · 빈칸 {counts['blank']}문항 (입력형·선택형)")


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[1])
