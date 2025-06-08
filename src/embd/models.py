from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class CodeConstruct(BaseModel):
    filename: str = Field(description="Source filename of the code construct")
    git_commit: str = Field(description="Git commit hash of last change")
    code: str = Field(description="Extracted code from the construct")
    construct_type: str = Field(description="Type of code construct (e.g. function, class)")
    name: str = Field(description="Name of the function or class")
    description: str = Field(description="AI-generated description of the code construct")
    embedding: List[float] = Field(description="Gemini embedding of the code and description")
    line_start: int = Field(description="Starting line number in source file")
    line_end: int = Field(description="Ending line number in source file")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Import(BaseModel):
    filename: str = Field(description="Source filename containing the import")
    repository: str = Field(description="Name of the repository")
    module_name: str = Field(description="Name of the imported module")
    import_type: str = Field(description="Type of import (import or from-import)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
