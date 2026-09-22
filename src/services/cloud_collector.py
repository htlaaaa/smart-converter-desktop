"""
云采集服务
从好单库等平台采集商品信息
"""
import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
import httpx
from loguru import logger


class HaoDanKuAPI:
    """好单库 API"""

    BASE_URL = "https://v2.api.haodanku.com"

    def __init__(self, apikey: str):
        self.apikey = apikey

    async def get_top_items(self, min_id: int = 1, back: int = 200,
                            cat: Optional[str] = None,
                            min_price: Optional[float] = None,
                            max_price: Optional[float] = None,
                            sort: int = 0) -> List[Dict]:
        """
        今日精选商品

        Args:
            min_id: 分页ID
            back: 每页数量（最大200）
            cat: 类目ID（可选）
            min_price: 最小价格
            max_price: 最大价格
            sort: 排序方式 0=综合, 1=销量, 2=价格升, 3=价格降, 4=佣金比例

        Returns:
            商品列表
        """
        params = {
            "apikey": self.apikey,
            "min_id": min_id,
            "back": back,
            "sort": sort,
            "type": 1,  # 1=PC, 2=APP
        }

        if cat:
            params["cat"] = cat
        if min_price:
            params["min_price"] = min_price
        if max_price:
            params["max_price"] = max_price

        return await self._call_api("/top_items", params)

    async def get_itemlist_channel(self, channel_type: str = "肉丝",
                                   min_id: int = 1, back: int = 200,
                                   sort: int = 0) -> List[Dict]:
        """
        好券清单（按类目）

        Args:
            channel_type: 频道（肉丝/优质/品牌/小等）
            min_id: 分页ID
            back: 每页数量
            sort: 排序方式
        """
        params = {
            "apikey": self.apikey,
            "channel_type": channel_type,
            "min_id": min_id,
            "back": back,
            "sort": sort,
        }

        return await self._call_api("/itemlist_channel", params)

    async def super_search(self, keyword: str, min_id: int = 1,
                           back: int = 200, sort: int = 0) -> List[Dict]:
        """
        超级搜索

        Args:
            keyword: 搜索关键词
            min_id: 分页ID
            back: 每页数量
            sort: 排序方式
        """
        params = {
            "apikey": self.apikey,
            "keyword": keyword,
            "min_id": min_id,
            "back": back,
            "sort": sort,
        }

        return await self._call_api("/supersearch", params)

    async def get_keyword_items(self, keyword: str, back: int = 100) -> List[Dict]:
        """
        关键词商品查询
        """
        params = {
            "apikey": self.apikey,
            "keyword": keyword,
            "back": back,
        }

        return await self._call_api("/get_keyword_items", params)

    async def _call_api(self, endpoint: str, params: dict) -> List[Dict]:
        """调用API"""
        url = f"{self.BASE_URL}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()

                # 好单库返回格式：{"code": 200, "msg": "success", "data": {...}}
                if isinstance(result, dict) and result.get("code") == 200:
                    data = result.get("data", {})
                    if isinstance(data, dict):
                        items = data.get("list", [])
                    elif isinstance(data, list):
                        items = data
                    else:
                        items = []

                    logger.info(f"采集到 {len(items)} 个商品")
                    return [self._parse_item(item) for item in items]
                else:
                    msg = result.get("msg", "未知错误") if isinstance(result, dict) else "返回格式错误"
                    logger.error(f"好单库API错误: {msg}")
                    raise Exception(f"好单库API错误: {msg}")

        except httpx.RequestError as e:
            logger.error(f"好单库API请求失败: {e}")
            raise Exception(f"网络请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"好单库API异常: {e}")
            raise

    def _parse_item(self, item: dict) -> Dict:
        """解析商品数据"""
        return {
            "item_id": str(item.get("itemid", "")),
            "title": item.get("itemtitle", "").replace("<font class='keyword'>", "").replace("</font>", ""),
            "original_price": float(item.get("itemprice", 0)),
            "discount_price": float(item.get("itemendprice", 0)),
            "coupon_amount": float(item.get("couponmoney", 0)),
            "commission_rate": float(item.get("tkrates", 0)),
            "commission_amount": float(item.get("tkmoney", 0)),
            "sales_count": int(item.get("itemsale", 0)),
            "shop_name": item.get("shopname", ""),
            "shop_type": item.get("shoptype", ""),  # B=天猫, C=淘宝
            "item_pic": item.get("itempic", ""),
            "item_url": item.get("itemurl", ""),
            "coupon_url": item.get("couponurl", ""),
            "coupon_start": item.get("couponstarttime", ""),
            "coupon_end": item.get("couponendtime", ""),
            "platform": "taobao",
            "source": "haodanku",
        }


class CloudResource:
    """云采集资源"""

    def __init__(self, resource_id: str = None, name: str = "", resource_type: str = "",
                 params: dict = None, enabled: bool = True, source: str = "haodanku"):
        self.resource_id = resource_id or f"res_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.name = name
        self.resource_type = resource_type  # top_items, itemlist_channel, supersearch
        self.params = params or {}
        self.enabled = enabled
        self.source = source

    def to_dict(self) -> dict:
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "resource_type": self.resource_type,
            "params": self.params,
            "enabled": self.enabled,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CloudResource":
        return cls(
            resource_id=data.get("resource_id"),
            name=data.get("name", ""),
            resource_type=data.get("resource_type", ""),
            params=data.get("params", {}),
            enabled=data.get("enabled", True),
            source=data.get("source", "haodanku"),
        )


class CloudCollector:
    """云采集器"""

    def __init__(self, apikey: str):
        self.apikey = apikey
        self.api = HaoDanKuAPI(apikey)

    async def collect_resource(self, resource: CloudResource) -> List[Dict]:
        """
        根据资源配置采集商品

        Args:
            resource: 采集资源

        Returns:
            商品列表
        """
        if not resource.enabled:
            logger.info(f"资源未启用: {resource.name}")
            return []

        try:
            if resource.resource_type == "top_items":
                items = await self.api.get_top_items(
                    back=resource.params.get("back", 100),
                    sort=resource.params.get("sort", 0),
                    min_price=resource.params.get("min_price"),
                    max_price=resource.params.get("max_price"),
                )
            elif resource.resource_type == "itemlist_channel":
                items = await self.api.get_itemlist_channel(
                    channel_type=resource.params.get("channel_type", "肉丝"),
                    back=resource.params.get("back", 100),
                    sort=resource.params.get("sort", 0),
                )
            elif resource.resource_type == "supersearch":
                items = await self.api.super_search(
                    keyword=resource.params.get("keyword", ""),
                    back=resource.params.get("back", 100),
                    sort=resource.params.get("sort", 0),
                )
            else:
                logger.error(f"不支持的资源类型: {resource.resource_type}")
                return []

            logger.info(f"资源 [{resource.name}] 采集到 {len(items)} 个商品")
            return items

        except Exception as e:
            logger.error(f"采集资源 [{resource.name}] 失败: {e}")
            return []