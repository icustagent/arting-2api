# main.py (修正版)
import sys
import time # <--- 修正：导入 time 模块
import uuid # <--- 修正：导入 uuid 模块
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import settings
from app.providers.arting_provider import ArtingProvider

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
provider = ArtingProvider()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"应用启动中... {settings.APP_NAME} v{settings.APP_VERSION_MULTI_INTERFACE}")
    logger.info("服务已进入 'Cloudscraper' 模式，将自动处理潜在的 Cloudflare 挑战。")
    logger.info(f"API 服务将在 http://localhost:{settings.NGINX_PORT} 上可用")
    logger.info(f"Web UI 测试界面已启用，请访问 http://localhost:{settings.NGINX_PORT}/")
    yield
    logger.info("应用关闭。")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION_MULTI_INTERFACE,
    description=settings.DESCRIPTION_MULTI_INTERFACE,
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

# 1. OpenAI 原生图像接口
@app.post("/v1/images/generations", dependencies=[Depends(verify_api_key)])
async def image_generations(request: Request):
    try:
        request_data = await request.json()
        image_urls = await provider.generate_image_urls(request_data)
        return JSONResponse(content={
            "created": int(time.time()), # <--- 此处需要 time 模块
            "data": [{"url": url} for url in image_urls]
        })
    except Exception as e:
        logger.error(f"处理 /v1/images/generations 请求时发生顶层错误: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

# 2. 聊天客户端适配接口
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: Request):
    try:
        request_data = await request.json()
        
        messages = request_data.get("messages", [])
        last_user_message = next((m['content'] for m in reversed(messages) if m.get('role') == 'user'), None)
        if not last_user_message:
            raise HTTPException(status_code=400, detail="在 'messages' 中未找到用户消息。")

        image_request_data = {"prompt": last_user_message, "n": 1}
        
        logger.info(f"通过聊天接口适配图像生成, prompt: '{last_user_message[:50]}...'")
        image_urls = await provider.generate_image_urls(image_request_data)

        if not image_urls:
            raise HTTPException(status_code=502, detail="从上游服务生成图像失败。")
            
        response_content = f"![]({image_urls[0]})"
        
        chat_response = {
            "id": f"chatcmpl-{uuid.uuid4()}", # <--- 此处需要 uuid 模块
            "object": "chat.completion",
            "created": int(time.time()), # <--- 此处需要 time 模块
            "model": request_data.get("model", "arting-ai-pro"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": response_content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        return JSONResponse(content=chat_response)

    except Exception as e:
        logger.error(f"处理 /v1/chat/completions 请求时发生顶层错误: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

# 3. Stable Diffusion WebUI 适配接口
@app.post("/sdapi/v1/txt2img", dependencies=[Depends(verify_api_key)])
async def sd_api_txt2img(request: Request):
    try:
        sd_request_data = await request.json()
        logger.info("接收到 SD WebUI API 请求...")
        
        image_request_data = provider.map_sd_to_arting_request(sd_request_data)
        
        image_urls = await provider.generate_image_urls(image_request_data)
        
        b64_images = await provider.fetch_images_as_base64(image_urls)
        
        sd_response = {
            "images": b64_images,
            "parameters": sd_request_data,
            "info": ""
        }
        return JSONResponse(content=sd_response)

    except Exception as e:
        logger.error(f"处理 /sdapi/v1/txt2img 请求时发生顶层错误: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    model_data = await provider.get_models()
    return JSONResponse(content=model_data)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="UI 文件 (static/index.html) 未找到。")
