from setuptools import setup, find_packages

setup(
    name="embd",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "embd": ["templates/*.j2"],
    },
    include_package_data=True,
    install_requires=[
        "gitpython>=3.1.42",
        "pydantic>=2.5.3",
        "tree-sitter>=0.20.4",
        "tree-sitter-languages>=1.10.2",
        "pymongo>=4.6.1",
        "python-dotenv>=1.0.0",
        "google-generativeai>=0.3.2",
        "psycopg2-binary>=2.9.9",
        "sqlalchemy>=2.0.41",
        "pgvector>=0.4.1",
        "sqlalchemy-utils>=0.41.1",
        "beautifulsoup4>=4.12.0",
        "requests>=2.31.0",
        "markdown>=3.4.0",
    ],
    entry_points={
        "console_scripts": [
            "embd=embd.main:main",
            "embd-search=embd.cli.search:main",
            "embd-web=embd.cli.web:main",
            "embd-repo=embd.cli.repo:main",
            "embd-reset-db=embd.cli.reset_db:main",
        ],
    },
    author="David Arnold",
    description="A tool for embedding code constructs with Gemini and storing them in MongoDB",
    python_requires=">=3.8",
)
