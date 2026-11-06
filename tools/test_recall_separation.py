"""Run after web_builder.py: python3 -m unittest discover -s tools -p 'test_recall_separation.py'."""
import json
import re
import subprocess
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from practice_types import practice_type

BASE = Path(__file__).resolve().parents[1]


class Widgets(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.items = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and "mock-exam" in attrs.get("class", "").split():
            self.items.append(attrs)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def pool(widget):
    data = read(BASE / widget["data-src"])
    if widget.get("data-part"):
        qs = data["parts"][widget["data-part"]]
    else:
        qs = data.get("pool", data.get("questions"))
    if widget.get("data-type"):
        qs = [q for q in qs if practice_type(q) == widget["data-type"]]
    return qs


def scope_id(widget):
    data = read(BASE / widget["data-src"])
    return data["id"] + "-" + widget["data-part"] + (
        "-" + widget["data-type"] if widget.get("data-type") else "")


class RecallSeparationTests(unittest.TestCase):
    def test_classification_includes_selection_cloze_but_not_normal_parentheses(self):
        cases = [
            ({"type": "ox", "q": "빈칸을 포함한 원문과 일치한다."}, "ox"),
            ({"type": "blank", "q": "환자 안전 {{0}}"}, "blank"),
            ({"type": "mc", "q": "다음 ( ) 안에 들어갈 말은?", "passage": "기관은 (          )개다."}, "blank"),
            ({"type": "mc", "q": "다음 문장의 완성은?", "passage": "기관은 ( \n )개다."}, "blank"),
            ({"type": "mc", "q": "빈칸에 해당하는 용어는?"}, "blank"),
            ({"type": "mc", "q": "AICC(스마트 고객센터)에 관한 설명은?"}, "mc"),
            ({"q": "2026.9.1. 기준으로 옳은 설명은?"}, "mc"),
        ]
        for question, expected in cases:
            with self.subTest(question=question):
                self.assertEqual(practice_type(question), expected)

    def test_all_primary_question_pages_only_expose_nonempty_regular_mc_pools(self):
        pages = list((BASE / "quiz").glob("0*.md"))
        pages += list((BASE / "mock").glob("*.md"))
        pages += [BASE / "practice/news2026" / name
                  for name in ("quiz.md", "mock1.md", "mock2.md", "mock3.md", "mock4.md")]
        self.assertEqual(len(list((BASE / "quiz").glob("0*.md"))), 8)
        for page in pages:
            widgets = Widgets(page.read_text(encoding="utf-8")).items
            self.assertTrue(widgets, page.name)
            for widget in widgets:
                with self.subTest(page=page.name, widget=widget):
                    questions = pool(widget)
                    self.assertTrue(questions)
                    self.assertEqual({practice_type(q) for q in questions}, {"mc"})

    def test_archive_covers_every_ox_and_blank_once_including_mixed_parts(self):
        expected = {"ox": [], "blank": []}
        for source in (BASE / "quiz").glob("*.json"):
            for questions in read(source)["parts"].values():
                for question in questions:
                    kind = practice_type(question)
                    if kind in expected:
                        expected[kind].append(question["id"])
        for kind in expected:
            page = BASE / f"practice/recall/{kind}.md"
            widgets = Widgets(page.read_text(encoding="utf-8")).items
            self.assertTrue(widgets)
            actual = []
            for widget in widgets:
                questions = pool(widget)
                self.assertTrue(questions, widget)
                self.assertEqual({practice_type(q) for q in questions}, {kind})
                actual += [q["id"] for q in questions]
            self.assertEqual(Counter(actual), Counter(expected[kind]))
            self.assertEqual(len(actual), len(set(actual)), "Archive question duplicated")
        # Regressions that type='mc' alone would silently miss.
        news = read(BASE / "quiz/w01.json")
        self.assertEqual(len(news["parts"]["num"]), 144)
        self.assertTrue(all(practice_type(q) == "blank" for q in news["parts"]["num"]))
        self.assertTrue(any(q["type"] == "blank" for q in news["parts"]["list"]))

    def test_source_questions_ids_and_answers_are_preserved(self):
        for path in (BASE / "quiz").glob("*.json"):
            rel = path.relative_to(BASE).as_posix()
            original = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=BASE,
                                      check=True, stdout=subprocess.PIPE).stdout
            self.assertEqual(read(path), json.loads(original), rel)

    def test_primary_and_archived_sessions_have_distinct_ids(self):
        primary = [widget for page in (BASE / "quiz").glob("0*.md")
                   for widget in Widgets(page.read_text(encoding="utf-8")).items]
        archived = [widget for name in ("ox", "blank")
                    for widget in Widgets((BASE / f"practice/recall/{name}.md").read_text(encoding="utf-8")).items]
        primary_ids, archive_ids = {scope_id(w) for w in primary}, {scope_id(w) for w in archived}
        self.assertFalse(primary_ids & archive_ids)
        self.assertEqual(len(archived), len(archive_ids))
        self.assertIn("u01-ox", archive_ids, "Existing O/X history must remain accessible")
        self.assertIn("u01-blank", archive_ids, "Existing input-blank history must remain accessible")
        self.assertIn("w01-list-mc", primary_ids)
        self.assertIn("w01-list-blank", archive_ids)

    def test_optional_menu_links_to_both_archives(self):
        sidebar = (BASE / "_sidebar.md").read_text(encoding="utf-8")
        self.assertIn("practice/recall/README.md", sidebar)
        self.assertNotIn("단원평가 (빈칸", sidebar)
        self.assertNotIn("소식지 문제은행 (아닌 것은? · 빈칸", sidebar)
        hub = (BASE / "practice/recall/README.md").read_text(encoding="utf-8")
        self.assertIn("practice/recall/ox.md", hub)
        self.assertIn("practice/recall/blank.md", hub)
        for link in re.findall(r'href="#/(practice/recall/[^"]+)"', hub):
            self.assertTrue((BASE / link).exists(), link)


if __name__ == "__main__":
    unittest.main()
