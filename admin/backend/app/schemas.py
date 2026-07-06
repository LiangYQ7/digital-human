from pydantic import BaseModel


class DocOut(BaseModel):
    id: int
    title: str
    source_path: str
    status: str

    class Config:
        from_attributes = True
