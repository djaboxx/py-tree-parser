"""Tests for the web document processing functionality."""

import unittest
import sys
import os
import asyncio
from unittest.mock import patch, MagicMock
import aiohttp

# Add the src directory to path to allow imports
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from embd.processors.web import WebProcessor
from embd import models
from embd.embedding import EmbeddingGenerator

class TestWebProcessor(unittest.TestCase):
    """Tests for the WebProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the Gemini embedding API
        self.embedding_mock = MagicMock()
        self.embedding_mock.values = [0.1] * 768  # Mock embedding values
        
        self.mock_response = MagicMock()
        self.mock_response.embeddings = [self.embedding_mock]
        
        self.mock_client = MagicMock()
        self.mock_client.models.embed_content.return_value = self.mock_response
        
        with patch('google.genai.Client') as mock_genai_client:
            mock_genai_client.return_value = self.mock_client
            self.embedding_gen = EmbeddingGenerator()
            
        self.url = "https://example.com/docs"
        self.processor = WebProcessor(self.url, self.embedding_gen)
    
    @patch('aiohttp.ClientSession.get')
    def test_fetch_and_process_document(self, mock_get):
        """Test web document fetching and processing."""
        # Set up mocks for a successful request
        mock_response = MagicMock()
        mock_response.status = 200
        async def mock_text():
            return "<html><body><h1>Test Doc</h1><pre><code>def test(): pass</code></pre></body></html>"
        mock_response.text = mock_text
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Process the document
        constructs, imports = self.processor.process()
        
        # Verify basic expectations
        self.assertTrue(isinstance(constructs, list))
        self.assertGreater(len(constructs), 0)
        
        # Verify first result is a (CodeConstruct, embedding) tuple
        first_result, first_embedding = constructs[0]
        self.assertIsInstance(first_result, models.CodeConstruct)
        self.assertEqual(first_result.filename, self.url)
        self.assertEqual(first_result.construct_type, "web_code_block")
        self.assertTrue(isinstance(first_embedding, list))
        self.assertTrue(all(isinstance(x, float) for x in first_embedding))
        
        # Verify imports list
        self.assertTrue(isinstance(imports, list))
        
if __name__ == '__main__':
    unittest.main()
