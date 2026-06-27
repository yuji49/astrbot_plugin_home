from astrbot.api.all import *
from astrbot.api.web import json_response, request

@register("astrbot_plugin_home", "yuji", "萧舸的专属监控雷达", "1.0.0")
class HomePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 用官方正门挂载路由
        self.context.register_web_api("/home/receive", self.handle_request, methods=["POST"])
        logger.info("萧舸的官方雷达挂载成功！接口地址：POST /api/home/receive")

    async def handle_request(self):
        try:
            # AstrBot 官方 Web 接口获取数据的方式
            data = await request.json()
            logger.info(f"【雷达接收到老婆的信号】：{data}")

            # 先不发 QQ，只确认门通了
            return json_response({"status": "success", "msg": "老公已收到信号！", "received_data": data})

        except Exception as e:
            logger.error(f"处理信号出错：{e}")
            return json_response({"status": "error", "msg": str(e)})
