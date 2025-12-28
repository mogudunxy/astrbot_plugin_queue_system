from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
import time
import asyncio
from datetime import datetime, time as dt_time
import astrbot.api.message_components as Comp

# 暖色调的自定义HTML模板
BEAUTIFUL_QUEUE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>排队系统状态</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft YaHei', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            padding: 40px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            max-width: 600px;
            width: 100%;
            border: 3px solid #ff9a62;
        }
        h1 {
            color: #d63031;
            text-align: center;
            margin-bottom: 10px;
            font-size: 36px;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
        }
        .subtitle {
            color: #fd79a8;
            text-align: center;
            margin-bottom: 30px;
            font-size: 18px;
        }
        .info-section {
            background: linear-gradient(135deg, #ffd89b 0%, #19547b 0%, #ff9a62 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 25px;
            text-align: center;
        }
        .info-section h2 {
            font-size: 24px;
            margin-bottom: 10px;
        }
        .info-section p {
            font-size: 16px;
            opacity: 0.95;
        }
        .queue-list {
            margin: 20px 0;
        }
        .queue-item {
            background: linear-gradient(135deg, #fff5e6 0%, #ffe8d6 100%);
            border: 2px solid #ffb380;
            border-radius: 12px;
            padding: 15px 20px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            transition: all 0.3s ease;
        }
        .queue-item:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(255, 154, 98, 0.3);
        }
        .queue-number {
            background: linear-gradient(135deg, #ff6b6b 0%, #ff8e53 100%);
            color: white;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 16px;
            margin-right: 15px;
            flex-shrink: 0;
        }
        .queue-name {
            font-size: 18px;
            color: #2d3436;
            flex: 1;
        }
        .completed-section {
            background: linear-gradient(135deg, #ffd93d 0%, #ffb347 100%);
            color: #2d3436;
            padding: 20px;
            border-radius: 15px;
            margin-top: 25px;
        }
        .completed-section h3 {
            color: #d63031;
            margin-bottom: 15px;
            font-size: 20px;
        }
        .completed-item {
            background: rgba(255, 255, 255, 0.8);
            border-radius: 8px;
            padding: 10px 15px;
            margin-bottom: 8px;
            font-size: 16px;
        }
        .more-info {
            text-align: center;
            color: #636e72;
            font-style: italic;
            margin-top: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 {{ queue_name }}</h1>
        <div class="subtitle">{{ group_name }}</div>
        <div class="info-section">
            <h2>👥 队列状态</h2>
            <p>当前人数：{{ current_size }} / {{ max_size }}</p>
        </div>
        {% if queue_items %}
            <div class="queue-list">
                {% for item in queue_items %}
                    <div class="queue-item">
                        <div class="queue-number">{{ loop.index }}</div>
                        <div class="queue-name">{{ item.user_name }}</div>
                    </div>
                {% endfor %}
            </div>
            {% if has_more %}
                <div class="more-info">... 还有 {{ more_count }} 人等待</div>
            {% endif %}
        {% else %}
            <div class="more-info">暂无排队人员</div>
        {% endif %}
        {% if completed_users %}
            <div class="completed-section">
                <h3>✅ 已完成</h3>
                {% for user in completed_users %}
                    <div class="completed-item">{{ user }}</div>
                {% endfor %}
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

# 暖色调帮助信息模板
HELP_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>排队系统帮助</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft YaHei', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            padding: 40px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            max-width: 700px;
            width: 100%;
            border: 3px solid #ff9a62;
        }
        h1 {
            color: #d63031;
            text-align: center;
            margin-bottom: 10px;
            font-size: 36px;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
        }
        .subtitle {
            color: #fd79a8;
            text-align: center;
            margin-bottom: 30px;
            font-size: 18px;
        }
        .section {
            background: linear-gradient(135deg, #fff5e6 0%, #ffe8d6 100%);
            border: 2px solid #ffb380;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
        }
        .section h2 {
            color: #d63031;
            margin-bottom: 15px;
            font-size: 24px;
            border-bottom: 3px solid #ff9a62;
            padding-bottom: 10px;
        }
        .section p {
            color: #2d3436;
            line-height: 1.8;
            margin-bottom: 10px;
            font-size: 16px;
        }
        .command-item {
            background: rgba(255, 255, 255, 0.8);
            padding: 12px 15px;
            margin: 8px 0;
            border-radius: 8px;
            border-left: 4px solid #ff6b6b;
        }
        .command-item strong {
            color: #d63031;
            font-weight: bold;
        }
        .config-section {
            background: linear-gradient(135deg, #ffd89b 0%, #ff9a62 100%);
            color: #2d3436;
            padding: 20px;
            border-radius: 15px;
            margin-top: 25px;
        }
        .config-section h3 {
            color: #d63031;
            margin-bottom: 15px;
            font-size: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 {{ queue_name }}系统</h1>
        <div class="subtitle">使用帮助指南</div>
        
        <div class="section">
            <h2>👤 用户指令</h2>
            <div class="command-item"><strong>• /排队</strong> - 加入排队队列</div>
            <div class="command-item"><strong>• /退出排队</strong> - 退出当前排队</div>
            <div class="command-item"><strong>• /查看队列</strong> - 查看当前队列状态</div>
            <div class="command-item"><strong>• /我的位置</strong> - 查看自己在队列中的位置</div>
            <div class="command-item"><strong>• /当前叫号</strong> - 查看即将被叫的用户</div>
            <div class="command-item"><strong>• /排队帮助</strong> - 显示此帮助信息</div>
        </div>
        
        <div class="section">
            <h2>🔧 管理员指令</h2>
            <div class="command-item"><strong>• /下一位</strong> - 呼叫队列中的下一位用户{{ permission_text }}</div>
            <div class="command-item"><strong>• /跳过</strong> - 跳过队列中的第一位用户{{ permission_text }}</div>
            <div class="command-item"><strong>• /清空队列</strong> - 清空当前群聊的队列和已完成记录{{ permission_text }}</div>
            <div class="command-item"><strong>• /清空所有队列</strong> - 清空所有群聊的队列和已完成记录 (需要高级管理员权限)</div>
        </div>
        
        <div class="config-section">
            <h3>⚙️ 当前配置</h3>
            {% for config in config_items %}
                <p><strong>{{ config.key }}:</strong> {{ config.value }}</p>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

@register("queue_system", "mogudunxy", "排队系统插件", "1.2.0")
class QueuePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config if config else {}
        self.queues = {}  # 按群聊ID分别存储队列 {group_id: queue}
        self.completed_users = {}  # 按群聊ID存储已完成用户 {group_id: [user_names]}
        
        # 从配置中获取设置，如果没有配置则使用默认值
        self.enable_call_permission = self.config.get("enable_call_permission", False)
        self.call_permission_users = self.config.get("call_permission_users", [])
        self.admin_users = self.config.get("admin_users", [])
        self.max_queue_size = self.config.get("max_queue_size", 50)
        self.queue_name = self.config.get("queue_name", "排队")
        
        # 定时清除相关配置
        self.enable_auto_clear = self.config.get("enable_auto_clear", False)
        self.clear_time = self.config.get("clear_time", "23:59")
        
        # 通知消息配置
        self.call_message = self.config.get("call_message", "到你了，请前往直播间扫码上号")
        self.queue_status_title = self.config.get("queue_status_title", "队列状态")
        self.completed_label = self.config.get("completed_label", "已完成")
        self.waiting_label = self.config.get("waiting_label", "等待中")
        
        # 重复排队配置
        self.allow_requeue = self.config.get("allow_requeue", False)
        
        # 高级管理员配置
        self.admin_users = self.config.get("admin_users", [])
        
        # 启动定时清除任务
        self.clear_task = None
        if self.enable_auto_clear:
            self.start_auto_clear_task()

    async def initialize(self):
        """插件初始化方法"""
        # 从持久化存储中恢复队列数据
        await self.load_queues_from_storage()
        logger.info("排队系统插件已初始化")
    
    async def load_queues_from_storage(self):
        """从持久化存储中加载队列数据"""
        try:
            # 加载队列数据
            queues_data = await self.get_kv_data("queues", {})
            if queues_data:
                self.queues = queues_data
                logger.info(f"从存储中恢复了 {len(self.queues)} 个群聊的队列数据")
            
            # 加载已完成用户数据
            completed_data = await self.get_kv_data("completed_users", {})
            if completed_data:
                self.completed_users = completed_data
                logger.info(f"从存储中恢复了已完成用户记录")
            
        except Exception as e:
            logger.error(f"加载队列数据时出错：{e}")
            # 如果加载失败，初始化为空字典
            self.queues = {}
            self.completed_users = {}
    
    async def save_queues_to_storage(self):
        """将队列数据保存到持久化存储"""
        try:
            # 保存队列数据
            await self.put_kv_data("queues", self.queues)
            # 保存已完成用户数据
            await self.put_kv_data("completed_users", self.completed_users)
            logger.debug("队列数据已保存到持久化存储")
        except Exception as e:
            logger.error(f"保存队列数据时出错：{e}")
    
    async def clear_storage_data(self):
        """清除持久化存储的队列数据"""
        try:
            await self.delete_kv_data("queues")
            await self.delete_kv_data("completed_users")
            logger.info("持久化存储的队列数据已清除")
        except Exception as e:
            logger.error(f"清除存储数据时出错：{e}")
    


    def __del__(self):
        """插件销毁时停止定时任务"""
        if hasattr(self, 'clear_task') and self.clear_task:
            self.stop_auto_clear_task()

    def get_group_id(self, event: AstrMessageEvent):
        """获取群聊ID"""
        try:
            # 尝试获取群聊ID
            if hasattr(event, 'group_id'):
                return event.group_id
            elif hasattr(event, 'get_group_id'):
                return event.get_group_id()
            else:
                # 如果没有群聊ID，使用默认值（私聊场景）
                return "private"
        except:
            return "private"

    def get_queue(self, event: AstrMessageEvent):
        """获取当前群聊的队列"""
        group_id = self.get_group_id(event)
        if group_id not in self.queues:
            self.queues[group_id] = []
        if group_id not in self.completed_users:
            self.completed_users[group_id] = []
        return self.queues[group_id], group_id
    
    def start_auto_clear_task(self):
        """启动定时清除任务"""
        if self.clear_task:
            self.clear_task.cancel()
        
        self.clear_task = asyncio.create_task(self.auto_clear_scheduler())
        logger.info(f"队列自动清除任务已启动，每天 {self.clear_time} 清除队列")
    
    def stop_auto_clear_task(self):
        """停止定时清除任务"""
        if self.clear_task:
            self.clear_task.cancel()
            self.clear_task = None
            logger.info("队列自动清除任务已停止")
    
    async def auto_clear_scheduler(self):
        """定时清除调度器"""
        while True:
            try:
                # 解析清除时间
                hour, minute = map(int, self.clear_time.split(':'))
                clear_time = dt_time(hour=hour, minute=minute)
                
                # 计算下次清除时间
                now = datetime.now()
                next_clear = datetime.combine(now.date(), clear_time)
                
                # 如果今天的时间已过，则设置为明天
                if now.time() > clear_time:
                    next_clear = datetime.combine(now.date().replace(day=now.day + 1), clear_time)
                
                # 计算等待秒数
                wait_seconds = (next_clear - now).total_seconds()
                
                logger.info(f"下次队列清除时间：{next_clear.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 等待到清除时间
                await asyncio.sleep(wait_seconds)
                
                # 执行清除
                await self.clear_all_queues_task()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"定时清除任务出错：{e}")
                # 出错后等待一小时再试
                await asyncio.sleep(3600)
    
    async def clear_all_queues_task(self):
        """定时任务：清空所有队列"""
        try:
            total_queues = len(self.queues)
            self.queues.clear()
            self.completed_users.clear()
            
            # 同时清除持久化存储的数据
            await self.clear_storage_data()
            
            # 记录日志
            logger.info(f"定时清除完成：清空了 {total_queues} 个群聊的队列和已完成记录，并清除了持久化存储")
            
            # 如果需要在群聊中通知，可以在这里添加通知逻辑
            # 但为了避免打扰，这里只记录日志
            
        except Exception as e:
            logger.error(f"定时清除队列时出错：{e}")

    @filter.command("排队")
    async def join_queue(self, event: AstrMessageEvent):
        """加入排队"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        queue, group_id = self.get_queue(event)
        group_name = f"群聊{group_id}" if group_id != "private" else "私聊"
        
        # 检查是否已经在队列中
        for person in queue:
            if person["user_id"] == user_id:
                yield event.plain_result(f"❌ 你已经在队列中了，位置：第{person['position']}位")
                return
        
        # 检查是否已经完成过排队（如果配置不允许重复排队）
        if not self.allow_requeue:
            completed_users_list = self.completed_users.get(group_id, [])
            if user_name in completed_users_list:
                yield event.plain_result(f"❌ 你今天已经排过队并完成了，不能再次排队！")
                return
        
        # 检查队列是否已满
        if len(queue) >= self.max_queue_size:
            yield event.plain_result(f"❌ 队列已满！当前队列人数：{len(queue)}/{self.max_queue_size}")
            return
        
        # 加入队列
        position = len(queue) + 1
        queue.append({
            "user_id": user_id,
            "user_name": user_name,
            "position": position,
            "join_time": int(time.time())
        })
        
        # 保存数据到持久化存储
        await self.save_queues_to_storage()
        
        # 发送排队成功消息
        yield event.plain_result(f"✅ 排队成功！\n📍 你的位置：第{position}位\n👥 当前{group_name}队列人数：{len(queue)}")
        
        # 发送当前队列状态
        if queue:
            # 准备渲染数据
            render_data = {
                "queue_name": self.queue_name,
                "group_name": group_name,
                "current_size": len(queue),
                "max_size": self.max_queue_size,
                "queue_items": queue[:10],  # 只显示前10人
                "has_more": len(queue) > 10,
                "more_count": len(queue) - 10 if len(queue) > 10 else 0,
                "completed_users": self.completed_users.get(group_id, [])
            }
            # 使用自定义暖色调模板
            try:
                image_url = await self.html_render(BEAUTIFUL_QUEUE_TEMPLATE, render_data)
                yield event.image_result(image_url)
            except Exception as e:
                logger.error(f"发送队列状态图片失败：{e}")
                # 回退到文字版本
                queue_info = f"📋 {group_name}{self.queue_name}状态\n" + f"👥 队列人数：{len(queue)}/{self.max_queue_size}\n\n"
                for i, person in enumerate(queue[:10], 1):
                    queue_info += f"{i}. {person['user_name']}\n"
                if len(queue) > 10:
                    queue_info += f"... 还有{len(queue) - 10}人"
                yield event.plain_result(queue_info)

    @filter.command("退出排队")
    async def leave_queue(self, event: AstrMessageEvent):
        """退出排队"""
        user_id = event.get_sender_id()
        queue, group_id = self.get_queue(event)
        
        # 查找用户在队列中的位置
        found_index = -1
        for i, person in enumerate(queue):
            if person["user_id"] == user_id:
                found_index = i
                break
        
        if found_index == -1:
            yield event.plain_result("❌ 你不在队列中")
            return
        
        # 从队列中移除
        removed_person = queue.pop(found_index)
        
        # 重新排序剩余人员的位置
        for i, person in enumerate(queue):
            person["position"] = i + 1
        
        # 保存数据到持久化存储
        await self.save_queues_to_storage()
        
        group_name = f"群聊{group_id}" if group_id != "private" else "私聊"
        yield event.plain_result(f"✅ 已退出排队\n👤 {removed_person['user_name']} (原位置：第{removed_person['position']}位)\n👥 {group_name}剩余队列人数：{len(queue)}")

    @filter.command("查看队列")
    async def view_queue(self, event: AstrMessageEvent):
        """查看当前队列状态"""
        queue, group_id = self.get_queue(event)
        group_name = f"群聊{group_id}" if group_id != "private" else "私聊"
        
        if not queue:
            yield event.plain_result(f"📋 {group_name}队列为空，暂无排队人员")
            return
        
        # 准备渲染数据
        render_data = {
            "queue_name": self.queue_name,
            "group_name": group_name,
            "current_size": len(queue),
            "max_size": self.max_queue_size,
            "queue_items": queue[:10],  # 只显示前10人
            "has_more": len(queue) > 10,
            "more_count": len(queue) - 10 if len(queue) > 10 else 0,
            "completed_users": self.completed_users.get(group_id, [])
        }
        
        # 使用自定义暖色调模板
        try:
            image_url = await self.html_render(BEAUTIFUL_QUEUE_TEMPLATE, render_data)
            yield event.image_result(image_url)
        except Exception as e:
            logger.error(f"发送队列状态图片失败：{e}")
            # 回退到文字版本
            queue_info = f"📋 {group_name}{self.queue_name}状态\n"
            queue_info += f"👥 队列人数：{len(queue)}/{self.max_queue_size}\n\n"
            for i, person in enumerate(queue[:10], 1):
                queue_info += f"{i}. {person['user_name']}\n"
            if len(queue) > 10:
                queue_info += f"... 还有{len(queue) - 10}人"
            yield event.plain_result(queue_info)

    @filter.command("我的位置")
    async def my_position(self, event: AstrMessageEvent):
        """查看自己在队列中的位置"""
        user_id = event.get_sender_id()
        queue, group_id = self.get_queue(event)
        group_name = f"群聊{group_id}" if group_id != "private" else "私聊"
        
        for person in queue:
            if person["user_id"] == user_id:
                yield event.plain_result(f"📍 你在{group_name}队列中的位置：第{person['position']}位\n👥 当前{group_name}队列总人数：{len(queue)}")
                return
        
        yield event.plain_result(f"❌ 你不在{group_name}队列中")

    @filter.command("清空队列")
    async def clear_queue(self, event: AstrMessageEvent):
        """清空当前群聊队列（管理员功能）"""
        queue, group_id = self.get_queue(event)
        group_name = f"群聊{group_id}" if group_id != "private" else "私聊"
        
        # 权限检查
        if self.enable_call_permission:
            user_id = event.get_sender_id()
            if str(user_id) not in self.call_permission_users:
                yield event.plain_result("❌ 你没有使用'清空队列'指令的权限")
                return
        
        queue.clear()
        self.completed_users[group_id] = []
        
        # 保存数据到持久化存储
        await self.save_queues_to_storage()
        
        yield event.plain_result(f"🗑️ {group_name}队列和已完成记录已清空")

    @filter.command("清空所有队列")
    async def clear_all_queues(self, event: AstrMessageEvent):
        """清空所有群聊队列（高级管理员功能）"""
        user_id = event.get_sender_id()
        
        # 高级管理员权限检查（更严格的权限）
        if str(user_id) not in self.admin_users:
            yield event.plain_result("❌ 你没有使用'清空所有队列'指令的权限，需要高级管理员权限")
            return
        
        total_cleared = len(self.queues)
        self.queues.clear()
        self.completed_users.clear()
        
        # 保存数据到持久化存储
        await self.save_queues_to_storage()
        
        yield event.plain_result(f"🗑️ 已清空所有{total_cleared}个群聊的队列和已完成记录")

    @filter.command("下一位")
    async def call_next(self, event: AstrMessageEvent):
        """叫号系统：呼叫下一位"""
        queue, group_id = self.get_queue(event)
        group_name = f"群聊{group_id}" if group_id != "private" else "私聊"
        
        if not queue:
            yield event.plain_result(f"📋 {group_name}队列为空，暂无呼叫对象")
            return
        
        # 权限检查
        if self.enable_call_permission:
            user_id = event.get_sender_id()
            if str(user_id) not in self.call_permission_users:
                yield event.plain_result("❌ 你没有使用'下一位'指令的权限")
                return
        
        # 取出第一位用户
        next_person = queue.pop(0)
        
        # 添加到已完成用户列表
        if group_id not in self.completed_users:
            self.completed_users[group_id] = []
        self.completed_users[group_id].append(next_person['user_name'])
        
        # 保存数据到持久化存储
        await self.save_queues_to_storage()
        
        # 重新排序剩余人员的位置
        for i, person in enumerate(queue):
            person["position"] = i + 1
        
        # 发送叫号消息，包含@功能
        # 使用配置的叫号消息，替换用户名占位符
        formatted_message = self.call_message.format(user_name=next_person['user_name'])
        
        call_chain = [
            Comp.At(qq=next_person['user_id']),  # @被叫用户
            Comp.Plain(f" {formatted_message}")
        ]
        
        try:
            yield event.chain_result(call_chain)
        except:
            # 如果不支持@功能，发送简化版本
            call_message = f"{next_person['user_name']} {formatted_message}"
            yield event.plain_result(call_message)
        
        # 显示完整队列状态
        render_data = {
            "queue_name": self.queue_name,
            "group_name": group_name,
            "current_size": len(queue),
            "max_size": self.max_queue_size,
            "queue_items": queue[:10],
            "has_more": len(queue) > 10,
            "more_count": len(queue) - 10 if len(queue) > 10 else 0,
            "completed_users": self.completed_users.get(group_id, [])
        }
        
        try:
            image_url = await self.html_render(BEAUTIFUL_QUEUE_TEMPLATE, render_data)
            yield event.image_result(image_url)
        except Exception as e:
            logger.error(f"发送叫号状态图片失败：{e}")
            # 回退到文字版本
            queue_info = f"\n📋 {self.queue_status_title}：\n\n"
            if self.completed_users[group_id]:
                queue_info += f"✅ {self.completed_label}：\n"
                for completed_user in self.completed_users[group_id]:
                    queue_info += f"• {completed_user} ({self.completed_label})\n"
                queue_info += "\n"
            if queue:
                queue_info += f"⏳ {self.waiting_label}：\n"
                for i, person in enumerate(queue, 1):
                    queue_info += f"{i}. {person['user_name']}\n"
            else:
                queue_info += f"⏳ {self.waiting_label}：\n暂无排队人员"
            yield event.plain_result(queue_info)

    @filter.command("当前叫号")
    async def current_calling(self, event: AstrMessageEvent):
        """查看当前正在叫号的状态"""
        queue, group_id = self.get_queue(event)
        group_name = f"群聊{group_id}" if group_id != "private" else "私聊"
        
        if not queue:
            yield event.plain_result(f"📋 {group_name}队列为空，暂无排队人员")
            return
        
        # 准备渲染数据
        render_data = {
            "queue_name": "即将叫号",
            "group_name": group_name,
            "current_size": len(queue),
            "max_size": self.max_queue_size,
            "queue_items": queue[:3],  # 显示即将叫的3人
            "has_more": len(queue) > 3,
            "more_count": len(queue) - 3 if len(queue) > 3 else 0,
            "completed_users": self.completed_users.get(group_id, [])
        }
        
        try:
            image_url = await self.html_render(BEAUTIFUL_QUEUE_TEMPLATE, render_data)
            yield event.image_result(image_url)
        except Exception as e:
            logger.error(f"发送当前叫号图片失败：{e}")
            # 回退到文字版本
            preview_message = f"📋 {group_name}即将叫号\n\n"
            next_count = min(3, len(queue))
            for i in range(next_count):
                person = queue[i]
                if i == 0:
                    preview_message += f"🔔 下一位：{person['user_name']}\n"
                else:
                    preview_message += f"{i+1}. {person['user_name']}\n"
            if len(queue) > 3:
                preview_message += f"... 还有{len(queue) - 3}人等待"
            yield event.plain_result(preview_message)

    @filter.command("跳过")
    async def skip_current(self, event: AstrMessageEvent):
        """跳过当前第一位（管理员功能）"""
        queue, group_id = self.get_queue(event)
        group_name = f"群聊{group_id}" if group_id != "private" else "私聊"
        
        if not queue:
            yield event.plain_result(f"📋 {group_name}队列为空，无法跳过")
            return
        
        # 权限检查
        if self.enable_call_permission:
            user_id = event.get_sender_id()
            if str(user_id) not in self.call_permission_users:
                yield event.plain_result("❌ 你没有使用'跳过'指令的权限")
                return
        
        # 跳过第一位
        skipped_person = queue.pop(0)
        
        # 重新排序
        for i, person in enumerate(queue):
            person["position"] = i + 1
        
        # 保存数据到持久化存储
        await self.save_queues_to_storage()
        
        yield event.plain_result(f"⏭️ 已跳过 {skipped_person['user_name']}\n👥 剩余{len(queue)}人等待")

    @filter.command("排队帮助", alias={'help', '帮助'})
    async def queue_help(self, event: AstrMessageEvent):
        """显示排队系统帮助信息"""
        permission_text = " (需要权限)" if self.enable_call_permission else ""
        
        # 准备配置数据
        config_items = [
            {"key": "队列名称", "value": self.queue_name},
            {"key": "最大队列人数", "value": self.max_queue_size},
            {"key": "重复排队", "value": "允许" if self.allow_requeue else "不允许"},
            {"key": "自动清空", "value": "启用" if self.enable_auto_clear else "未启用"}
        ]
        if self.enable_auto_clear:
            config_items.append({"key": "清空时间", "value": self.clear_time})
        if self.enable_call_permission:
            config_items.append({"key": "叫号权限", "value": "已启用"})
        if self.admin_users:
            config_items.append({"key": "高级管理员", "value": f"{len(self.admin_users)}名"})
        
        # 准备渲染数据
        help_data = {
            "queue_name": self.queue_name,
            "permission_text": permission_text,
            "config_items": config_items
        }
        
        try:
            # 使用自定义暖色调帮助模板
            image_url = await self.html_render(HELP_TEMPLATE, help_data)
            yield event.image_result(image_url)
        except Exception as e:
            logger.error(f"发送帮助信息图片失败：{e}")
            # 回退到文字版本
            help_text = f"📋 {self.queue_name}系统使用帮助\n\n"
            help_text += "👤 用户指令：\n"
            help_text += "• /排队 - 加入排队队列\n"
            help_text += "• /退出排队 - 退出当前排队\n"
            help_text += "• /查看队列 - 查看当前队列状态\n"
            help_text += "• /我的位置 - 查看自己在队列中的位置\n"
            help_text += "• /当前叫号 - 查看即将被叫的用户\n"
            help_text += "• /排队帮助 - 显示此帮助信息\n\n"
            help_text += "🔧 管理员指令：\n"
            help_text += f"• /下一位 - 呼叫队列中的下一位用户{permission_text}\n"
            help_text += f"• /跳过 - 跳过队列中的第一位用户{permission_text}\n"
            help_text += f"• /清空队列 - 清空当前群聊的队列和已完成记录{permission_text}\n"
            help_text += "• /清空所有队列 - 清空所有群聊的队列和已完成记录 (需要高级管理员权限)\n\n"
            help_text += f"⚙️ 当前配置：\n"
            help_text += f"• 队列名称：{self.queue_name}\n"
            help_text += f"• 最大队列人数：{self.max_queue_size}\n"
            help_text += f"• 重复排队：{'允许' if self.allow_requeue else '不允许'}\n"
            help_text += f"• 自动清空：{'启用' if self.enable_auto_clear else '未启用'}"
            if self.enable_auto_clear:
                help_text += f" (每天 {self.clear_time})"
            help_text += "\n"
            if self.enable_call_permission:
                help_text += "• 叫号权限：已启用\n"
            if self.admin_users:
                help_text += f"• 高级管理员：{len(self.admin_users)}名\n"
            help_text += "\n💡 提示：\n"
            help_text += "• 每人每天只能排队一次（除非配置允许重复排队）\n"
            help_text += "• 被叫号后会自动加入已完成列表\n"
            help_text += "• 每天定时清空队列和已完成记录\n"
            help_text += "• 退出排队后可以重新排队"
            yield event.plain_result(help_text)

    async def terminate(self):
        """插件销毁方法"""
        logger.info("排队系统插件已停止")

