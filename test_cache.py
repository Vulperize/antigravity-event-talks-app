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
        app.releases_cache["last_failed"] = 0

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
            
            # Assert cooldown is set
            import time
            now = time.time()
            self.assertAlmostEqual(app.releases_cache["last_failed"], now, delta=2)
            
            # Subsequent non-forced request should return stale cached data without calling remote
            mock_get.reset_mock()
            mock_get.side_effect = None
            mock_get.return_value = mock_response
            
            response_subsequent = self.client.get('/api/releases')
            self.assertEqual(response_subsequent.status_code, 200)
            self.assertEqual(response_subsequent.json[0]['title'], "Initial Title")
            mock_get.assert_not_called()

    @patch('app.requests.get')
    def test_cache_http_failure_with_stale_data(self, mock_get):
        # Populate cache first
        mock_response_ok = unittest.mock.Mock()
        mock_response_ok.status_code = 200
        mock_response_ok.content = b"""<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Initial Title</title>
                <updated>2026-06-16T12:00:00Z</updated>
                <content type="html">Initial Content</content>
            </entry>
        </feed>"""
        mock_get.return_value = mock_response_ok

        # Request to populate cache
        response = self.client.get('/api/releases')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_get.call_count, 1)

        # Now mock a non-200 HTTP response
        mock_response_fail = unittest.mock.Mock()
        mock_response_fail.status_code = 503
        mock_get.return_value = mock_response_fail

        with patch.object(app.app.logger, 'error') as mock_error:
            response_fail = self.client.get('/api/releases?refresh=true')
            self.assertEqual(response_fail.status_code, 200)
            # Should have logged error
            mock_error.assert_called_once()
            # Stale cached data is returned
            self.assertEqual(response_fail.json[0]['title'], "Initial Title")
            
            # Assert cooldown is set
            import time
            now = time.time()
            self.assertAlmostEqual(app.releases_cache["last_failed"], now, delta=2)
            
            # Subsequent non-forced request should return stale cached data without calling remote
            mock_get.reset_mock()
            mock_get.return_value = mock_response_ok
            
            response_subsequent = self.client.get('/api/releases')
            self.assertEqual(response_subsequent.status_code, 200)
            self.assertEqual(response_subsequent.json[0]['title'], "Initial Title")
            mock_get.assert_not_called()

    @patch('app.requests.get')
    def test_cache_failure_no_stale_data(self, mock_get):
        # Cache is already empty from setUp()
        mock_get.side_effect = Exception("Connection Refused")

        with patch.object(app.app.logger, 'error') as mock_error:
            response_fail = self.client.get('/api/releases')
            self.assertEqual(response_fail.status_code, 500)
            mock_error.assert_called_once()

    @patch('app.requests.get')
    def test_cooldown_on_empty_cache(self, mock_get):
        # Empty cache, first attempt fails
        mock_get.side_effect = Exception("Connection Refused")
        
        with patch.object(app.app.logger, 'error') as mock_error:
            response = self.client.get('/api/releases')
            self.assertEqual(response.status_code, 500)
            self.assertEqual(mock_get.call_count, 1)
            mock_error.assert_called_once()
        
        # Second attempt should NOT call requests.get because we are in cooldown
        mock_get.reset_mock()
        response2 = self.client.get('/api/releases')
        self.assertEqual(response2.status_code, 500)
        mock_get.assert_not_called()
        
        # Forced refresh should bypass cooldown and try again
        mock_get.reset_mock()
        mock_get.side_effect = Exception("Another Connection Refused")
        with patch.object(app.app.logger, 'error') as mock_error:
            response3 = self.client.get('/api/releases?refresh=true')
            self.assertEqual(response3.status_code, 500)
            self.assertEqual(mock_get.call_count, 1)

    @patch('app.requests.get')
    def test_non_blocking_lock_returns_stale_data(self, mock_get):
        # Populate cache with stale data
        import time
        app.releases_cache["data"] = [{"id": "stale", "title": "Stale", "date": "2026-06-16", "type": "CHANGE", "content": "Stale content"}]
        app.releases_cache["last_updated"] = time.time() - app.CACHE_TIMEOUT_SECONDS - 100
        
        # Acquire lock in test thread to simulate another thread updating the cache
        app.cache_lock.acquire()
        try:
            # Request should immediately return stale data without blocking or calling requests.get
            response = self.client.get('/api/releases')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json[0]['title'], "Stale")
            mock_get.assert_not_called()
        finally:
            app.cache_lock.release()

if __name__ == '__main__':
    unittest.main()
