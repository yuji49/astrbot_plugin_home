# Home v0.1 目标
## 功能
接收 iOS 快捷指令发送的“打开 App”事件。
## 流程
iOS 快捷指令
→ HTTP POST
→ Home 插件
→ AstrBot 日志显示事件
## 第一版只做
- 接收 app_opened 事件
- 记录 app 名称
- 记录时间
- 不主动回复 QQ
- 不调用 Gemini
## 示例请求
POST /home/app_opened
```json
{
  "event": "app_opened",
  "app": "小红书",
  "source": "ios_shortcuts"
}
