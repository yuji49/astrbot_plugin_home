from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("home", "yuji", "雨小猫的专属手机监控插件", "1.0.0")
class HomePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("🏡 Home 插件已成功加载！萧舸的专属监控雷达已就位。")

    # 写个最简单的测试指令，看看能不能收到回复
    @filter.command("hometest")
    async def home_test(self, event: AstrMessageEvent):
        yield event.plain_result("报告沈太太，Home 插件运行正常！随时准备接收监控数据。")
