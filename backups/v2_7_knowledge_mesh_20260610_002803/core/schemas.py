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
