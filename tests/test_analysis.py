"""Offline verification of the pure analysis core. Run: python3 -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from analysis import (aggregate, analyze_response, compute_deltas,
                      extract_citations, find_mentions, position_score,
                      share_of_voice)

RESPONSE = (
    "For project management, Asana is a popular choice. Asana's timeline view "
    "is strong, though Trello and Monday.com are simpler for small teams. "
    "See https://www.example.com/pm-tools and https://blog.asana.com/guide. "
    "Many teams also like Trello for kanban boards."
)


class TestMentions(unittest.TestCase):
    def test_finds_brand_and_possessive(self):
        m = find_mentions(RESPONSE, "Asana")
        self.assertEqual(len(m), 2)  # "Asana" + "Asana's" (blog URL is not a word match)
        self.assertEqual(m[0]["offset"], RESPONSE.index("Asana"))

    def test_aliases_counted(self):
        m = find_mentions("We use PostHog. posthog is great.", "PostHog")
        self.assertEqual(len(m), 2)  # case-insensitive

    def test_no_partial_word_match(self):
        self.assertEqual(find_mentions("Asanas are yoga poses", "Asana"), [])

    def test_empty_alias_ignored(self):
        self.assertEqual(len(find_mentions("Acme rocks", "Acme", ["  "])), 1)


class TestScoring(unittest.TestCase):
    def test_position_score_top(self):
        self.assertEqual(position_score("Acme is best" + "x" * 1000, 0), 10)

    def test_position_score_tail(self):
        text = "x" * 1000 + "Acme"
        self.assertEqual(position_score(text, 1000), 1)

    def test_position_score_absent(self):
        self.assertEqual(position_score("whatever", None), 0)

    def test_share_of_voice(self):
        self.assertEqual(share_of_voice(2, {"Trello": 2}), 0.5)
        self.assertEqual(share_of_voice(0, {}), 0.0)
        self.assertEqual(share_of_voice(3, {"A": 0, "B": 0}), 1.0)


class TestCitations(unittest.TestCase):
    def test_extracts_unique_urls_with_domains(self):
        c = extract_citations(RESPONSE)
        self.assertEqual([x["domain"] for x in c], ["example.com", "blog.asana.com"])

    def test_strips_trailing_punctuation(self):
        c = extract_citations("See https://a.com/x.")
        self.assertEqual(c[0]["url"], "https://a.com/x")

    def test_provider_source_urls_included(self):
        # Search-backed engines return sources out-of-band, not in the prose.
        c = extract_citations("No links in this prose at all.",
                              ["https://www.g2.com/categories/pm"])
        self.assertEqual([x["domain"] for x in c], ["g2.com"])

    def test_provider_urls_deduped_against_inline(self):
        c = extract_citations("See https://a.com/x for more.",
                              ["https://a.com/x", "https://b.com/y"])
        self.assertEqual([x["url"] for x in c],
                         ["https://a.com/x", "https://b.com/y"])

    def test_analyze_response_surfaces_provider_domains(self):
        r = analyze_response("Asana is popular.", "Asana", None, [],
                             ["https://blog.example.com/pm"])
        self.assertEqual(r["cited_domains"], ["blog.example.com"])


class TestAnalyzeAndAggregate(unittest.TestCase):
    def test_analyze_response_full(self):
        r = analyze_response(RESPONSE, "Asana", None, ["Trello", "Monday.com"])
        self.assertTrue(r["brand_mentioned"])
        self.assertEqual(r["mention_count"], 2)
        self.assertEqual(r["competitor_mentions"], {"Trello": 2, "Monday.com": 1})
        self.assertAlmostEqual(r["share_of_voice"], 2 / 5)
        self.assertEqual(r["position_score"], 10)

    def test_aggregate_and_deltas(self):
        recs = [
            {"brand": "Asana", "engine": "chatgpt", "brand_mentioned": True,
             "position_score": 10, "share_of_voice": 0.5},
            {"brand": "Asana", "engine": "perplexity", "brand_mentioned": False,
             "position_score": 0, "share_of_voice": 0.0},
        ]
        agg = aggregate(recs)
        self.assertEqual(agg["Asana"]["mention_rate"], 0.5)
        self.assertEqual(agg["Asana"]["engines"]["chatgpt"]["mention_rate"], 1.0)

        prev = {"Asana": {"mention_rate": 0.75, "avg_position_score": 6.0,
                          "avg_share_of_voice": 0.4}}
        d = compute_deltas(agg, prev)
        self.assertEqual(d["Asana"]["mention_rate"]["delta"], -0.25)
        # brand new this run → previous None
        d2 = compute_deltas(agg, None)
        self.assertIsNone(d2["Asana"]["mention_rate"]["previous"])


if __name__ == "__main__":
    unittest.main()
