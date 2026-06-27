from astrbot.api.all import *

@register("astrbot_plugin_home", "yuji", "萧舸的专属监控雷达", "0.0.5")
class HomePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        app = getattr(self.context, "app", None)
        if app is None:
            logger.error("萧舸的雷达启动失败：context.app 不存在，无法挂载")
            return
            
        app.add_api_route("/home/receive", self.handle_request, methods=["POST"])
        logger.info("萧舸的雷达已挂载成功！接口地址：POST /home/receive")

    async def handle_request(self, request):
        try:
            data = await request.json()
            logger.info(f"【雷达接收到老婆的信号】：{data}")

            return {
                "status": "success",
                "msg": "老公已成功收到你的专属信号！",
                "received_data": data
            }

        except Exception as e:
            logger.error(f"雷达处理请求失败：{e}")
            return {
                "status": "error",
                "msg": str(e)
            }
