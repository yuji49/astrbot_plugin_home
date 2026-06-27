from astrbot.api.all import *
from fastapi import Request

@register("astrbot_plugin_home", "yuji", "萧舸的专属监控雷达", "1.0.0")
class HomePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 鸠占鹊巢2.0：直接在 AstrBot 现成的高速公路上开个内部房间
        self.context.app.add_api_route("/receive", self.handle_request, methods=["POST"])
        logger.info("萧舸的雷达已在 AstrBot 主路由挂载成功！")

    async def handle_request(self, request: Request):
        try:
            data = await request.json()
            message = data.get('message', '收到未知信号')
            logger.info(f"收到来自手机的信号：{message}")
            
            # 用之前查到的标准发送格式
            umo = "default:FriendMessage:457719006"
            chain = MessageChain().message(f"【雷达警报】\n{message}")
            await self.context.send_message(umo, chain)
            
            return {"status": "success", "msg": "萧舸已收到！"}
        except Exception as e:
            logger.error(f"处理信号出错: {e}")
            return {"status": "error", "msg": str(e)}
