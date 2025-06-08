from pymongo import MongoClient, ASCENDING
from . import config

def init_indexes():
    """Initialize MongoDB indexes for optimal performance"""
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    
    # Indexes for code_constructs collection
    constructs = db[config.CONSTRUCTS_COLLECTION]
    constructs.create_index([
        ("filename", ASCENDING),
        ("line_start", ASCENDING),
        ("line_end", ASCENDING)
    ], unique=True)
    constructs.create_index([("construct_type", ASCENDING)])
    constructs.create_index([("git_commit", ASCENDING)])
    constructs.create_index([("created_at", ASCENDING)])
    constructs.create_index([("updated_at", ASCENDING)])
    
    # Indexes for imports collection
    imports = db[config.IMPORTS_COLLECTION]
    imports.create_index([
        ("filename", ASCENDING),
        ("module_name", ASCENDING)
    ], unique=True)
    imports.create_index([("repository", ASCENDING)])
    imports.create_index([("module_name", ASCENDING)])
    imports.create_index([("import_type", ASCENDING)])
    imports.create_index([("created_at", ASCENDING)])
    imports.create_index([("updated_at", ASCENDING)])

if __name__ == "__main__":
    init_indexes()
