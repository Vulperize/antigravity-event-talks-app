import unittest
from unittest.mock import patch
import app

class TestCache(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.app.config['TESTING'] = True
        self.client = app.app.test_client()
        
        # Reset cache
        app.releases_cache["data"] = None
        app.releases_cache["last_updated"] = 0

    @patch('app.requests.get')
    def test_caching_behavior(self, mock_get):
        # Setup mock response
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.content = b"""<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Test Title</title>
                <updated>2026-06-16T12:00:00Z</updated>
                <content type="html">Test Content</content>
            </entry>
        </feed>"""
        mock_get.return_value = mock_response

        # 1. First request should call requests.get
        response1 = self.client.get('/api/releases')
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(mock_get.call_count, 1)

        # 2. Second request should return cached data and not call requests.get again
        response2 = self.client.get('/api/releases')
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(mock_get.call_count, 1) # Still 1

        # 3. Request with refresh=true should bypass cache and call requests.get again
        response3 = self.client.get('/api/releases?refresh=true')
        self.assertEqual(response3.status_code, 200)
        self.assertEqual(mock_get.call_count, 2) # Incremented to 2

        # 4. Request with refresh=false should return cached data and not call requests.get
        response4 = self.client.get('/api/releases?refresh=false')
        self.assertEqual(response4.status_code, 200)
        self.assertEqual(mock_get.call_count, 2) # Still 2

    @patch('app.requests.get')
    def test_cache_failure_with_stale_data(self, mock_get):
        # Populate cache first
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.content = b"""<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Initial Title</title>
                <updated>2026-06-16T12:00:00Z</updated>
                <content type="html">Initial Content</content>
            </entry>
        </feed>"""
        mock_get.return_value = mock_response

        # Request to populate cache
        response = self.client.get('/api/releases')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_get.call_count, 1)

        # Now mock a request exception for forced refresh
        mock_get.side_effect = Exception("Connection Refused")

        with patch.object(app.app.logger, 'warning') as mock_warning:
            response_fail = self.client.get('/api/releases?refresh=true')
            self.assertEqual(response_fail.status_code, 200)
            # Should have called warning log
            mock_warning.assert_called_once()
            # Stale cached data is returned
            self.assertEqual(response_fail.json[0]['title'], "Initial Title")

    @patch('app.requests.get')
    def test_cache_failure_no_stale_data(self, mock_get):
        # Cache is already empty from setUp()
        mock_get.side_effect = Exception("Connection Refused")

        with patch.object(app.app.logger, 'error') as mock_error:
            response_fail = self.client.get('/api/releases')
            self.assertEqual(response_fail.status_code, 500)
            mock_error.assert_called_once()

if __name__ == '__main__':
    unittest.main()
