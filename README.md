# embd

A tool for extracting, embedding, and storing code constructs from Git repositories using tree-sitter parsing and Gemini embeddings.

## Installation

```bash
pip install -e .
```

## Usage

Navigate to any Git repository and run:

```bash
embd
```

The tool will:
1. Find all tracked Python and Markdown files
2. Parse them using tree-sitter
3. Extract code constructs (functions and classes)
4. Generate embeddings using Google's Gemini API
5. Store everything in MongoDB

## Configuration

Environment variables:
- `MONGO_URI`: MongoDB connection string (default: "mongodb://admin:password@localhost:27017")
- `MONGO_DB`: Database name (default: "code_parser")
- `CONSTRUCTS_COLLECTION`: Collection for code constructs (default: "code_constructs")
- `IMPORTS_COLLECTION`: Collection for imports (default: "imports")
- `GEMINI_API_KEY`: Your Google Gemini API key

## Data Models

### Code Constructs

The `CodeConstruct` model represents parsed code entities (functions and classes):

```python
class CodeConstruct:
    filename: str           # Source file path
    git_commit: str        # Git commit hash of last change
    code: str             # Actual code content
    construct_type: str    # "function_definition" or "class_definition"
    embedding: List[float] # Gemini vector embedding
    line_start: int       # Starting line in source file
    line_end: int         # Ending line in source file
    created_at: datetime  # When the record was created
    updated_at: datetime  # When the record was last updated
```

### Imports

The `Import` model tracks module imports across the codebase:

```python
class Import:
    filename: str        # Source file path
    repository: str      # Git repository name
    module_name: str     # Name of imported module
    import_type: str     # "import" or "from-import"
    created_at: datetime # When the record was created
    updated_at: datetime # When the record was last updated
```

## MongoDB Schema

### code_constructs Collection

```javascript
{
  "_id": ObjectId,
  "filename": String,        // Indexed
  "git_commit": String,      // Indexed
  "code": String,
  "construct_type": String,  // Indexed
  "embedding": Array,        // Vector embedding
  "line_start": Number,      // Indexed
  "line_end": Number,
  "created_at": Date,       // Indexed
  "updated_at": Date        // Indexed
}
```

Indexes:
- `filename_1_line_start_1_line_end_1`: Unique compound index for deduplication
- `construct_type_1`: For querying by function/class
- `git_commit_1`: For version tracking
- `created_at_1`: For time-based queries
- `updated_at_1`: For change tracking

### imports Collection

```javascript
{
  "_id": ObjectId,
  "filename": String,       // Indexed
  "repository": String,     // Indexed
  "module_name": String,    // Indexed
  "import_type": String,    // Indexed
  "created_at": Date,      // Indexed
  "updated_at": Date       // Indexed
}
```

Indexes:
- `filename_1_module_name_1`: Unique compound index for deduplication
- `repository_1`: For repository-wide queries
- `module_name_1`: For dependency analysis
- `import_type_1`: For filtering by import type

## Features

- Extracts functions and classes from Python files
- Parses import statements and tracks dependencies
- Generates semantic embeddings using Gemini API
- Tracks file changes through Git commits
- Stores everything in MongoDB for easy querying
- Supports both Python and Markdown files

## Requirements

- Python 3.8+
- MongoDB
- Git repository
- Google Gemini API key

## Dependencies

- gitpython: Git repository interaction
- tree-sitter: Code parsing
- pymongo: MongoDB interaction
- google-generativeai: Gemini embeddings
- pydantic: Data validation
- python-dotenv: Environment management
