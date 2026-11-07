"""Smoke tests HTTP para sondagem do Render."""
import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from app import db
from app.server import Handler

class HttpSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(db, 'DB_PATH', Path(self.temp.name) / 'test.sqlite3')
        self.db_patch.start()
        db.initialize()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.db_patch.stop()
        self.temp.cleanup()

    def request(self, method, path):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request(method, path)
        response = connection.getresponse()
        status, body = response.status, response.read()
        connection.close()
        return status, body

    def test_head_root(self):
        status, body = self.request('HEAD', '/')
        self.assertEqual((status, body), (200, b''))

    def test_health(self):
        status, body = self.request('GET', '/api/health')
        self.assertEqual(status, 200)
        self.assertIn(b'"status": "ok"', body)

    def test_head_health(self):
        status, body = self.request('HEAD', '/api/health')
        self.assertEqual((status, body), (200, b''))
