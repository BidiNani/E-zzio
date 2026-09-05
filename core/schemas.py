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


class ImagePromptRequest(BaseModel):
    prompt: str
    style: str = "cinematic"
    negative: str = ""


class VideoPlanRequest(BaseModel):
    prompt: str
    duration_sec: int = 4
    fps: int = 8
    style: str = "cinematic"


class VideoFromFolderRequest(BaseModel):
    folder: str
    fps: int = 8
    output_name: str = "ezzio_video_cpu.mp4"


class MobileManifestRequest(BaseModel):
    app_name: str = "E-ZZIO"
    app_id: str = "com.ezzio.local"


class VisionPathRequest(BaseModel):
    path: str
    prompt: str = ""
    mode: str = "auto"


class ApprovalDecision(BaseModel):
    decision: str
    approver: str = "system"
    reason: str = ""
    metadata: dict = {}


class CreateRunRequest(BaseModel):
    prompt: str
    profile: str = "prive"

