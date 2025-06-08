"""Script to reinitialize database tables and vector indexes."""
from .database import engine
from .models import CodeEmbedding

def main():
    """Reinitialize database tables and indexes."""
    print("Creating vector indexes and tables...")
    CodeEmbedding.create_indexes(engine)
    print("Done!")

if __name__ == "__main__":
    main()