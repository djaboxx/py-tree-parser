import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB settings
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "code_parser")
CONSTRUCTS_COLLECTION = os.getenv("CONSTRUCTS_COLLECTION", "code_constructs")
IMPORTS_COLLECTION = os.getenv("IMPORTS_COLLECTION", "imports")

# Gemini settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "gemini-embedding-exp-03-07"  # Latest embedding model
DESCRIBING_MODEL = "gemini-2.0-flash"
# File patterns
CODE_FILE_PATTERNS = ('.py', '.md')
