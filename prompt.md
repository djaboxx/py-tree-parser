# Python Code Parser
create a script that lists all files that are tracked by git, from those files find the files
that are either markdown or python. parse them using tree-sitter. Use the AST Map to extract logical chunks 
out of original source code. Store these chunks in mongodb. 

Create Pydantic Models for extracted code constructs. 
In mongodb, we want to track the following for each type of construct:
* Git Commit of last change
* Filename of extracted code construct
* extracted code from code construct
* Embedding from Gemini

We have a mongodb server setup in #file:docker-compose.yml in the infra directory.
We will use this shared infrastructure for the backend code of this script.

## Create Embedding
https://ai.google.dev/gemini-api/docs/embeddings
```python
from google import genai

client = genai.Client(api_key="GEMINI_API_KEY")

result = client.models.embed_content(
        model="gemini-embedding-exp-03-07",
        contents="What is the meaning of life?")

print(result.embeddings)
```

## Find matching files
https://gitpython.readthedocs.io/en/0.1.7/reference.html#module-git.cmd

```python
Git
classgit.cmd.Git(git_dir=None)
The Git class manages communication with the Git binary.

It provides a convenient interface to calling the Git binary, such as in:

g = Git( git_dir )
g.init()                               # calls 'git init' program
rval = g.ls_files()            # calls 'git ls-files' program
```

## Parse Python code with tree-sitter
https://github.com/tree-sitter/py-tree-sitter/tree/master

```python
from tree_sitter import Parser
from tree_sitter_languages import get_language, get_parser

# Get the Python language and parser
language = get_language('python')
parser = get_parser('python')

# Python code to parse
code = """
def hello(name):
    print(f"Hello, {name}!")
"""

# Parse the code
tree = parser.parse(bytes(code, "utf8"))

# Get the root node of the parse tree
root_node = tree.root_node

# Print the root node type
print(f"Root node type: {root_node.type}")

# Iterate through the children of the root node
for child in root_node.children:
    print(f"  Child node type: {child.type}")
    if child.type == "function_definition":
      for grand_child in child.children:
        print(f"    Grandchild node type: {grand_child.type}")
        if grand_child.type == "identifier":
          print(f"      Function name: {grand_child.text.decode('utf8')}")
```