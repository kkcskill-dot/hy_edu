"""빌드 후 실행: python3 -m unittest discover -s tools -p 'test_news_basic.py'."""
import json
import re
import unittest
from collections import Counter
from pathlib import Path

from news_basic_build import load_items, verify, mock_sets
from practice_types import practice_type

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "practice/news-basic"


class BasicNewsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = load_items()
        cls.bank = json.loads((OUT / "bank.json").read_text())
        cls.mocks = [json.loads((OUT / f"mock{n}.json").read_text()) for n in range(1, 10)]

    def test_all_questions_are_basic_mc_with_verified_source_pages(self):
        self.assertEqual(verify(BASE, self.items), [])
        self.assertEqual(len(self.items), 270)
        self.assertEqual(self.bank["pool"], self.items)
        self.assertEqual({practice_type(q) for q in self.items}, {"mc"})
        self.assertEqual({q["difficulty"] for q in self.items}, {"기본"})
        self.assertEqual(Counter(q["quotes"][0]["doc"] for q in self.items),
                         {f"webzine-{n}": 15 for n in range(977, 995)})
        for q in self.items:
            self.assertNotIn(q["format"], ("복합 보기", "사례 적용", "비교·연결"))
            self.assertNotRegex(q["q"], r"ㄱ\.|ㄴ\.|ㄷ\.")

    def test_nine_exams_cover_all_questions_once_and_all_issues_each_time(self):
        originals = {q["id"]: q for q in self.items}
        used = []
        for mock in self.mocks:
            with self.subTest(exam=mock["id"]):
                qs = mock["questions"]
                self.assertEqual(len(qs), 30)
                self.assertEqual(len({q["id"] for q in qs}), 30)
                self.assertEqual({q["quotes"][0]["doc"] for q in qs},
                                 {f"webzine-{n}" for n in range(977, 995)})
                self.assertEqual(Counter(q["answer"] for q in qs), {n: 6 for n in range(1, 6)})
                for q in qs:
                    old = originals[q["id"]]
                    self.assertEqual(set(q["choices"]), set(old["choices"]))
                    self.assertEqual(q["choices"][q["answer"] - 1], old["choices"][old["answer"] - 1])
                    self.assertEqual({k: v for k, v in q.items() if k not in ("choices", "answer")},
                                     {k: v for k, v in old.items() if k not in ("choices", "answer")})
                    used.append(q["id"])
        self.assertEqual(Counter(used), Counter(originals.keys()))

    def test_rebuilds_preserve_question_order_and_answers(self):
        before = json.dumps(self.items, ensure_ascii=False, sort_keys=True)
        rebuilt = mock_sets(list(reversed(self.items)))
        self.assertEqual(rebuilt, [m["questions"] for m in self.mocks])
        self.assertEqual(json.dumps(self.items, ensure_ascii=False, sort_keys=True), before)

    def test_records_and_questions_do_not_collide_with_existing_learning(self):
        basic_ids = [self.bank["id"]] + [m["id"] for m in self.mocks]
        self.assertEqual(len(set(basic_ids)), 10)
        self.assertTrue(all(k.startswith("news-basic-2026-") for k in basic_ids))
        question_ids = {q["id"] for q in self.items}
        for folder in ("quiz", "mock", "practice/news2026"):
            for path in (BASE / folder).glob("*.json"):
                data = json.loads(path.read_text())
                self.assertNotIn(data["id"], basic_ids)
                qs = data.get("pool", data.get("questions", []))
                qs += [q for part in data.get("parts", {}).values() for q in part]
                self.assertFalse(question_ids.intersection(q.get("id") for q in qs))

    def test_menus_widgets_and_reader_links_resolve(self):
        for name in ("README.md", "_sidebar.md"):
            page = (BASE / name).read_text()
            self.assertLess(page.index("practice/news-basic/README.md"), page.index("practice/news2026/README.md"))
        for n in range(1, 10):
            page = (OUT / f"mock{n}.md").read_text()
            self.assertIn(f'data-src="practice/news-basic/mock{n}.json"', page)
            self.assertIn(f"practice/news-basic/mock{n}.md", (BASE / "_sidebar.md").read_text())
        for path in OUT.glob("*.md"):
            page = path.read_text()
            for link in re.findall(r'(?:href="#/|data-src=")([^"?#]+)', page):
                self.assertTrue((BASE / link).is_file(), (path.name, link))
        rows = re.findall(r"^\| (\d{3})호 \| (.+?) \| (\d+) \| (.+?) \|$", (OUT / "coverage.md").read_text(), re.M)
        self.assertEqual(len(rows), 18)
        for issue, topics, count, links in rows:
            self.assertEqual(int(count), 15)
            self.assertTrue(topics.strip())
            actual_pages = {q["quotes"][0]["p"] for q in self.items if q["quotes"][0]["doc"] == f"webzine-{issue}"}
            linked = {int(n) for n in re.findall(rf'reader.html\?doc=webzine-{issue}&amp;p=(\d+)', links)}
            self.assertEqual(linked, actual_pages)


if __name__ == "__main__":
    unittest.main()
