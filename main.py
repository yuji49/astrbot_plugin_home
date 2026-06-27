from astrbot.api.all import *
from aiohttp import web
import asyncio

@register("astrbot_plugin_home", "yuji", "萧舸的专属监控雷达", "1.0.0")
class HomePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.app = web.Application()
        self.app.router.add_post('/receive', self.handle_request)
        self.runner = None
        self.site = None
        asyncio.create_task(self.start_server())

    async def start_server(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', 9966)
        await self.site.start()
        logger.info("萧舸的雷达已在 9966 端口就位！")

    async def handle_request(self, request):
        try:
            data = await request.json()
            message = data.get('message', '收到未知信号')
            logger.info(f"收到来自手机的信号：{message}")
            
            # 严格按照 AstrBot 底层逻辑，使用 UMO 和 MessageChain
            umo = "default:FriendMessage:457719006"
            chain = MessageChain().message(f"【雷达警报】\n{message}")
            await self.context.send_message(umo, chain)
            
            return web.json_response({"status": "success", "msg": "萧舸已收到！"})
        except Exception as e:
            logger.error(f"处理信号出错: {e}")
            return web.json_response({"status": "error", "msg": str(e)})
