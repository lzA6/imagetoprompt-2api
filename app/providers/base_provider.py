from abc import ABC, abstractmethod
from typing import Dict, Any
from fastapi.responses import JSONResponse

class BaseProvider(ABC):
    @abstractmethod
    async def get_prompt_from_data_uri(self, data_uri: str) -> JSONResponse:
        pass

    @abstractmethod
    async def get_models(self) -> JSONResponse:
        pass
