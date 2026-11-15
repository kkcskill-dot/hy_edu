"""빌드 후 실행: python3 -m unittest discover -s tools -p 'test_exam.py'."""
import json
import re
import unittest
from collections import Counter
from pathlib import Path

import exam_check
import hard_check
from news_basic_build import load_items as basic_items
import news2026_build

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "exam/data"


class ExamSpaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((OUT / "index.json").read_text())
        cls.sets = {m["id"]: json.loads((OUT / f"{m['id']}.json").read_text())
                    for g in cls.catalog["groups"] for m in g["sets"]}

    def test_textbook_items_match_source_pages(self):
        items, sections = exam_check.load()
        self.assertEqual(exam_check.verify(items, sections), [])
        self.assertEqual({q["unit"] for q in items}, set(range(1, 8)))

    def test_groups_are_units_and_issues(self):
        groups = {g["key"]: g for g in self.catalog["groups"]}
        self.assertEqual([g["key"] for g in self.catalog["groups"]], ["textbook", "news", "hard"])
        self.assertEqual([m["id"] for m in groups["textbook"]["sets"]], [f"unit{n:02d}" for n in range(1, 8)])
        self.assertEqual([m["id"] for m in groups["news"]["sets"]], [f"news{n}" for n in range(977, 996)])
        self.assertEqual([m["id"] for m in groups["hard"]["sets"]],
                         [f"hard-unit{n:02d}" for n in range(1, 8)] + [f"hard-news{n}" for n in range(977, 996)])

    def test_hard_items_verify_and_are_placed_once(self):
        found = hard_check.load()
        self.assertEqual(sorted(found), sorted(hard_check.MODULES))
        self.assertEqual(hard_check.verify(found), [])
        expected = {q["id"] for items in found.values() for q in items}
        placed = Counter(q["id"] for k, s in self.sets.items() if k.startswith("hard-") for q in s["questions"])
        self.assertEqual(set(placed), expected)
        self.assertEqual([k for k, v in placed.items() if v > 1], [])
        for k, s in self.sets.items():
            for q in s["questions"]:
                self.assertEqual(q["level"] == "고난도", k.startswith("hard-"), (k, q["id"]))
                if k.startswith("hard-news"):
                    self.assertEqual(q["section"], "고난도")
                    self.assertTrue(q.get("tag"), q["id"])

    def test_every_news_question_is_placed_once(self):
        expected = {q["id"] for q in basic_items()}
        expected |= {q["id"] for q in news2026_build.ITEMS}
        placed = Counter(q["id"] for k, s in self.sets.items() if k.startswith("news") for q in s["questions"])
        self.assertEqual(set(placed), expected)
        self.assertEqual(max(placed.values()), 1)

    def test_questions_are_well_formed_and_catalog_matches(self):
        ids = Counter()
        for g in self.catalog["groups"]:
            for m in g["sets"]:
                s = self.sets[m["id"]]
                qs = s["questions"]
                self.assertEqual(m["count"], len(qs))
                self.assertEqual(m["ids"], [q["id"] for q in qs])
                self.assertEqual(sum(x["count"] for x in m["sections"]), len(qs))
                for q in qs:
                    ids[q["id"]] += 1
                    self.assertIn(q["section"], s["sections"])
                    self.assertIn(q["level"], ("기본", "심화", "고난도"))
                    self.assertFalse({"key", "truth"} & set(q), q["id"])
                    self.assertEqual(len(q["choices"]), 5)
                    self.assertIn(q["answer"], range(1, 6))
                    self.assertTrue(q["explain"] and q["quotes"])
                    for r in q["quotes"]:
                        meta = json.loads((BASE / "ebook" / r["doc"] / "meta.json").read_text())
                        self.assertTrue(1 <= r["p"] <= meta["pages"], (q["id"], r))
        self.assertEqual(max(ids.values()), 1)

    def test_page_is_wired_into_site(self):
        html = (BASE / "exam/index.html").read_text()
        self.assertRegex(html, r"var BUILD = '\d{8}-\d{6}';")
        self.assertIn("../reader.html?doc=", html)
        self.assertIn("exam/", (BASE / "_sidebar.md").read_text())
        self.assertIn('href="exam/"', (BASE / "README.md").read_text())
        self.assertIn("(exam/#/g/hard ':ignore')", (BASE / "_sidebar.md").read_text())
        self.assertIn('href="exam/#/g/hard"', (BASE / "README.md").read_text())
        self.assertTrue(re.search(r"EXAM_HTML", (BASE / "web_builder.py").read_text()))

    def test_published_files_are_not_gitignored(self):
        import subprocess
        files = ["exam/index.html", "exam/data/index.json"] + [f"exam/data/{k}.json" for k in self.sets]
        ignored = subprocess.run(["git", "check-ignore", *files], cwd=BASE, capture_output=True, text=True).stdout
        self.assertEqual(ignored.strip(), "")


if __name__ == "__main__":
    unittest.main()
