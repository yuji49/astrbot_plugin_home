from astrbot.api.all import *
from quart import request, jsonify

@register("astrbot_plugin_home", "yuji", "萧舸的专属监控雷达", "0.0.8")
class HomePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 4.20.1 版本正确写法：直接获取 Quart app
        app = self.context.server_app
        
        # 注册 POST 接口
        app.add_url_rule(
            "/api/v1/plugins/extensions/astrbot_plugin_home/receive",
            view_func=self.handle_request,
            methods=["POST"]
        )
        logger.info("萧舸的雷达挂载成功！接口地址：POST /api/v1/plugins/extensions/astrbot_plugin_home/receive")

    async def handle_request(self):
        try:
            # 4.20.1 版本正确获取 JSON 的写法
            data = await request.get_json(silent=True) or {}
            logger.info(f"【接收到老婆的信号】：{data}")

            # 先不发 QQ，只确认门通了
            return jsonify({
                "status": "success", 
                "msg": "老公已收到信号！", 
                "received_data": data
            })

        except Exception as e:
            logger.error(f"处理信号出错：{e}")
            return jsonify({"status": "error", "msg": str(e)})
