"""Run with: python3 -m unittest discover -s tools -p 'test_news2026.py'."""

import json
import re
import unittest
from collections import Counter
from pathlib import Path

from kichul_build import load_sources
from webzine_build import missing


BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "practice" / "news2026"


class News2026ContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = json.loads((OUT / "bank.json").read_text(encoding="utf-8"))
        cls.items = cls.bank["pool"]
        cls.pages, _ = load_sources(BASE)
        cls.mocks = [json.loads((OUT / f"mock{i}.json").read_text(encoding="utf-8"))
                     for i in range(1, 5)]

    def test_substantive_coverage_and_difficulty(self):
        self.assertEqual(len(self.items), 120)
        self.assertEqual(Counter(q["topic"] for q in self.items), {
            "prism": 12, "aicc": 12, "yaid": 12,
            "clinical": 8, "operations": 8, "strategy": 8,
            "care": 10, "research": 10, "education": 10,
            "projects": 10, "collaboration": 10, "values": 10,
        })
        self.assertGreaterEqual(sum(q["difficulty"] == "상" for q in self.items), 60)
        self.assertEqual(len({q["format"] for q in self.items}), 6)
        self.assertEqual(set(self.bank["topics"]), {q["topic"] for q in self.items})
        self.assertTrue(any(q["topic"] == "aicc" and q["format"] == "명칭·기능"
                            for q in self.items))
        for topic in ("prism", "aicc", "yaid"):
            self.assertTrue(any(q["topic"] == topic and q["format"] == "틀린 설명"
                                for q in self.items), topic)

    def test_all_eighteen_newsletter_issues_have_multiple_questions(self):
        coverage = Counter(doc for q in self.items for doc in {r["doc"] for r in q["quotes"]})
        self.assertEqual(set(coverage), {f"webzine-{i}" for i in range(977, 995)})
        for doc, count in coverage.items():
            self.assertGreaterEqual(count, 2, f"{doc} needs at least two sourced questions")
        page = (OUT / "coverage.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| (\d{3})호 \| (.+?) \| (\d+) \| (.+?) \|$", page, re.M)
        self.assertEqual(len(rows), 18)
        self.assertEqual({int(row[0]) for row in rows}, set(range(977, 995)))
        for issue, topics, count, links in rows:
            self.assertTrue(topics.strip())
            self.assertEqual(int(count), coverage[f"webzine-{issue}"])
            referenced = {r["p"] for q in self.items for r in q["quotes"]
                          if r["doc"] == f"webzine-{issue}"}
            linked = {int(p) for p in re.findall(rf"reader.html\?doc=webzine-{issue}(?:&|&amp;)p=(\d+)", links)}
            self.assertEqual(linked, referenced)
            for markdown_link in re.findall(r"\]\((reader\.html[^)]+)\)", links):
                self.assertIn(":ignore", markdown_link, "Reader links must bypass Docsify hash routing")

    def test_single_answer_and_stable_identifiers(self):
        self.assertEqual(len({q["id"] for q in self.items}), len(self.items))
        self.assertEqual(len({q["q"] for q in self.items}), len(self.items))
        for q in self.items:
            with self.subTest(question=q["id"]):
                self.assertEqual(q["type"], "mc")
                self.assertEqual(len(q["choices"]), 5)
                self.assertEqual(len(set(q["choices"])), 5)
                self.assertIs(type(q["answer"]), int)
                self.assertIn(q["answer"], range(1, 6))
                self.assertIn(q["difficulty"], ("중", "상"))
                self.assertTrue(q["explain"].strip())
                self.assertTrue(q["quotes"])
                # Choice order is randomized: explanations must not rely on its numbers.
                self.assertNotRegex(q["explain"], r"[①②③④⑤]|[1-5]번\s*(?:보기|선지)")
                if q["format"] == "복합 보기":
                    self.assertTrue(q.get("passage"))

    def test_each_quote_matches_the_actual_cited_page(self):
        for q in self.items:
            for ref in q["quotes"]:
                with self.subTest(question=q["id"], doc=ref["doc"], page=ref["p"]):
                    self.assertRegex(ref["doc"], r"^webzine-\d{3}$")
                    self.assertIs(type(ref["p"]), int)
                    self.assertEqual(missing(self.pages, int(ref["doc"].split("-")[1]),
                                             ref["p"], ref["text"]), [])
                    meta = json.loads((BASE / "ebook" / ref["doc"] / "meta.json").read_text())
                    self.assertGreaterEqual(ref["p"], 1)
                    self.assertLessEqual(ref["p"], meta["pages"])

    def test_mock_sets_are_balanced_disjoint_and_complete(self):
        bank_by_id = {q["id"]: q for q in self.items}
        sets = []
        topic_counts = []
        high_counts = []
        for data in self.mocks:
            self.assertEqual(len(data["questions"]), 30)
            topics = Counter(q["topic"] for q in data["questions"])
            self.assertEqual(set(topics), set(self.bank["topics"]))
            topic_counts.append(topics)
            high = sum(q["difficulty"] == "상" for q in data["questions"])
            self.assertGreaterEqual(high, 15)
            high_counts.append(high)
            self.assertEqual(Counter(q["answer"] for q in data["questions"]),
                             {answer: 6 for answer in range(1, 6)})
            ids = {q["id"] for q in data["questions"]}
            self.assertEqual(len(ids), 30)
            sets.append(ids)
            for q in data["questions"]:
                original = bank_by_id[q["id"]]
                # Mock option order is balanced at build time; semantic answers stay the same.
                self.assertEqual(set(q["choices"]), set(original["choices"]))
                self.assertEqual(q["choices"][q["answer"] - 1],
                                 original["choices"][original["answer"] - 1])
                self.assertEqual({k: v for k, v in q.items() if k not in ("choices", "answer")},
                                 {k: v for k, v in original.items() if k not in ("choices", "answer")})
        self.assertEqual(sum(len(s) for s in sets), len(set.union(*sets)))
        self.assertEqual(set.union(*sets), set(bank_by_id))
        for topic in self.bank["topics"]:
            counts = [c[topic] for c in topic_counts]
            self.assertLessEqual(max(counts) - min(counts), 1, topic)
        self.assertLessEqual(max(high_counts) - min(high_counts), 1)

    def test_menu_data_paths_and_storage_are_separate(self):
        sidebar = (BASE / "_sidebar.md").read_text(encoding="utf-8")
        home = (BASE / "README.md").read_text(encoding="utf-8")
        self.assertIn("practice/news2026/README.md", sidebar)
        self.assertIn("practice/news2026/README.md", home)
        ids = [self.bank["id"]] + [d["id"] for d in self.mocks]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertTrue(all(i.startswith("news2026-") for i in ids))
        for name in ("README.md", "quiz.md", "mock1.md", "mock2.md", "mock3.md", "mock4.md", "coverage.md"):
            page = (OUT / name).read_text(encoding="utf-8")
            for src in re.findall(r'data-src="([^"]+)"', page):
                self.assertTrue((BASE / src).is_file(), src)
                self.assertTrue(src.startswith("practice/news2026/"), src)


if __name__ == "__main__":
    unittest.main()
