from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ImportResponse(BaseModel):
    imported: int
    pages: int
