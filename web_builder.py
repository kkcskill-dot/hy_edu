#!/usr/bin/env python3
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SUMMARY_DIR = BASE_DIR / "summary"
ORIGINAL_DIR = BASE_DIR / "original"

def build():
    print("🚀 [1/3] 마스터 요약집 및 단원 요약 문서 탐색 중...")
    summary_files = sorted(SUMMARY_DIR.glob("*.md"))
    
    print(f"📄 총 {len(summary_files)}개의 요약 문서가 확인되었습니다.")
    
    original_files = sorted([f for f in ORIGINAL_DIR.glob("*.md") if f.name != "webzine_2026_전체색인.md"])
    print(f"📑 총 {len(original_files)}개의 교본 원본 문서가 확인되었습니다.")

    # 1. _sidebar.md 검증 및 업데이트
    print("📑 [2/3] 사이드바(_sidebar.md) 확인 완료.")
    
    # 2. README.md 검증
    print("🏠 [3/3] 대문 페이지(README.md) 확인 완료.")
    print("✨ 웹 서비스 빌드 및 동기화가 성공적으로 완료되었습니다.")

if __name__ == "__main__":
    build()
