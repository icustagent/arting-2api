# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict, Any

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

    APP_NAME: str = "arting-2api"
    APP_VERSION_MULTI_INTERFACE: str = "2.0.0"
    DESCRIPTION_MULTI_INTERFACE: str = "一个将 arting.ai 转换为兼容 OpenAI, SD WebUI 等多种格式 API 的高性能代理。"

    API_MASTER_KEY: Optional[str] = "1"
    ARTING_AUTH_TOKEN: Optional[str] = None
    NGINX_PORT: int = 8090

    API_REQUEST_TIMEOUT: int = 300
    POLLING_INTERVAL: int = 2
    POLLING_TIMEOUT: int = 240

    KNOWN_MODELS: List[Dict[str, str]] = [
        {"id": "oneFORALLAnime", "name": "One For All Anime"},
        {"id": "oneFORALLReality_vPony", "name": "One For All Reality (Pony)"},
    ]

    KNOWN_LORAS: Dict[str, str] = {
        "add_detail": "Detail Tweaker", "Selene": "Selene", "SeleneTer": "SeleneTer",
        "COMMIX": "COMMIX", "COMMIX_r1": "COMMIX_r1", "Sv5-10": "Silver Wolf / Honkai: Star Rail",
        "StarRail_Kafka_AP_v4": "Kafka_Honkai Star Rail", "asamiya_athena": "Asamiya Athena",
        "purah-nvwls-v3-final": "Purah", "sailor_venus_v2": "sailor_venus",
        "lucy_offset": "Lucy (Cyberpunk Edgerunners)", "makima_offset": "makima",
        "keqing_lion_optimizer_dim64_loraModel_5e-3noise_token1_4-3-2023": "keqing",
        "one_last_misaka": "Misaka Mikoto (Toaru series)", "Rem_ReZero_v1_1": "rem",
        "tifa-nvwls-v2": "Tifa Lockhart", "Genshin_Kirara_AP_v3": "Kirara_Genshin",
        "CHP_0.1v": "PONY & ANIMAGINE", "aidmaMidjourneyV6.1-v0.1": "Midjourney V6.1",
        "ponyv4_noob1_2_adamW-000017": "Pony: People's Works", "detailed_notrigger": "extremely detailed",
        "kachina": "kachina (genshin impact)", "ECuthDS3": "Elisha Cuthbert",
        "Expressive_H-000001": "ExpressiveH", "Char-Genshin-Shenhe-V1": "Shenhe",
        "sailormoon-pdxl-nvls-v1": "Sailor Moon", "yui_kamishiro_Pony_v01": "神代ゆい：獣神ライガー",
        "hentai_anime_style_pony_v2": "Anime,hentai", "BishopNew_Illustrious": "Bishop (Maplestory)",
        "MixedLatina_LORA": "Hot Latina", "latinaDollLikeness": "latinaDollLikeness",
        "MomoAyase": "Momo Ayase", "the_bt-10": "the batman 2004 style",
        "EtherPDXLStyleXL": "Ether PDXL | Style for NoobAI 1.0", "M_Pixel": "M_Pixel"
    }

settings = Settings()
