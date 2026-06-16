import unittest
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

if __name__ == '__main__':
    unittest.main()
