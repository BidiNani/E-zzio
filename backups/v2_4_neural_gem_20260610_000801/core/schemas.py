from pydantic import BaseModel

class Prompt(BaseModel):
    text: str
    speed: str = "normal"

class MemoryQuery(BaseModel):
    query: str
    limit: int = 10

class CreateFileRequest(BaseModel):
    filename: str
    content: str
