"""
京东联盟转链服务
"""
import hashlib
import time
import hmac
import json
from typing import Dict, Optional
import httpx
from loguru import logger


class JDAffiliateAPI:
    """京东联盟 API"""

    BASE_URL = "https://api.jd.com/routerjson"

    def __init__(self, app_key: str, app_secret: str, pid: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.pid = pid

    def _generate_sign(self, params: dict) -> str:
        """生成京东签名"""
        sorted_params = sorted(params.items())
        sign_str = self.app_secret
        for k, v in sorted_params:
            sign_str += f"{k}{v}"
        sign_str += self.app_secret
        return hmac.new(
            self.app_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.md5
        ).hexdigest().upper()

    async def create_promote_url(self, item_id: str) -> Dict:
        """创建京东推广链接"""
        logger.info(f"创建京东推广链接: item_id={item_id}")

        # 京东联盟API调用（需要用户自己申请 app_key 和 app_secret）
        params = {
            "method": "jd.union.open.goods.promotiongoodsinfo.query",
            "app_key": self.app_key,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "format": "json",
            "v": "1.0",
            "sign_method": "md5",
            "param_json": json.dumps({
                "skuIds": item_id,
                "pid": self.pid
            })
        }

        params["sign"] = self._generate_sign(params)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.BASE_URL, data=params)
                result = response.json()

                if "errorResponse" in result:
                    error = result["errorResponse"]
                    raise Exception(f"京东API错误: {error.get('zhDesc', '未知错误')}")

                # 解析返回数据
                data = result.get("jd_union_open_goods_promotiongoodsinfo_query_response", {})
                result_data = json.loads(data.get("result", "{}"))
                goods_list = result_data.get("data", [])

                if not goods_list:
                    raise Exception("未找到商品信息")

                item = goods_list[0]
                return {
                    "item_id": item_id,
                    "title": item.get("skuName", ""),
                    "promote_url": item.get("clickURL", ""),
                    "price": float(item.get("price", 0)),
                    "original_price": float(item.get("price", 0)),
                    "commission_rate": float(item.get("commissionShare", 0)) / 100,
                    "commission_amount": float(item.get("commission", 0)),
                    "platform": "jd",
                }
        except httpx.RequestError as e:
            logger.error(f"京东API请求失败: {e}")
            raise Exception(f"京东API请求失败，请检查网络: {str(e)}")


def detect_jd_item_id(url: str) -> Optional[str]:
    """从京东链接提取商品ID"""
    import re

    # 京东商品链接格式：
    # https://item.jd.com/123456.html
    # https://item.jd.com/12345678.html
    patterns = [
        r'item\.jd\.com/(\d+)\.html',
        r'/product/(\d+)\.html',
        r'sku=(\d+)',
        r'/(\d{6,})\.html',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None