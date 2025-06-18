# Web Document Processing Update

## Changes Made (June 16, 2025)

This update improves the web document processing capabilities of the `embd` package:

### 1. Consolidated Web Fetcher

- The web document fetcher has been consolidated into a single file: `fetch_web_fixed.py`
- Old implementations (`fetch_web.py` and `fetch_web_enhanced.py`) have been deprecated
- Command-line entry point has been updated to use the new implementation: `embd-web`

### 2. Enhanced Features

- **Chunking for Large Documents**: Automatically breaks down large documents into manageable chunks to avoid token limits
- **Proper Error Handling**: Improved error handling with graceful fallbacks
- **Token Count Reporting**: Added logging with token count information
- **Advanced Processing**: Uses the RAG web processor when available for better document processing

### 3. Usage

```bash
# Basic usage
embd-web https://example.com

# Save to database
embd-web https://example.com --save

# Control chunking parameters
embd-web https://example.com --max-tokens 2000 --chunk-overlap 100 --max-sections 50

# Output to JSON
embd-web https://example.com -o output.json

# Process as Markdown
embd-web https://example.com --as-markdown
```

### 4. Implementation Details

The main implementation in `fetch_web_fixed.py` attempts to use the advanced chunking functionality from the RAG module when available. If the RAG module is not available or fails, it falls back to the original processor.
