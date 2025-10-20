import sys
import re
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends, Header, File, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import settings
from app.providers.imagetoprompt_provider import ImageToPromptProvider

# --- 配置 Loguru ---
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True
)

# --- 全局 Provider 实例 ---
provider = ImageToPromptProvider()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"应用启动中... {settings.APP_NAME} v{settings.APP_VERSION}")
    await provider.initialize()
    logger.info(f"服务将在 http://localhost:{settings.NGINX_PORT} 上可用")
    logger.info(f"Web UI 测试界面已启用，请访问 http://localhost:{settings.NGINX_PORT}/")
    yield
    await provider.close()
    logger.info("应用关闭。")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan
)

# --- 挂载静态文件目录 ---
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 安全依赖 ---
async def verify_api_key(authorization: Optional[str] = Header(None)):
    if settings.API_MASTER_KEY and settings.API_MASTER_KEY != "1":
        if not authorization or "bearer" not in authorization.lower():
            raise HTTPException(status_code=401, detail="需要 Bearer Token 认证。")
        token = authorization.split(" ")[-1]
        if token != settings.API_MASTER_KEY:
            raise HTTPException(status_code=403, detail="无效的 API Key。")

# --- API 路由 ---
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: Request):
    """
    兼容 Cherry Studio 等客户端的聊天接口。
    它会从消息中提取图片 URL 或 Base64 Data URI，然后调用核心服务。
    同时，它会从请求体中提取 'language' 和 'structured_prompt' 参数。
    """
    try:
        request_data = await request.json()
        messages = request_data.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="请求体中缺少 'messages' 字段。")

        # 提取语言和结构化提示参数，如果未提供则使用默认值
        language = request_data.get("language", "en")
        structured_prompt = request_data.get("structured_prompt", "yes")

        # 查找最后一个用户消息中的图片信息
        image_data_uri = None
        url_pattern = re.compile(r'https?://[^\s\)]+')
        data_uri_pattern = re.compile(r'data:image/[a-zA-Z]+;base64,[a-zA-Z0-9+/=]+')

        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    # 尝试匹配 Data URI
                    data_uri_match = data_uri_pattern.search(content)
                    if data_uri_match:
                        image_data_uri = data_uri_match.group(0)
                        logger.info("从消息内容中提取到 Base64 Data URI。")
                        break
                    
                    # 尝试匹配 URL
                    url_match = url_pattern.search(content)
                    if url_match:
                        image_url = url_match.group(0)
                        logger.info(f"从消息内容中提取到图片 URL: {image_url}")
                        image_data_uri = await provider.url_to_data_uri(image_url)
                        break
        
        if not image_data_uri:
            raise HTTPException(status_code=400, detail="在用户消息中未找到有效的图片 URL 或 Base64 Data URI。")

        return await provider.get_prompt_as_chat_completion(image_data_uri, language, structured_prompt)

    except Exception as e:
        logger.error(f"处理聊天请求时发生顶层错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

@app.post("/api/generate-from-upload", dependencies=[Depends(verify_api_key)])
async def generate_from_upload(
    image: UploadFile = File(...),
    language: str = Form("en"),
    structured_prompt: str = Form("yes")
):
    """
    专为 Web UI 设计的接口，处理文件上传。
    """
    try:
        image_bytes = await image.read()
        import base64
        mime_type = image.content_type
        base64_data = base64.b64encode(image_bytes).decode('utf-8')
        data_uri = f"data:{mime_type};base64,{base64_data}"
        
        prompt = await provider.get_prompt_internal(data_uri, language, structured_prompt)
        return JSONResponse(content={"prompt": prompt})
    except Exception as e:
        logger.error(f"处理文件上传时发生错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.get("/v1/models", dependencies=[Depends(verify_api_key)], response_class=JSONResponse)
async def list_models():
    return await provider.get_models()

# --- Web UI 路由 ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="UI 文件 (static/index.html) 未找到。")
