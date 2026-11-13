"""문제풀이 공간(/exam) 교본 문항 작성용 공통 형식.

각 단원 파일(tools/exam_u0N*.py)은 SECTIONS(교본 목차 순 소단원 이름)와 ITEMS를 정의한다.

Q(단원, 번호, 소단원, 유형, 발문, [보기 5개], 정답번호(1~5), [(PDF쪽, "교본 원문"), …], "해설")
  - 근거 원문은 교본 original/0N_*.md 의 해당 PDF 쪽 텍스트와 그대로 대조한다
    (띄어쓰기·따옴표·가운뎃점·하이픈 무시, " … " 로 끊은 조각마다 대조).
  - 해설에 보기 번호(①, 3번 보기 등)를 쓰지 않는다.
"""

FORMATS = ("내용 확인", "옳은 설명", "틀린 설명", "숫자·기준", "용어·정의")


def Q(unit, no, section, kind, question, choices, answer, quotes, explain):
    return {
        "id": f"ex-u{unit:02d}-{no:03d}",
        "type": "mc", "unit": unit, "section": section, "format": kind,
        "q": question, "choices": list(choices), "answer": answer,
        "explain": explain,
        "quotes": [{"doc": f"unit{unit:02d}", "p": p, "text": t} for p, t in quotes],
    }
