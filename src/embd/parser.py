"""Module for parsing code files and extracting embeddings."""
import os
import json
from typing import Optional, Any, List, Tuple, Dict
from git import Repo, Git
import tree_sitter
from tree_sitter_languages import get_language, get_parser
from google import genai
from google.genai import types
from . import models
from . import config
from . import pg_vector
import pathlib
from jinja2 import Template

ParseResult = Tuple[List[Tuple[models.CodeConstruct, List[float]]], List[models.Import]]

# Setup language parsers
PYTHON_LANGUAGE = get_language('python')
HCL_LANGUAGE = get_language('hcl')  # For Terraform HCL files
MARKDOWN_LANGUAGE = get_language('markdown')  # For Markdown files

# Terraform construct types
TERRAFORM_TYPES = {
    'module': 'terraform_module',
    'resource': 'terraform_resource',
    'data': 'terraform_data'
}

# Markdown construct types
MARKDOWN_TYPES = {
    'atx_heading': 'markdown_heading',
    'setext_heading': 'markdown_heading', 
    'paragraph': 'markdown_section',
    'fenced_code_block': 'markdown_code_block',
    'indented_code_block': 'markdown_code_block',
    'list': 'markdown_list',
    'blockquote': 'markdown_quote',
    'thematic_break': 'markdown_hr',
    'link_reference_definition': 'markdown_link_ref',
    'html_block': 'markdown_html'
}

# Setup Gemini client
client = genai.Client(api_key=config.GEMINI_API_KEY)

