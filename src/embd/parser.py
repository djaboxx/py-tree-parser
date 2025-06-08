import os
from typing import Optional, Any, List, Tuple
from git import Repo, Git
import tree_sitter
from tree_sitter_languages import get_language, get_parser
from google import genai
from google.genai import types
from . import models
from . import config
import pathlib
from jinja2 import Template

# Setup Gemini client
client = genai.Client(api_key=config.GEMINI_API_KEY)

def get_embedding(text: str, description: str) -> List[float]:
    """Get embedding from Gemini API using the embeddings model"""
    default_embedding = [0.0]  # Default embedding to return on error
    
    try:
        # Combine code and description for a richer embedding
        combined_text = f"{text}\n\nDescription: {description}"
        result: Optional[Any] = client.models.embed_content(
            model=config.EMBEDDING_MODEL,
            contents=combined_text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        if (result is not None and 
            hasattr(result, 'embeddings') and 
            result.embeddings is not None):
            embeddings = result.embeddings
            if len(embeddings) > 0 and hasattr(embeddings[0], 'values'):
                embedding = [float(val) for val in embeddings[0].values]
                if embedding:  # Make sure we got some values
                    return embedding
        print(f"Warning: Could not generate embedding for text: {combined_text[:100]}...")
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
    
    return default_embedding

def get_git_tracked_files(repo_path: str) -> List[str]:
    """Get all files tracked by git"""
    g = Git(repo_path)
    files = g.ls_files().split('\n')
    return [f for f in files if f.endswith(config.CODE_FILE_PATTERNS)]

def extract_imports(node, code_bytes, filename: str, repo_name: str) -> List[models.Import]:
    """Extract import statements from an AST node"""
    imports = []
    
    def process_import_node(node):
        if node.type == 'import_statement':
            # Handle regular imports (import x)
            for child in node.children:
                if child.type == 'dotted_name':
                    module_name = code_bytes[child.start_byte:child.end_byte].decode('utf-8')
                    imports.append(models.Import(
                        filename=filename,
                        repository=repo_name,
                        module_name=module_name,
                        import_type='import'
                    ))
        elif node.type == 'import_from_statement':
            # Handle from-imports (from x import y)
            module_name = None
            for child in node.children:
                if child.type == 'dotted_name':
                    module_name = code_bytes[child.start_byte:child.end_byte].decode('utf-8')
                elif child.type == 'import_statement':
                    imported_names = code_bytes[child.start_byte:child.end_byte].decode('utf-8')
                    if module_name:
                        imports.append(models.Import(
                            filename=filename,
                            repository=repo_name,
                            module_name=f"{module_name}.{imported_names}",
                            import_type='from-import'
                        ))

    def traverse_imports(node):
        if node.type in ['import_statement', 'import_from_statement']:
            process_import_node(node)
        for child in node.children:
            traverse_imports(child)

    traverse_imports(node)
    return imports

def parse_file(file_path: str, repo: Repo) -> Tuple[List[models.CodeConstruct], List[models.Import]]:
    """Parse a file and extract code constructs and imports"""
    constructs = []
    
    # Get file content and repo name
    with open(file_path, 'rb') as f:
        content = f.read()
    repo_name = os.path.basename(repo.working_dir)

    # Get the last commit that modified this file
    last_commit = next(repo.iter_commits(paths=file_path))
    
    # Setup parser based on file type
    if file_path.endswith('.py'):
        parser = get_parser('python')
        language = get_language('python')
    else:  # Markdown
        parser = get_parser('markdown')
        language = get_language('markdown')
    
    parser.set_language(language)
    tree = parser.parse(content)
    
    # Extract imports first
    imports = extract_imports(tree.root_node, content, file_path, repo_name) if file_path.endswith('.py') else []
    
    def extract_construct(node, code_bytes):
        """Extract code construct from a node"""
        if node.type in ['function_definition', 'class_definition']:
            code_text = code_bytes[node.start_byte:node.end_byte].decode('utf-8')
            description = get_code_description(code_text)
            construct = models.CodeConstruct(
                filename=file_path,
                git_commit=last_commit.hexsha,
                code=code_text,
                construct_type=node.type,
                description=description,
                embedding=get_embedding(code_text, description),
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1
            )
            constructs.append(construct)
            
    def traverse_tree(node):
        """Traverse the AST"""
        if node.type in ['function_definition', 'class_definition']:
            extract_construct(node, content)
        for child in node.children:
            traverse_tree(child)
    
    traverse_tree(tree.root_node)
    return constructs, imports

def get_code_description(code: str) -> str:
    """Get a natural language description of code using Gemini"""
    try:
        # Create a prompt for Gemini to describe the code
        with open(
            os.path.join(
                os.path.dirname(__file__),
                'templates/code_description.j2'
            ), 
            'r') as f:
            prompt = Template(f.read()).render(code=code)

        response = client.models.generate_content(
            model=config.DESCRIBING_MODEL,  # Using the same model for consistency
            contents=prompt
        )

        if response and response.text:
            return response.text.strip()
            
        print(f"Warning: Could not generate description for code: {code[:100]}...")
    except Exception as e:
        print(f"Error generating description: {str(e)}")
    
    return "No description available"
