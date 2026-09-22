"""
AI 服务 - Claude 集成
"""
import json
import anthropic
from typing import Dict
from loguru import logger


class AIService:
    """AI 服务"""

    def __init__(self, api_key: str, model: str = "claude-fable-5"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def analyze_product(self, product_info: Dict) -> Dict:
        """分析商品"""
        try:
            prompt = f"""分析以下商品信息，以 JSON 格式返回：

商品：{product_info.get('title', '')}
价格：{product_info.get('price', 0)} 元
原价：{product_info.get('original_price', 0)} 元
销量：{product_info.get('sales_count', 0)}
佣金：{product_info.get('commission_rate', 0) * 100:.1f}%

返回格式：
{{
    "category": "品类",
    "target_audience": ["人群1", "人群2"],
    "key_selling_points": ["卖点1", "卖点2"],
    "promotion_difficulty": "高/中/低",
    "suggestions": "推广建议",
    "risk_level": "高/中/低"
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            content = message.content[0].text
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content

            return json.loads(json_str)

        except Exception as e:
            logger.error(f"AI 分析失败: {e}")
            return self._default_analysis()

    async def generate_copywriting(self, product_info: Dict, ai_analysis: Dict, style: str = "通用") -> str:
        """生成推广文案"""
        try:
            style_guides = {
                "小红书": "使用大量 emoji，种草语气，场景化描述",
                "朋友圈": "简短有力，引发好奇",
                "微博": "详细评测，互动引导",
                "抖音脚本": "开场抓眼球，痛点+方案+行动号召",
                "通用": "平衡描述，突出卖点",
            }

            prompt = f"""为商品生成推广文案：

商品：{product_info.get('title', '')}
价格：{product_info.get('price', 0)} 元
卖点：{', '.join(ai_analysis.get('key_selling_points', []))}
人群：{', '.join(ai_analysis.get('target_audience', []))}

风格：{style_guides.get(style, style_guides['通用'])}

直接输出文案，不要解释："""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text.strip()

        except Exception as e:
            logger.error(f"文案生成失败: {e}")
            return self._default_copywriting(product_info)

    def _default_analysis(self) -> Dict:
        return {
            "category": "未分类",
            "target_audience": ["通用人群"],
            "key_selling_points": ["性价比高"],
            "promotion_difficulty": "中",
            "suggestions": "建议结合商品特点进行推广",
            "risk_level": "低",
        }

    def _default_copywriting(self, product_info: Dict) -> str:
        title = product_info.get('title', '好物推荐')
        price = product_info.get('price', 0)
        return f"🔥 超值推荐！{title}\n💰 价格：{price}元\n\n超划算，赶紧入手吧！"