def get_embedding(text: str, description: str) -> List[float]:
    """Get embedding from Gemini API using the embeddings model"""
    default_embedding = [0.0] * config.EMBEDDING_DIMENSION  # Default embedding to return on error
    try:
        # Combine code and description for a richer embedding
        combined_text = f"{text}\n\nDescription: {description}"
        
        # Check token count before embedding
        token_count = client.models.count_tokens(
            model=config.DESCRIBING_MODEL,
            contents=combined_text,
        ).total_tokens
        token_count = token_count or 0  # Ensure token count is not None
        
        if token_count > config.EMBEDDING_TOKEN_LIMIT:
            # If over limit, truncate the text
            while token_count > config.EMBEDDING_TOKEN_LIMIT and len(text) > 100:
                text = text[:int(len(text) * 0.9)]  # Truncate by 10% each time
                combined_text = f"{text}\n\nDescription: {description}"
                token_count = client.models.count_tokens(
                    model=config.DESCRIBING_MODEL,
                    contents=combined_text,
                ).total_tokens
                token_count = token_count or 0  # Ensure token count is not None
            
            print(f"Warning: Input exceeded token limit ({token_count} > {config.EMBEDDING_TOKEN_LIMIT}). Using truncated text.")
        
       
        result = client.models.embed_content(
            model=config.EMBEDDING_MODEL,
            contents=combined_text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        
        if result is not None and result.embeddings:  # Check if embeddings exist
            first_embedding = result.embeddings[0]  # Get first embedding
            if first_embedding is not None and first_embedding.values:  # Check if values exist
                embedding_values = [float(val) for val in first_embedding.values]  # Convert to list of floats
                if len(embedding_values) == config.EMBEDDING_DIMENSION:
                    return embedding_values
                else:
                    print(f"Warning: Unexpected embedding dimension: {len(embedding_values)} (expected {config.EMBEDDING_DIMENSION})")
            else:
                print("Warning: First embedding has no values")
        else:
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
            # Handle regular imports (import x, y, z)
            for child in node.children:
                if child.type == 'dotted_name':
                    module_name = code_bytes[child.start_byte:child.end_byte].decode('utf-8')
                    imports.append(models.Import(
                        filename=filename,
                        repository=repo_name,
                        module_name=module_name,
                        import_type='import'
                    ))
                elif child.type == 'aliased_import':
                    # Handle 'import x as y'
                    for grandchild in child.children:
                        if grandchild.type == 'dotted_name':
                            module_name = code_bytes[grandchild.start_byte:grandchild.end_byte].decode('utf-8')
                            imports.append(models.Import(
                                filename=filename,
                                repository=repo_name,
                                module_name=module_name,
                                import_type='import'
                            ))
                            break

        elif node.type == 'import_from_statement':
            # Handle from-imports (from x import y, z)
            module_name = None
            for child in node.children:
                if child.type == 'dotted_name':
                    module_name = code_bytes[child.start_byte:child.end_byte].decode('utf-8')
                elif child.type == 'import_statement':
                    # Handle multiple imports in from statement
                    for grandchild in child.children:
                        if grandchild.type in ['dotted_name', 'identifier']:
                            imported_name = code_bytes[grandchild.start_byte:grandchild.end_byte].decode('utf-8')
                            if module_name:
                                imports.append(models.Import(
                                    filename=filename,
                                    repository=repo_name,
                                    module_name=f"{module_name}.{imported_name}",
                                    import_type='from-import'
                                ))
                        elif grandchild.type == 'aliased_import':
                            # Handle 'from x import y as z'
                            for great_grandchild in grandchild.children:
                                if great_grandchild.type in ['dotted_name', 'identifier']:
                                    imported_name = code_bytes[great_grandchild.start_byte:great_grandchild.end_byte].decode('utf-8')
                                    if module_name:
                                        imports.append(models.Import(
                                            filename=filename,
                                            repository=repo_name,
                                            module_name=f"{module_name}.{imported_name}",
                                            import_type='from-import'
                                        ))
                                    break

    def traverse_imports(node):
        if node.type in ['import_statement', 'import_from_statement']:
            process_import_node(node)
        for child in node.children:
            traverse_imports(child)

    traverse_imports(node)
    return imports

def get_code_description(code: str) -> str:
    """Get a description of the code using Gemini"""
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

def get_node_name(node, code_bytes) -> str:
    """Extract the name from a function or class definition node"""
    # The identifier (name) is the first child after any decorators
    for child in node.children:
        if child.type == 'identifier':
            return code_bytes[child.start_byte:child.end_byte].decode('utf-8')
    return "unnamed"  # Fallback in case we can't find the name

def generate_description(code: str, construct_type: str, name: str) -> str:
    """Generate a description for a code construct using Gemini.
    
    Args:
        code: The code content
        construct_type: Type of construct (e.g., terraform_module)
        name: Name of the construct
        
    Returns:
        Generated description string
    """
    try:
        # For Terraform code, use a more detailed prompt
        if construct_type.startswith('terraform_'):
            prompt = f"""Analyze this Terraform code and provide a detailed description:

{code}

Requirements:
1. Start with: "Terraform {construct_type.replace('terraform_', '')} that"
2. Explain what resources it creates/manages and their key configurations
3. Mention any important variables, data sources, or conditions
4. Include security-relevant details like IAM roles or network config
5. Be specific about the infrastructure being created

Example good descriptions:
- "Terraform module that provisions a highly available RDS cluster with automated backups and encrypted storage using customer-managed KMS keys"
- "Terraform resource that creates an EC2 instance in a private subnet with an IAM role for S3 access and custom user data script"

Your description:"""
        else:
            # Use existing template-based approach for non-Terraform code
            template = None
            for lang_config in config.LANGUAGES.values():
                if construct_type in lang_config['description_templates']:
                    template = lang_config['description_templates'][construct_type]
                    break
            
            if not template:
                return f"{construct_type} named {name}"
                
            prompt = f"""Analyze this code and complete the template:

{code}

Template: {template}
"""
        
        response = client.models.generate_content(
            model=config.DESCRIBING_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1  # Lower temperature for more consistent output
            )
        )
        
        if response:
            if hasattr(response, 'text') and response.text:
                description = response.text.strip()
                # For non-Terraform code using templates
                if not construct_type.startswith('terraform_') and template:
                    description = Template(template).render(purpose=description)
                return description
            
    except Exception as e:
        print(f"Error generating description: {str(e)}")
    
    # Fallback description
    if construct_type.startswith('terraform_'):
        return f"{construct_type.replace('terraform_', '')} named {name}"
    return f"{construct_type} named {name}"

