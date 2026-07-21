"""Offline verification of citation extraction from OpenRouter payloads.

Run: python3 -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from engines import Answer, _provider_citations


def _payload(**extra) -> dict:
    return {"choices": [{"message": {"content": "text"}}], **extra}


class TestProviderCitations(unittest.TestCase):
    def test_none_when_absent(self):
        self.assertEqual(_provider_citations(_payload()), [])

    def test_perplexity_style_url_strings(self):
        p = _payload(citations=["https://g2.com/a", "https://capterra.com/b"])
        self.assertEqual(_provider_citations(p),
                         ["https://g2.com/a", "https://capterra.com/b"])

    def test_citation_objects(self):
        p = _payload(citations=[{"url": "https://g2.com/a"}])
        self.assertEqual(_provider_citations(p), ["https://g2.com/a"])

    def test_openai_style_annotations(self):
        p = {"choices": [{"message": {
            "content": "text",
            "annotations": [
                {"type": "url_citation",
                 "url_citation": {"url": "https://forbes.com/x", "title": "X"}},
            ],
        }}]}
        self.assertEqual(_provider_citations(p), ["https://forbes.com/x"])

    def test_flat_annotation_shape(self):
        p = {"choices": [{"message": {
            "content": "text",
            "annotations": [{"type": "url_citation", "url": "https://a.com/1"}],
        }}]}
        self.assertEqual(_provider_citations(p), ["https://a.com/1"])

    def test_deduped_across_both_sources(self):
        p = {"choices": [{"message": {
            "content": "text",
            "annotations": [{"type": "url_citation",
                             "url_citation": {"url": "https://a.com/1"}}],
        }}], "citations": ["https://a.com/1", "https://b.com/2"]}
        self.assertEqual(_provider_citations(p),
                         ["https://a.com/1", "https://b.com/2"])

    def test_malformed_entries_ignored(self):
        p = _payload(citations=[None, {}, {"title": "no url"}, "https://ok.com"])
        self.assertEqual(_provider_citations(p), ["https://ok.com"])


class TestAnswer(unittest.TestCase):
    def test_not_truncated_by_default(self):
        self.assertFalse(Answer("text", []).truncated)

    def test_truncation_flag_carried(self):
        self.assertTrue(Answer("text", [], True).truncated)


if __name__ == "__main__":
    unittest.main()
