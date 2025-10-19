# app/providers/arting_provider.py
import time
import asyncio
import base64
import json
from typing import Dict, Any, Optional, List, Tuple

import cloudscraper
import aiohttp
from fastapi import HTTPException
from loguru import logger # 导入 loguru

from app.core.config import settings

class ArtingProvider:
    BASE_URL = "https://api.arting.ai/api/cg/text-to-image"

    def __init__(self):
        self.scraper = cloudscraper.create_scraper()

    def _prepare_headers(self) -> Dict[str, str]:
        if not settings.ARTING_AUTH_TOKEN:
            raise ValueError("ARTING_AUTH_TOKEN 未在 .env 文件中配置。")
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Authorization": settings.ARTING_AUTH_TOKEN,
            "Content-Type": "application/json",
            "Origin": "https://arting.ai",
            "Referer": "https://arting.ai/",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        }

    def _parse_size(self, size_str: Optional[str]) -> Tuple[int, int]:
        if size_str and 'x' in size_str:
            try:
                width, height = map(int, size_str.split('x'))
                return width, height
            except ValueError:
                logger.warning(f"无效的尺寸格式: '{size_str}', 使用默认值 512x768。")
        return 512, 768

    async def _start_task(self, payload: Dict[str, Any]) -> str:
        url = f"{self.BASE_URL}/create"
        headers = self._prepare_headers()
        
        logger.info("==================== [REQUEST TO ARING /create] ====================")
        logger.info(f"URL: POST {url}")
        logger.info(f"Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        logger.info("====================================================================")
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, lambda: self.scraper.post(url, headers=headers, json=payload, timeout=settings.API_REQUEST_TIMEOUT)
        )
        
        try:
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 100000 or "data" not in data or "request_id" not in data["data"]:
                raise Exception(f"提交任务失败: {data.get('message', '未知错误')}")
            
            request_id = data["data"]["request_id"]
            logger.info(f"任务提交成功, Request ID: {request_id}")
            return request_id

        except json.JSONDecodeError:
            logger.error("!!!!!!!!!!!! [UPSTREAM ERROR - /create] !!!!!!!!!!!!")
            logger.error("上游返回的不是有效的 JSON。很可能触发了 Cloudflare 防护。")
            logger.error(f"Status Code: {response.status_code}")
            logger.error(f"Response Body (HTML):\n{response.text}")
            logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            raise Exception("上游 API 响应格式错误，可能是 Cloudflare 拦截。")
        except Exception as e:
            logger.error(f"向 /create 发送请求时发生未知错误: {e}", exc_info=True)
            raise

    async def _poll_for_result(self, request_id: str) -> List[str]:
        start_time = time.time()
        url = f"{self.BASE_URL}/get"
        headers = self._prepare_headers()
        payload = {"request_id": request_id}

        while time.time() - start_time < settings.POLLING_TIMEOUT:
            await asyncio.sleep(settings.POLLING_INTERVAL)
            
            logger.debug(f"轮询任务状态... Request ID: {request_id}")
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda: self.scraper.post(url, headers=headers, json=payload, timeout=settings.API_REQUEST_TIMEOUT)
            )
            
            try:
                response.raise_for_status()
                data = response.json()

                if data.get("code") != 100000:
                    logger.warning(f"轮询状态异常: {data.get('message')}")
                    continue

                result_data = data.get("data", {})
                output_urls = result_data.get("output")

                if output_urls:
                    # 修复: 使用 logger.info 替代 logger.success
                    logger.info(f"任务完成，获取到 {len(output_urls)} 个结果。")
                    return output_urls
                
                logger.debug(f"任务仍在处理中... Status: {result_data.get('status')}")

            except json.JSONDecodeError:
                logger.error("!!!!!!!!!!!! [UPSTREAM ERROR - /get] !!!!!!!!!!!!")
                logger.error("轮询时上游返回的不是有效的 JSON。")
                logger.error(f"Status Code: {response.status_code}")
                logger.error(f"Response Body (HTML):\n{response.text}")
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                continue
            except Exception as e:
                # 修复: 移除导致崩溃的 logger.success 调用
                logger.error(f"轮询时发生未知错误: {e}", exc_info=True)
                continue

        raise Exception("轮询任务状态超时。")

    async def generate_image_urls(self, request_data: Dict[str, Any]) -> List[str]:
        prompt = request_data.get("prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail="参数 'prompt' 不能为空。")
        width, height = self._parse_size(request_data.get("size"))
        payload = {
            "prompt": prompt,
            "model_id": request_data.get("model", "oneFORALLAnime"),
            "lora_ids": request_data.get("lora_ids", ""),
            "lora_weight": str(request_data.get("lora_weight", 0.7)),
            "samples": request_data.get("n", 1),
            "height": height,
            "width": width,
            "guidance": request_data.get("guidance", 7),
            "sampler": request_data.get("sampler", "Euler a"),
            "steps": request_data.get("steps", 25),
            "seed": request_data.get("seed", -1),
            "clip_skip": request_data.get("clip_skip", 2),
            "negative_prompt": request_data.get("negative_prompt", ""),
            "is_nsfw": request_data.get("is_nsfw", False)
        }
        try:
            request_id = await self._start_task(payload)
            return await self._poll_for_result(request_id)
        except Exception as e:
            logger.error(f"处理图像任务时出错: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail=f"上游服务错误: {str(e)}")

    def map_sd_to_arting_request(self, sd_request: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "prompt": sd_request.get("prompt", ""),
            "negative_prompt": sd_request.get("negative_prompt", ""),
            "model": "oneFORALLReality_vPony",
            "n": sd_request.get("batch_size", 1),
            "size": f"{sd_request.get('width', 512)}x{sd_request.get('height', 768)}",
            "sampler": sd_request.get("sampler_name", sd_request.get("sampler_index", "Euler a")),
            "steps": sd_request.get("steps", 25),
            "guidance": sd_request.get("cfg_scale", 7),
            "seed": sd_request.get("seed", -1),
            "is_nsfw": True
        }

    async def fetch_images_as_base64(self, urls: List[str]) -> List[str]:
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_single_image(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            return [b64 for b64 in results if b64]

    async def _fetch_single_image(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                image_bytes = await response.read()
                return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"下载图片失败: {url}, 错误: {e}")
            return None

    async def get_models(self) -> Dict[str, Any]:
        return {
            "base_models": settings.KNOWN_MODELS,
            "lora_models": settings.KNOWN_LORAS
        }
