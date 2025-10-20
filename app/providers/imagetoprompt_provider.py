import time
import uuid
import mimetypes
from typing import Dict, Any

import httpx
import aiohttp
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings

class ImageToPromptProvider:
    UPSTREAM_URL = "https://www.imagetoprompt.app/api/generate-prompt"

    def __init__(self):
        self.client: httpx.AsyncClient = None
        self.session: aiohttp.ClientSession = None

    async def initialize(self):
        self.client = httpx.AsyncClient(timeout=settings.API_REQUEST_TIMEOUT)
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.client:
            await self.client.aclose()
        if self.session:
            await self.session.close()

    async def url_to_data_uri(self, url: str) -> str:
        """从 URL 下载图片并转换为 Base64 Data URI"""
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                image_bytes = await response.read()
                mime_type = response.content_type or mimetypes.guess_type(url)[0] or "image/png"
                
                import base64
                base64_data = base64.b64encode(image_bytes).decode('utf-8')
                return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            logger.error(f"下载或转换图片失败: {url}, 错误: {e}")
            raise HTTPException(status_code=400, detail=f"无法从 URL 下载或处理图片: {e}")

    async def get_prompt_internal(self, data_uri: str, language: str, structured_prompt: str) -> str:
        """
        核心内部函数，从 Data URI 获取提示词。
        :param data_uri: 图片的 Base64 Data URI。
        :param language: 目标语言代码 (例如 'en', 'zh-CN')。
        :param structured_prompt: 是否使用结构化提示 ('yes' 或 'no')。
        :return: 生成的提示词字符串。
        """
        headers = self._prepare_headers()
        payload = {
            "imageBase64": data_uri,
            "language": language,
            "structuredPrompt": structured_prompt
        }

        try:
            logger.info(f"正在向上游 API 发送请求... 语言: {language}, 结构化: {structured_prompt}")
            response = await self.client.post(self.UPSTREAM_URL, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if not data.get("success") or "prompt" not in data:
                error_detail = data.get('prompt', '未知错误')
                logger.error(f"上游 API 返回失败: {error_detail}")
                raise HTTPException(status_code=502, detail=f"上游 API 返回失败: {error_detail}")

            prompt = data["prompt"]
            logger.success(f"成功获取提示词: {prompt[:100]}...")
            return prompt

        except httpx.HTTPStatusError as e:
            logger.error(f"请求上游 API 失败，状态码: {e.response.status_code}, 响应: {e.response.text}")
            raise HTTPException(status_code=502, detail=f"上游服务错误: {e.response.text}")
        except Exception as e:
            logger.error(f"处理请求时发生未知错误: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

    async def get_prompt_as_chat_completion(self, data_uri: str, language: str, structured_prompt: str) -> JSONResponse:
        """为聊天端点调用核心函数并格式化为 OpenAI 响应。"""
        prompt = await self.get_prompt_internal(data_uri, language, structured_prompt)
        
        chat_response = {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": settings.DEFAULT_MODEL,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": prompt,
                },
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        }
        return JSONResponse(content=chat_response)

    def _prepare_headers(self) -> Dict[str, str]:
        return {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json",
            "Origin": "https://www.imagetoprompt.app",
            "Referer": "https://www.imagetoprompt.app/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        }

    async def get_models(self) -> JSONResponse:
        model_data = {
            "object": "list",
            "data": [
                {"id": name, "object": "model", "created": int(time.time()), "owned_by": "lzA6"}
                for name in settings.KNOWN_MODELS
            ]
        }
        return JSONResponse(content=model_data)