def parse_file(filename: str, repo_path: Optional[str] = None, repo_name: Optional[str] = None) -> ParseResult:
    """Parse a file and extract code constructs and imports.
    
    Args:
        filename: Path to file to parse
        repo_path: Optional git repository path for commit info
        repo_name: Optional repository name to use for constructs. If not provided and repo_path exists,
                  will use the basename of repo_path.
        
    Returns:
        Tuple of (list of (CodeConstruct, embedding) tuples, list of Imports)
    """
    try:
        with open(filename, 'rb') as f:
            code_bytes = f.read()
            
        git_commit = ''
        # Use provided repo_name or extract from path if available
        if repo_name is None and repo_path:
            repo_name = os.path.basename(repo_path)
            
        if repo_path:
            try:
                repo = Repo(repo_path)
                git_commit = repo.head.commit.hexsha
            except Exception as e:
                print(f"Warning: Could not get git info: {e}")
        
        # Initialize results
        constructs_with_embeddings = []
        imports = []
        
        # Check file type and parse accordingly
        if filename.endswith(('.tf', '.tfvars')):
            # Parse Terraform files
            constructs = extract_terraform_constructs(code_bytes, filename)
            
            # Generate descriptions and embeddings for each construct
            for construct, desc_template in constructs:
                construct.git_commit = git_commit
                construct.repository = repo_name or ''  # Set repository name here
                
                # Generate description using template
                description = generate_description(
                    code=construct.code,
                    construct_type=construct.construct_type,
                    name=construct.name
                )
                construct.description = description
                
                # Generate embedding
                embedding = get_embedding(construct.code, description)
                constructs_with_embeddings.append((construct, embedding))
                
        elif filename.endswith('.py'):
            # Handle Python files
            parser = get_parser('python')
            language = get_language('python')
            parser.set_language(language)
            tree = parser.parse(code_bytes)
            
            # Extract imports first (for Python files only)
            imports = extract_imports(tree.root_node, code_bytes, filename, repo_name or '')
            
            def extract_construct(node, content_bytes):
                """Extract code construct from a node"""
                if node.type in ['function_definition', 'class_definition']:
                    code_text = content_bytes[node.start_byte:node.end_byte].decode('utf-8')
                    construct_name = get_node_name(node, content_bytes)
                    description = get_code_description(code_text)
                    embedding = get_embedding(code_text, description)
                    
                    # Create Pydantic construct
                    construct = models.CodeConstruct(
                        filename=filename,
                        repository=repo_name or '',  # Set repository name
                        git_commit=git_commit,
                        code=code_text,
                        name=construct_name,
                        construct_type=node.type,
                        description=description,
                        embedding=embedding,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1
                    )
                    constructs_with_embeddings.append((construct, construct.embedding))
            
            # Visit each node in the tree
            def visit_node(node):
                extract_construct(node, code_bytes)
                for child in node.children:
                    visit_node(child)
                    
            visit_node(tree.root_node)
            
        elif filename.endswith('.md'):
            # Handle Markdown files
            parser = get_parser('markdown')
            parser.set_language(MARKDOWN_LANGUAGE)
            tree = parser.parse(code_bytes)
            
            # Extract markdown constructs and process them
            constructs_and_embeddings = extract_markdown_constructs(tree.root_node, code_bytes, filename)
            for construct, embedding in constructs_and_embeddings:
                # Fill in repository info
                construct.git_commit = git_commit
                construct.repository = repo_name or ''
                constructs_with_embeddings.append((construct, embedding))
                
        return constructs_with_embeddings, imports
        
    except Exception as e:
        print(f"Error parsing {filename}: {str(e)}")
        return [], []

def parse_terraform_block(node, code_bytes) -> Optional[Dict[str, Any]]:
    """Parse a Terraform block (resource, data, or module) into a dictionary."""
    block_type = None
    block_name = None
    
    # First child is the block type (resource, module, data)
    type_node = node.children[0] if node.children else None
    if type_node:
        block_type = code_bytes[type_node.start_byte:type_node.end_byte].decode('utf-8')
    
    # Second child is usually the resource type or module name
    if len(node.children) > 1:
        name_node = node.children[1]
        if name_node.type == 'string_lit':
            # Remove quotes from string literals
            block_name = code_bytes[name_node.start_byte + 1:name_node.end_byte - 1].decode('utf-8')
        else:
            block_name = code_bytes[name_node.start_byte:name_node.end_byte].decode('utf-8')
            
    if not block_type or not block_name:
        return None
        
    return {
        'type': block_type,
        'name': block_name,
        'code': code_bytes[node.start_byte:node.end_byte].decode('utf-8'),
        'start_line': node.start_point[0] + 1,
        'end_line': node.end_point[0] + 1
    }

