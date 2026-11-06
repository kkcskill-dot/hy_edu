"""입력형과 선택형 빈칸을 같은 보관 학습 유형으로 분류한다."""
import re

_BLANK = re.compile(r"\(\s*\)|\{\{\d+\}\}|빈칸")


def practice_type(question):
    if question.get("type") == "ox":
        return "ox"
    text = question.get("q", "") + " " + question.get("passage", "")
    if question.get("type") == "blank" or _BLANK.search(text):
        return "blank"
    return "mc"
