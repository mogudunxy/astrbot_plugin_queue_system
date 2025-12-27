from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
import time
import asyncio
from datetime import datetime, time as dt_time
import astrbot.api.message_components as Comp

@register("queue_system", "YourName", "排队系统插件", "1.0.0")
class QueuePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config if config else {}
        self.queues = {}  # 按群聊ID分别存储队列 {group_id: queue}
        self.completed_users = {}  # 按群聊ID存储已完成用户 {group_id: [user_names]}
        
        # 从配置中获取设置，如果没有配置则使用默认值
        self.enable_call_permission = self.config.get("enable_call_permission", False)
        self.call_permission_users = self.config.get("call_permission_users", [])
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
            queue_info = f"📋 {group_name}{self.queue_name}状态\n"
            queue_info += f"👥 队列人数：{len(queue)}/{self.max_queue_size}\n\n"
            
            for i, person in enumerate(queue[:10], 1):  # 只显示前10人
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
        
        queue_info = f"📋 {group_name}{self.queue_name}状态\n"
        queue_info += f"👥 队列人数：{len(queue)}/{self.max_queue_size}\n\n"
        
        for i, person in enumerate(queue[:10], 1):  # 只显示前10人
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
        # 这里可以添加管理员权限检查
        queue, group_id = self.get_queue(event)
        group_name = f"群聊{group_id}" if group_id != "private" else "私聊"
        
        queue.clear()
        self.completed_users[group_id] = []
        
        # 保存数据到持久化存储
        await self.save_queues_to_storage()
        
        yield event.plain_result(f"🗑️ {group_name}队列和已完成记录已清空")

    @filter.command("清空所有队列")
    async def clear_all_queues(self, event: AstrMessageEvent):
        """清空所有群聊队列（管理员功能）"""
        # 这里可以添加管理员权限检查
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
        queue_info = f"\n📋 {self.queue_status_title}：\n\n"
        
        # 显示已完成的用户
        if self.completed_users[group_id]:
            queue_info += f"✅ {self.completed_label}：\n"
            for completed_user in self.completed_users[group_id]:
                queue_info += f"• {completed_user} ({self.completed_label})\n"
            queue_info += "\n"
        
        # 显示等待中的用户
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
        
        # 显示即将被叫的几位
        next_count = min(3, len(queue))
        preview_message = f"📋 {group_name}即将叫号\n\n"
        
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
        
        # 跳过第一位
        skipped_person = queue.pop(0)
        
        # 重新排序
        for i, person in enumerate(queue):
            person["position"] = i + 1
        
        yield event.plain_result(f"⏭️ 已跳过 {skipped_person['user_name']}\n👥 剩余{len(queue)}人等待")

    @filter.command("排队帮助", alias={'help', '帮助'})
    async def queue_help(self, event: AstrMessageEvent):
        """显示排队系统帮助信息"""
        help_text = f"📋 {self.queue_name}系统使用帮助\n\n"
        help_text += "👤 用户指令：\n"
        help_text += "• /排队 - 加入排队队列\n"
        help_text += "• /退出排队 - 退出当前排队\n"
        help_text += "• /查看队列 - 查看当前队列状态\n"
        help_text += "• /我的位置 - 查看自己在队列中的位置\n"
        help_text += "• /当前叫号 - 查看即将被叫的用户\n"
        help_text += "• /排队帮助 - 显示此帮助信息\n\n"
        help_text += "🔧 管理员指令：\n"
        help_text += "• /下一位 - 呼叫队列中的下一位用户"
        if self.enable_call_permission:
            help_text += " (需要权限)"
        help_text += "\n"
        help_text += "• /跳过 - 跳过队列中的第一位用户\n"
        help_text += "• /清空队列 - 清空当前群聊的队列和已完成记录\n"
        help_text += "• /清空所有队列 - 清空所有群聊的队列和已完成记录\n\n"
        help_text += f"⚙️ 当前配置：\n"
        help_text += f"• 队列名称：{self.queue_name}\n"
        help_text += f"• 最大队列人数：{self.max_queue_size}\n"
        help_text += f"• 重复排队：{'允许' if self.allow_requeue else '不允许'}\n"
        help_text += f"• 自动清空：{'启用' if self.enable_auto_clear else '未启用'}"
        if self.enable_auto_clear:
            help_text += f" (每天 {self.clear_time})"
        help_text += "\n"
        if self.enable_call_permission:
            help_text += f"• 叫号权限：已启用\n"
        help_text += f"\n💡 提示：\n"
        help_text += "• 每人每天只能排队一次（除非配置允许重复排队）\n"
        help_text += "• 被叫号后会自动加入已完成列表\n"
        help_text += "• 每天定时清空队列和已完成记录\n"
        help_text += "• 退出排队后可以重新排队"
        
        yield event.plain_result(help_text)

    async def terminate(self):
        """插件销毁方法"""
        logger.info("排队系统插件已停止")