def extract_terraform_constructs(code_bytes: bytes, filename: str) -> List[Tuple[models.CodeConstruct, str]]:
    """Extract Terraform constructs (modules, resources, data sources) from code."""
    constructs = []
    
    # Try parsing as HCL first
    try:
        parser = get_parser('hcl')
        tree = parser.parse(code_bytes)
        
        # Traverse the AST
        cursor = tree.walk()
        
        def visit_node():
            node = cursor.node
            
            # Check if this is a block (resource, module, or data)
            if node.type == 'block':
                block_info = parse_terraform_block(node, code_bytes)
                if block_info and block_info['type'] in TERRAFORM_TYPES:
                    construct_type = TERRAFORM_TYPES[block_info['type']]
                    
                    # Create CodeConstruct object
                    construct = models.CodeConstruct(
                        filename=filename,
                        repository='',  # Will be filled in by parse_file
                        git_commit='',  # Will be filled in by parse_file
                        code=block_info['code'],
                        construct_type=construct_type,
                        name=block_info['name'],
                        description='',  # Will be generated by AI
                        line_start=block_info['start_line'],
                        line_end=block_info['end_line'],
                        embedding=[]  # Will be generated later
                    )
                    
                    # Get description template based on type
                    desc_template = config.LANGUAGES['terraform']['description_templates'][construct_type]
                    constructs.append((construct, desc_template))
            
            # Visit children
            if cursor.goto_first_child():
                while True:
                    visit_node()
                    if not cursor.goto_next_sibling():
                        break
                cursor.goto_parent()
        
        visit_node()
        return constructs
        
    except Exception as e:
        # If HCL parsing fails, try JSON
        try:
            tf_json = json.loads(code_bytes)
            json_constructs = []
            
            # Process each section (resource, module, data)
            for section_type, section_data in tf_json.items():
                if section_type not in TERRAFORM_TYPES:
                    continue
                    
                for resource_type, resources in section_data.items():
                    for resource_name, resource_config in resources.items():
                        construct_type = TERRAFORM_TYPES[section_type]
                        
                        # Create JSON representation
                        code = json.dumps({
                            section_type: {
                                resource_type: {
                                    resource_name: resource_config
                                }
                            }
                        }, indent=2)
                        
                        # Create CodeConstruct object
                        construct = models.CodeConstruct(
                            filename=filename,
                            repository='',  # Will be filled in by parse_file
                            git_commit='',  # Will be filled in by parse_file
                            code=code,
                            construct_type=construct_type,
                            name=f"{resource_type}.{resource_name}",
                            description='',  # Will be generated by AI
                            line_start=1,  # JSON doesn't preserve line numbers
                            line_end=len(code.split('\n')),
                            embedding=[]  # Will be generated later
                        )
                        
                        # Get description template
                        desc_template = config.LANGUAGES['terraform']['description_templates'][construct_type]
                        json_constructs.append((construct, desc_template))
            
            return json_constructs
            
        except json.JSONDecodeError:
            print(f"Failed to parse {filename} as either HCL or JSON")
            return []

def extract_markdown_constructs(node, code_bytes: bytes, filename: str) -> List[Tuple[models.CodeConstruct, List[float]]]:
    """Extract markdown sections from a markdown file.
    
    Args:
        node: The root AST node
        code_bytes: Raw file contents
        filename: Source filename
        
    Returns:
        List of tuples containing (CodeConstruct, embedding)
    """
    constructs = []
    current_section = None
    
    def visit_node(node) -> None:
        nonlocal current_section
        
        # Get node text
        node_text = code_bytes[node.start_byte:node.end_byte].decode('utf-8')
        
        # Handle different markdown elements
        if node.type in MARKDOWN_TYPES:
            construct_type = MARKDOWN_TYPES[node.type]
            
            # Extract name/title for the section
            name = ''
            if node.type in ['atx_heading', 'setext_heading']:
                # For headings, use the heading text as name
                name = node_text.strip('#').strip()
            elif node.type in ['fenced_code_block', 'indented_code_block']:
                # For code blocks, look for language info
                first_line = node_text.split('\n')[0]
                if '```' in first_line:
                    name = first_line.strip('`').strip()
                else:
                    name = 'code'
            else:
                # For other elements, use first line or truncate
                name = node_text.split('\n')[0][:50]
            
            # Create the construct
            construct = models.CodeConstruct(
                filename=filename,
                repository='',  # Will be set by caller
                git_commit='',  # Will be set by caller
                code=node_text,
                construct_type=construct_type,
                name=name,
                description='',  # Will be generated by caller
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                embedding=[]  # Will be generated by caller
            )
            
            # Generate initial description 
            if node.type in ['atx_heading', 'setext_heading']:
                description = f"Markdown heading: {name}"
            elif node.type in ['fenced_code_block', 'indented_code_block']:
                lang = name if name != 'code' else 'unknown'
                description = f"Code block in {lang}"
            else:
                description = f"Markdown {construct_type}"
            
            # Create embedding and store construct
            embedding = get_embedding(node_text, description)
            constructs.append((construct, embedding))
        
        # Recursively visit children
        for child in node.children:
            visit_node(child)
    
    # Start traversal from root
    visit_node(node)
    return constructs
