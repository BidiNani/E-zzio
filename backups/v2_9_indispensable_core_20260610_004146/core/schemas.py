from pydantic import BaseModel

class Prompt(BaseModel):
    text: str
    speed: str = "auto"

class MemoryQuery(BaseModel):
    query: str
    limit: int = 10

class CreateFileRequest(BaseModel):
    filename: str
    content: str

class CloudGetRequest(BaseModel):
    provider: str
    path: str
    params: dict = {}

class KnowledgeRequest(BaseModel):
    provider: str
    query: str
    lang: str = "fr"
    limit: int = 5
    compress: bool = True
    params: dict = {}

class CompressRequest(BaseModel):
    text: str
    max_chars: int = 4000
    mode: str = "extractive"
