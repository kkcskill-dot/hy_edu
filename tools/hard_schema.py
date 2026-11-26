"""고난도(중·상) 문제 세트 — 공통 형식. 검증: python3 tools/hard_check.py

H(key, no, section, kind, question, choices, answer, quotes, explain, passage=None, truth=None)

key      교본 "u01"~"u07" · 소식지 "n977"~"n996"  → ID hd-u01-001 · hd-n977-001
section  교본: 그 단원 SECTIONS(tools/exam_u0N*.py)의 이름 · 소식지: 기사 제목을 줄인 꼬리표(원문 표현)
kind     FORMATS 중 하나
choices  보기 5개 (개수 판단은 ["1개", "2개", "3개", "4개", "5개"] 또는 ["0개", "1개", "2개", "3개", "4개"])
answer   정답 번호 1~5
quotes   [(쪽, "원문 그대로"), …] 1~6개 — key 문서(교본 단원·소식지 호)의 쪽. 같은 쪽의 떨어진 부분은 " … "로 잇는다
explain  해설 — 틀린 진술마다 원문 표현을 밝힌다 (보기 번호 언급 금지)
passage  개수 판단·복합 보기·순서 배열: "ㄱ. …\nㄴ. …" · 빈칸 짝짓기: (가)(나)…가 든 글 · 사례 적용·수치 계산: 사례·조건 글
truth    개수 판단·복합 보기: 진술(ㄱ부터)마다 원문과 맞으면 True, 틀리면 False
         옳은 설명·틀린 설명(사례 적용은 선택): 보기(1번부터)마다 True/False
"""
FORMATS = ("개수 판단", "복합 보기", "빈칸 짝짓기", "순서 배열", "수치 계산", "사례 적용", "옳은 설명", "틀린 설명")


def H(key, no, section, kind, question, choices, answer, quotes, explain, passage=None, truth=None):
    doc = f"unit{key[1:]}" if key.startswith("u") else f"webzine-{key[1:]}"
    item = {
        "id": f"hd-{key}-{no:03d}", "key": key, "section": section, "format": kind,
        "q": question, "choices": list(choices), "answer": answer, "explain": explain,
        "quotes": [{"doc": doc, "p": r[0], "text": r[1]} if len(r) == 2 else {"doc": r[0], "p": r[1], "text": r[2]}
                   for r in quotes],
    }
    if passage:
        item["passage"] = passage
    if truth is not None:
        item["truth"] = list(truth)
    return item
