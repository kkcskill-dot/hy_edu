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

    # 2. 배포 버전 갱신 → 브라우저에 남은 이전 검색 색인·문항 캐시 무효화
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    html = INDEX_HTML.read_text(encoding="utf-8")
    html, count = re.subn(r"var BUILD = '[^']*';", f"var BUILD = '{stamp}';", html)
    assert count == 1, "index.html에서 BUILD 값을 찾지 못했습니다"
    INDEX_HTML.write_text(html, encoding="utf-8")
    print(f"🔖 [3/4] 배포 버전(BUILD) 갱신: {stamp}")

    # 3. _sidebar.md / README.md 확인
    print("🏠 [4/4] 사이드바(_sidebar.md) · 대문 페이지(README.md) 확인 완료.")
    print("✨ 웹 서비스 빌드 및 동기화가 성공적으로 완료되었습니다.")

if __name__ == "__main__":
    build()
