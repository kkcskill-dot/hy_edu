#!/usr/bin/env python3
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SUMMARY_DIR = BASE_DIR / "summary"

def build():
    print("🚀 [1/3] 단원 요약 문서 탐색 중...")
    md_files = sorted(SUMMARY_DIR.glob("*.md"))
    chapters = []

    for f in md_files:
        title = f.stem
        with open(f, "r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if line.startswith("# "):
                    title = line.replace("# ", "").strip()
                    title = re.sub(r"\s*\(.*?\)", "", title)
                    break
        chapters.append((f"summary/{f.name}", title))

    print(f"📄 총 {len(chapters)}개의 단원이 확인되었습니다.")

    # 1. _sidebar.md 생성
    print("📑 [2/3] 목차 사이드바(_sidebar.md) 생성 중...")
    with open(BASE_DIR / "_sidebar.md", "w", encoding="utf-8") as f:
        f.write("* [🏠 학습 센터 홈](README.md)\n\n")
        f.write("* **단원별 핵심 요약 및 해설**\n")
        for path, title in chapters:
            f.write(f"  * [{title}]({path})\n")
        f.write("\n* **부록**\n")
        f.write("  * [ℹ️ 학습 안내 및 사용법](README.md#학습-안내)\n")

    # 2. README.md 생성
    print("🏠 [3/3] 대문 페이지(README.md) 생성 중...")
    with open(BASE_DIR / "README.md", "w", encoding="utf-8") as f:
        f.write("# 🏥 2026 연세대학교 의료원 3급 승진교육 마스터 뷰어\n\n")
        f.write("> **2026년도 일반직 3급 승진교육 교본 및 규정 완벽 요약·해설**\n\n")
        f.write("PC와 모바일 어디서나 핵심 규정을 검색하고 학습할 수 있는 온라인 학습 서비스입니다.\n\n")
        f.write("---\n\n")
        f.write("### 📚 전체 단원 바로가기\n\n")
        for path, title in chapters:
            f.write(f"- 📖 **[{title}]({path})**\n")
        f.write("\n---\n\n")
        f.write("### 💡 주요 기능 안내\n")
        f.write("1. **통합 키워드 검색**: 상단 검색창에 조항 번호(예: `제15조`), 키워드(예: `징계`, `자산취득`, `진료기록부`)를 입력하면 즉시 해당 위치로 이동합니다.\n")
        f.write("2. **조문 및 표 복사 기능**: 각 규정 조항 및 비교표를 우측 상단 복사 버튼으로 손쉽게 복사할 수 있습니다.\n")
        f.write("3. **출처 표기 완비**: 각 요약 내용마다 원본 PDF 교재 페이지 및 규정 제·개정일자가 명시되어 있습니다.\n")

    # 3. index.html 생성
    index_html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>2026 연세의료원 3급 승진교육 학습 센터</title>
  <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
  <link rel="stylesheet" href="//cdn.jsdelivr.net/npm/docsify@4/lib/themes/vue.css">
  <style>
    :root {
      --theme-color: #003876;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    .sidebar {
      font-size: 15px;
      line-height: 1.6;
    }
    .app-name-link {
      font-weight: 700;
      color: #003876 !important;
    }
    .markdown-section {
      max-width: 950px;
      line-height: 1.85;
      font-size: 16px;
    }
    .markdown-section h1 {
      color: #003876;
      border-bottom: 2px solid #003876;
      padding-bottom: 10px;
    }
    .markdown-section h2 {
      color: #1a4f8b;
      margin-top: 36px;
      border-bottom: 1px solid #e1e4e8;
      padding-bottom: 8px;
    }
    .markdown-section h3 {
      color: #2b5f9e;
      margin-top: 26px;
    }
    table {
      display: table !important;
      width: 100%;
      margin: 18px 0;
      border-collapse: collapse;
    }
    th {
      background-color: #f1f4f8;
      color: #003876;
      font-weight: bold;
    }
    th, td {
      border: 1px solid #d0d7de !important;
      padding: 10px 14px !important;
    }
    tr:nth-child(even) {
      background-color: #fafbfc;
    }
    blockquote {
      background-color: #f6f8fa;
      border-left: 4px solid #003876;
      padding: 12px 18px;
      color: #333;
      margin: 16px 0;
    }
    .search input {
      border-radius: 4px;
      padding: 8px 12px;
    }
  </style>
</head>
<body>
  <div id="app">로딩 중... 잠시만 기다려주세요.</div>
  <script>
    window.$docsify = {
      name: '🏛️ 2026 승진교육',
      loadSidebar: true,
      subMaxLevel: 3,
      auto2top: true,
      homepage: 'README.md',
      search: {
        maxAge: 86400000,
        paths: 'auto',
        placeholder: '🔍 규정, 조항, 키워드 검색',
        noData: '검색 결과가 없습니다.',
        depth: 4
      },
      copyCode: {
        buttonText : '복사',
        errorText  : '오류',
        successText: '복사 완료'
      }
    }
  </script>
  <script src="//cdn.jsdelivr.net/npm/docsify@4"></script>
  <script src="//cdn.jsdelivr.net/npm/docsify/lib/plugins/search.min.js"></script>
  <script src="//cdn.jsdelivr.net/npm/docsify-copy-code/dist/docsify-copy-code.min.js"></script>
  <script src="//cdn.jsdelivr.net/npm/docsify/lib/plugins/zoom-image.min.js"></script>
</body>
</html>
"""
    with open(BASE_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html_content)

    print("🎉 루트 웹 파일 생성 완료! (index.html, _sidebar.md, README.md)")

if __name__ == "__main__":
    build()
