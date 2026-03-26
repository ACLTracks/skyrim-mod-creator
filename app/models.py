from pydantic import BaseModel, Field


class ModRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)
    mod_name: str = Field(min_length=3, max_length=80)


class ModResponse(BaseModel):
    mod_name: str
    plugin_path: str
    script_path: str
    summary: str
