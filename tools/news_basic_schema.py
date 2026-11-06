"""소식지 기본 모의고사 문항 작성용 공통 형식."""

TOPICS = {
    "ai": "AI·디지털",
    "care": "진료·환자안전",
    "research": "연구·성과",
    "education": "교육·간호",
    "projects": "사업·운영",
    "collaboration": "협력·나눔",
    "values": "비전·제도",
}
FORMATS = ("내용 확인", "옳은 설명", "틀린 설명", "명칭·기능")


def item(issue, number, page, topic, title, question, choices, answer, quote, explain, kind="내용 확인"):
    """정답은 1부터 시작하며, quote는 지정 지면의 원문을 그대로 사용한다."""
    return {
        "id": f"basic26-{issue}-{number:02d}",
        "type": "mc", "unit": 8, "topic": topic,
        "difficulty": "기본", "format": kind, "tag": title,
        "q": question, "choices": choices, "answer": answer,
        "explain": explain,
        "quotes": [{"doc": f"webzine-{issue}", "p": page, "label": title, "text": quote}],
    }
