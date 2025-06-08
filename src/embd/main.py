import os
from git import Repo, exc as git_exc
from pymongo import MongoClient
from . import parser
from . import config

def main():
    """Main function to process files and store in MongoDB"""
    # Setup MongoDB connection and ensure indexes
    from . import db
    db.init_indexes()
    
    # Get MongoDB collections
    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    constructs_collection = db[config.CONSTRUCTS_COLLECTION]
    imports_collection = db[config.IMPORTS_COLLECTION]

    # Get the repository path (current directory)
    repo_path = os.getcwd()
    
    try:
        repo = Repo(repo_path)
    except git_exc.InvalidGitRepositoryError:
        print("\nError: Not a git repository")
        print("\nPlease run 'embd' from within a git repository directory.")
        print("You can initialize a new git repository with 'git init' if needed.\n")
        return 1
    
    # Get all tracked Python and Markdown files
    files = parser.get_git_tracked_files(repo_path)
    
    # Process each file
    for file_path in files:
        print(f"Processing {file_path}...")
        constructs, imports = parser.parse_file(file_path, repo)
        
        # Store code constructs in MongoDB
        for construct in constructs:
            constructs_collection.update_one(
                {
                    'filename': construct.filename,
                    'line_start': construct.line_start,
                    'line_end': construct.line_end
                },
                {'$set': construct.model_dump()},
                upsert=True
            )
            print(f"Stored {construct.construct_type} from {construct.filename}")
            
        # Store imports in MongoDB
        for imp in imports:
            imports_collection.update_one(
                {
                    'filename': imp.filename,
                    'module_name': imp.module_name
                },
                {'$set': imp.model_dump()},
                upsert=True
            )
            print(f"Stored import of {imp.module_name} from {imp.filename}")

if __name__ == "__main__":
    main()
