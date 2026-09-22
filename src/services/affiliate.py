"""
智能转链服务 - 核心逻辑
"""
import hashlib
import time
import hmac
import urllib.parse
from typing import Dict, Optional
import httpx
from loguru import logger


class TaobaoAffiliateAPI:
    """淘宝联盟 API"""

    BASE_URL = "https://eco.taobao.com/router/rest"

    def __init__(self, app_key: str, app_secret: str, pid: str, adzone_id: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.pid = pid
        self.adzone_id = adzone_id

    def _generate_sign(self, params: dict) -> str:
        """生成 API 签名"""
        sorted_params = sorted(params.items())
        sign_str = self.app_secret + "".join([f"{k}{v}" for k, v in sorted_params]) + self.app_secret
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    async def _call_api(self, method: str, params: dict) -> dict:
        """调用淘宝联盟 API"""
        api_params = {
            "method": method,
            "app_key": self.app_key,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "format": "json",
            "v": "2.0",
            "sign_method": "md5",
            "pid": self.pid,
        }

        api_params.update(params)
        api_params["sign"] = self._generate_sign(api_params)

        async with httpx.AsyncClient() as client:
            response = await client.post(self.BASE_URL, data=api_params)
            result = response.json()

            if "error_response" in result:
                error = result["error_response"]
                logger.error(f"淘宝 API 错误: {error}")
                raise Exception(f"API Error {error.get('code')}: {error.get('msg')}")

            return result

    async def create_promote_url(self, item_id: str) -> Dict:
        """创建推广链接"""
        logger.info(f"创建推广链接: item_id={item_id}")

        params = {
            "item_id": item_id,
            "adzone_id": self.adzone_id,
        }

        result = await self._call_api("taobao.tbk.dg.material.optional", params)

        data = result.get("tbk_dg_material_optional_response", {})
        result_list = data.get("result_list", {}).get("map_data", [])

        if not result_list:
            raise Exception("未找到商品信息")

        item = result_list[0]
        promote_url = item.get("click_url", "")

        return {
            "item_id": item_id,
            "title": item.get("title", ""),
            "promote_url": promote_url,
            "tao_password": self._generate_password(promote_url),
            "price": float(item.get("zk_final_price", 0)),
            "original_price": float(item.get("reserve_price", 0)),
            "coupon_amount": float(item.get("coupon_amount", 0)),
            "commission_rate": float(item.get("commission_rate", 0)) / 100,
            "commission_amount": float(item.get("commission_amount", 0)),
            "sales_count": int(item.get("volume", 0)),
            "images": item.get("pict_url", ""),
        }

    def _generate_password(self, url: str) -> str:
        """生成淘口令"""
        return f"￥{hashlib.md5(url.encode()).hexdigest()[:8]}￥"

    def _generate_qr_code(self, url: str) -> str:
        """生成二维码链接"""
        return f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(url)}"


def detect_platform(url: str) -> str:
    """检测链接平台"""
    url_lower = url.lower()
    if any(domain in url_lower for domain in ["taobao.com", "tmall.com"]):
        return "taobao"
    elif any(domain in url_lower for domain in ["jd.com"]):
        return "jd"
    elif any(domain in url_lower for domain in ["pinduoduo.com"]):
        return "pdd"
    return "unknown"


def extract_item_id(url: str, platform: str) -> Optional[str]:
    """从 URL 提取商品 ID"""
    import re

    if platform == "taobao":
        patterns = [r"id=(\d+)", r"item\.taobao\.com/item\.htm\?id=(\d+)"]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

    elif platform == "jd":
        patterns = [r"/(\d+)\.html", r"item\.jd\.com/(\d+)\.html"]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

    return None
