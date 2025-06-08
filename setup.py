from setuptools import setup, find_packages

setup(
    name="embd",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "gitpython>=3.1.42",
        "pydantic>=2.5.3",
        "tree-sitter>=0.20.4",
        "tree-sitter-languages>=1.10.2",
        "pymongo>=4.6.1",
        "python-dotenv>=1.0.0",
        "google-generativeai>=0.3.2",
    ],
    entry_points={
        "console_scripts": [
            "embd=embd.main:main",
        ],
    },
    author="David Arnold",
    description="A tool for embedding code constructs with Gemini and storing them in MongoDB",
    python_requires=">=3.8",
)
