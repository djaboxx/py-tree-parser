import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL settings
POSTGRES_URI = os.getenv(
    "POSTGRES_URI", 
    "postgresql://postgres:postgres@localhost:5432/code_embed"
)

# Gemini settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "text-embedding-004"  # Latest embedding model
DESCRIBING_MODEL = "gemini-2.0-flash"  # For descriptions
EMBEDDING_DIMENSION = 768  # Dimension for model
EMBEDDING_TOKEN_LIMIT = 8192  # Max tokens for embedding

# Similarity thresholds
DEFAULT_MIN_SIMILARITY = 0.7  # Default minimum similarity score for matches
DEFAULT_MAX_RESULTS = 10     # Default maximum number of results

# File patterns and languages
CODE_FILE_PATTERNS = ('.py', '.md', '.tf', '.tfvars', '.html', '.htm')

# Language-specific settings
LANGUAGES = {
    'python': {
        'extensions': ['.py'],
        'description_templates': {
            'function_definition': 'Python function that {{purpose}}',
            'class_definition': 'Python class that {{purpose}}',
            'whole_file': 'Complete Python file that {{purpose}}'
        }
    },
    'terraform': {
        'extensions': ['.tf', '.tfvars'],
        'description_templates': {
            'terraform_module': 'Terraform module that {{purpose}}',
            'terraform_resource': 'Terraform resource that {{purpose}}',
            'terraform_data': 'Terraform data source that {{purpose}}',
            'whole_file': 'Complete Terraform file that {{purpose}}'
        }
    },
    'markdown': {
        'extensions': ['.md'],
        'description_templates': {
            'markdown_heading': 'Markdown heading that {{purpose}}',
            'markdown_section': 'Markdown section that {{purpose}}',
            'markdown_code_block': 'Markdown code block that {{purpose}}',
            'whole_file': 'Complete Markdown document that {{purpose}}'
        }
    },
    'html': {
        'extensions': ['.html', '.htm'],
        'description_templates': {
            'web_html_document': 'Complete HTML document that {{purpose}}',
            'web_html_section': 'HTML section that {{purpose}}',
            'web_html_code_block': 'HTML code block that {{purpose}}',
            'whole_file': 'Complete HTML document that {{purpose}}'
        }
    },
    'general': {
        'extensions': ['*'],
        'description_templates': {
            'whole_file': 'Complete file that {{purpose}}'
        }
    }
}
