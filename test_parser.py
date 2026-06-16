import unittest
import xml.etree.ElementTree as ET
from app import parse_xml_feed

class TestParser(unittest.TestCase):
    def test_parse_valid_feed(self):
        sample_xml = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>BigQuery release notes: June 15, 2026</title>
                <updated>2026-06-15T12:00:00Z</updated>
                <content type="html">Feature: A new optimized storage format is now default.</content>
            </entry>
        </feed>"""
        results = parse_xml_feed(sample_xml.encode('utf-8'))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "BigQuery release notes: June 15, 2026")
        self.assertEqual(results[0]['date'], "2026-06-15")
        self.assertEqual(results[0]['type'], "FEATURE")

    def test_missing_and_empty_tags(self):
        # Entry with empty tags (self-closing / no text)
        sample_xml_empty = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title></title>
                <updated/>
                <content type="html"></content>
            </entry>
        </feed>"""
        results = parse_xml_feed(sample_xml_empty.encode('utf-8'))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "No Title")
        self.assertEqual(results[0]['date'], "")
        self.assertEqual(results[0]['type'], "CHANGE")
        self.assertEqual(results[0]['content'], "")

        # Entry with completely missing tags
        sample_xml_missing = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
            </entry>
        </feed>"""
        results2 = parse_xml_feed(sample_xml_missing.encode('utf-8'))
        self.assertEqual(len(results2), 1)
        self.assertEqual(results2[0]['title'], "No Title")
        self.assertEqual(results2[0]['date'], "")
        self.assertEqual(results2[0]['type'], "CHANGE")
        self.assertEqual(results2[0]['content'], "")

    def test_category_classification(self):
        # Helper to generate entry XML with specified content
        def make_feed_xml(content_text):
            return f"""<?xml version="1.0" encoding="utf-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
                <entry>
                    <title>Test Title</title>
                    <updated>2026-06-16T12:00:00Z</updated>
                    <content type="html">{content_text}</content>
                </entry>
            </feed>"""

        # FEATURE triggers: FEATURE, NEW:, INTRODUCED
        for kw in ["Introducing new feature x", "NEW: improved search", "introduced table clone"]:
            results = parse_xml_feed(make_feed_xml(kw).encode('utf-8'))
            self.assertEqual(results[0]['type'], "FEATURE")

        # DEPRECATION triggers: DEPRECATE, DISCONTINUE, REMOVED
        for kw in ["This interface is deprecated", "We will discontinue storage layer v1", "removed legacy api"]:
            results = parse_xml_feed(make_feed_xml(kw).encode('utf-8'))
            self.assertEqual(results[0]['type'], "DEPRECATION")

        # BUGFIX triggers: BUG, FIX, RESOLVED
        for kw in ["Fixed a bug in parsing", "Fix query timeout", "resolved incorrect counts"]:
            results = parse_xml_feed(make_feed_xml(kw).encode('utf-8'))
            self.assertEqual(results[0]['type'], "BUGFIX")

        # CHANGE (default fallback)
        results = parse_xml_feed(make_feed_xml("Just a routine update and change.").encode('utf-8'))
        self.assertEqual(results[0]['type'], "CHANGE")

    def test_malformed_xml(self):
        malformed_xml = "<feed><entry><title>Malformed XML</title>" # Missing closing tags
        with self.assertRaises(ET.ParseError):
            parse_xml_feed(malformed_xml.encode('utf-8'))

    def test_stable_id_generation(self):
        sample_xml = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>BigQuery release notes: June 15, 2026</title>
                <updated>2026-06-15T12:00:00Z</updated>
                <content type="html">Feature: A new optimized storage format is now default.</content>
            </entry>
        </feed>"""
        results1 = parse_xml_feed(sample_xml.encode('utf-8'))
        results2 = parse_xml_feed(sample_xml.encode('utf-8'))
        
        # Verify both parses yield the same stable ID
        id1 = results1[0]['id']
        id2 = results2[0]['id']
        self.assertEqual(id1, id2)
        
        # Verify length of the ID (16 hex chars as specified by [:16])
        self.assertEqual(len(id1), 16)
        # Verify it consists of valid hex chars
        int(id1, 16)

if __name__ == '__main__':
    unittest.main()
