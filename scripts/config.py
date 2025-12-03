import os
from typing import List
from pydantic import BaseModel, ValidationError
from scripts.utils import read_json

class RepoObject(BaseModel):
    url: str

class ConfigModel(BaseModel):
    repos: List[RepoObject] = []


def load_config(path: str) -> ConfigModel:
    raw = read_json(path)
    try:
        cfg = ConfigModel.model_validate(raw)
    except ValidationError as exc:
        raise
    return cfg


def is_git_repo(path: str) -> bool:
    return os.path.exists(path) and os.path.isdir(path) and os.path.exists(os.path.join(path, ".git"))