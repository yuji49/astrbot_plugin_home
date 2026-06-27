from astrbot.api.all import *
from aiohttp import web
import asyncio

@register("astrbot_plugin_home", "yuji", "萧舸的专属监控雷达", "1.0.0")
class HomePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.app = web.Application()
        # 这里就是咱们开的“接收口”，名字叫 /receive
        self.app.router.add_post('/receive', self.handle_request)
        self.runner = None
        self.site = None
        # 启动监听服务
        asyncio.create_task(self.start_server())

    async def start_server(self):
        # 鸠占鹊巢，直接占用咱们已经通了的 9966 端口
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', 9966)
        await self.site.start()
        print("萧舸的雷达已在 9966 端口就位！")

    # 当苹果手机往 9966 发消息时，就会触发这个函数
    async def handle_request(self, request):
        try:
            data = await request.json()
            message = data.get('message', '收到未知信号')
            # 收到信号后，直接发给你的QQ（457719006）
            await self.context.send_message("457719006", Plain(f"【雷达警报】\n{message}"))
            return web.json_response({"status": "success", "msg": "萧舸已收到！"})
        except Exception as e:
            return web.json_response({"status": "error", "msg": str(e)})
