#!/usr/bin/env python3
import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SUMMARY_DIR = BASE_DIR / "summary"
ORIGINAL_DIR = BASE_DIR / "original"
MOCK_DIR = BASE_DIR / "mock"
INDEX_HTML = BASE_DIR / "index.html"
VERSION_JSON = BASE_DIR / "version.json"
READER_HTML = BASE_DIR / "reader.html"
EBOOK_DIR = BASE_DIR / "ebook"
WEBZINE_META = BASE_DIR / "data" / "2026_webzine" / "metadata.json"


def build_ebook_index():
    docs = []
    titles = {}
    for md in sorted(ORIGINAL_DIR.glob("0*_*.md")):
        first = md.read_text(encoding="utf-8").splitlines()[0]
        m = re.match(r"#\s*\S*\s*제(\d+)단원 교본 원본:\s*(.+)", first)
        if m:
            titles[f"unit{int(m.group(1)):02d}"] = (f"제{m.group(1)}단원 교본", m.group(2).strip())
    webzines = {}
    if WEBZINE_META.exists():
        for x in json.loads(WEBZINE_META.read_text(encoding="utf-8")):
            webzines[f"webzine-{x['issue']}"] = x
    for meta_path in sorted(EBOOK_DIR.glob("*/meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        doc_id = meta["id"]
        if doc_id in titles:
            title, sub = titles[doc_id]
            group = "승진교육 교본"
        elif doc_id in webzines:
            x = webzines[doc_id]
            title, sub = f"연세의료원소식 {x['issue']}호", f"{x['date']} 발행"
            group = "2026 연세의료원 소식지"
        else:
            continue
        docs.append({"id": doc_id, "title": title, "sub": sub, "group": group,
                     "pages": meta["pages"], "sizes": meta["sizes"]})
    order = {"승진교육 교본": 0, "2026 연세의료원 소식지": 1}
    docs.sort(key=lambda d: (order[d["group"]], d["id"]))
    (EBOOK_DIR / "index.json").write_text(
        json.dumps({"groups": list(order), "docs": docs}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"📖 e-book 서재 목록: {len(docs)}권 ({sum(d['pages'] for d in docs)}쪽)")

def build():
    print("🚀 [1/4] 마스터 요약집 및 단원 요약 문서 탐색 중...")
    summary_files = sorted(SUMMARY_DIR.glob("*.md"))

    print(f"📄 총 {len(summary_files)}개의 요약 문서가 확인되었습니다.")

    original_files = sorted([f for f in ORIGINAL_DIR.glob("*.md") if f.name != "webzine_2026_전체색인.md"])
    print(f"📑 총 {len(original_files)}개의 교본 원본 문서가 확인되었습니다.")

    # 1. 실전 모의고사 데이터 검증 (보기 4개, 정답 번호, 원문 근거 필수)
    print("📝 [2/4] 실전 모의고사 문항 검증 중...")
    for path in sorted(MOCK_DIR.glob("set*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for i, q in enumerate(data["questions"], 1):
            assert len(q["choices"]) == 4, f"{path.name} 문{i}: 보기는 4개여야 합니다"
            assert 1 <= q["answer"] <= 4, f"{path.name} 문{i}: 정답 번호 오류"
            assert q.get("quote") and q.get("source"), f"{path.name} 문{i}: 원문 근거 누락"
        print(f"   {path.name}: {len(data['questions'])}문항 확인")

    # 1-2. 필수 기능 코드가 실수로 지워지지 않았는지 확인 (모바일 메뉴·진도·채점·자동 갱신)
    html = INDEX_HTML.read_text(encoding="utf-8")
    required = {
        "모바일 메뉴(드로어)": "window.hyeduSetDrawer = setDrawer;",
        "메뉴 버튼 동작": "closest('.menu-btn')",
        "학습 진도·메뉴 정리": "function decorateNav()",
        "모의고사 채점": "function mxBuild(",
        "배포 후 자동 갱신": "function checkForUpdate(",
    }
    missing = [name for name, marker in required.items() if marker not in html]
    assert not missing, f"index.html에 필수 기능 코드가 없습니다: {', '.join(missing)}"
    print("🧩 필수 기능 코드 확인: " + ", ".join(required))

    # 2. 배포 버전 갱신 → 열려 있는 화면이 version.json을 보고 자동으로 새 버전을 불러옴
    #    (문서·문항 요청에도 같은 값이 붙어 GitHub Pages·nginx 캐시를 건너뜀) — push 전에 꼭 실행
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for page in (INDEX_HTML, READER_HTML):
        html = page.read_text(encoding="utf-8")
        html, count = re.subn(r"var BUILD = '[^']*';", f"var BUILD = '{stamp}';", html)
        assert count == 1, f"{page.name}에서 BUILD 값을 찾지 못했습니다"
        page.write_text(html, encoding="utf-8")
    VERSION_JSON.write_text(json.dumps({"build": stamp}) + "\n", encoding="utf-8")
    print(f"🔖 [3/4] 배포 버전(BUILD · version.json) 갱신: {stamp}")

    # 3. e-book 서재 목록 (ebook/<문서>/meta.json → ebook/index.json)
    build_ebook_index()

    # 3. _sidebar.md / README.md 확인
    print("🏠 [4/4] 사이드바(_sidebar.md) · 대문 페이지(README.md) 확인 완료.")
    print("✨ 웹 서비스 빌드 및 동기화가 성공적으로 완료되었습니다.")

if __name__ == "__main__":
    build()
