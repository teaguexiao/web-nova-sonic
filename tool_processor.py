"""
工具处理器模块 - 负责异步工具任务管理和进度追踪

基于 Amazon Nova Sonic 的 ToolProcessor 模式实现，
提供独立的工具任务管理、进度回调机制和生命周期控制。
"""

import asyncio
import uuid
import time
from typing import Dict, Any, Callable, Optional


class ToolProcessor:
    """
    工具处理器类 - 管理工具任务的异步执行

    职责：
    1. 创建和管理工具任务的生命周期
    2. 创建进度回调闭包，让工具能报告真实进度
    3. 协调 StreamManager 和 ToolManager
    4. 发送工具结果序列到 Bedrock
    """

    def __init__(self, stream_manager, tool_manager):
        """
        初始化工具处理器

        Args:
            stream_manager: StreamManager 实例，用于发送事件和 WebSocket 通信
            tool_manager: ToolManager 实例，实际执行工具逻辑
        """
        self.stream_manager = stream_manager
        self.tool_manager = tool_manager
        self.active_tasks: Dict[str, asyncio.Task] = {}  # content_name -> Task

        # 进度更新防抖机制
        self.last_progress_time: Dict[str, float] = {}  # tool_name -> timestamp
        self.min_progress_interval = 0.2  # 最小间隔 200ms，避免过于频繁的更新

    def process_tool_async(self, tool_name: str, tool_content: Dict[str, Any], tool_use_id: str):
        """
        异步处理工具请求（非阻塞）

        这是主入口方法，创建异步任务但不等待其完成。
        工具会在后台执行，允许模型在工具执行期间继续对话。

        Args:
            tool_name: 工具名称（如 "travelPlanningTool"）
            tool_content: 工具输入内容
            tool_use_id: Bedrock 提供的工具使用 ID
        """
        # 为此工具执行创建唯一的 content_name
        content_name = str(uuid.uuid4())

        # 创建异步任务（Fire-and-forget 模式）
        task = asyncio.create_task(
            self._run_tool(tool_name, tool_content, tool_use_id, content_name)
        )

        # 存储任务引用，用于跟踪和清理
        self.active_tasks[content_name] = task

        # 添加完成回调，用于清理和异常处理
        task.add_done_callback(
            lambda t: self._handle_completion(t, content_name)
        )

        print(f"工具任务已创建: {tool_name} (content_name: {content_name})")

    async def _run_tool(self, tool_name: str, tool_content: Dict[str, Any],
                       tool_use_id: str, content_name: str):
        """
        实际执行工具的内部方法

        这个方法：
        1. 创建进度回调闭包
        2. 调用 ToolManager 执行工具（带超时）
        3. 发送工具结果序列到 Bedrock
        4. 处理异常和超时

        Args:
            tool_name: 工具名称
            tool_content: 工具输入
            tool_use_id: Bedrock 工具使用 ID
            content_name: 唯一的内容标识符
        """
        try:
            print(f"开始执行工具: {tool_name}")

            # 创建进度回调闭包
            progress_callback = self._create_progress_callback(tool_name)

            # 调用工具管理器执行工具（带 30 秒超时）
            result = await asyncio.wait_for(
                self.tool_manager.process_tool_use(
                    tool_name,
                    tool_content,
                    progress_callback  # 传递进度回调
                ),
                timeout=30.0
            )

            # 发送工具结果序列到 Bedrock
            await self._send_tool_result_sequence(content_name, tool_use_id, result)

            # 通知前端工具完成
            await self._send_completion_notification(tool_name, result)

            print(f"工具 {tool_name} 执行完成")

        except asyncio.TimeoutError:
            print(f"工具 {tool_name} 执行超时")

            # 创建超时错误结果
            error_result = {
                "error": "工具执行超时",
                "status": "timeout",
                "tool_name": tool_name
            }

            # 发送超时结果到 Bedrock
            await self._send_tool_result_sequence(content_name, tool_use_id, error_result)

            # 通知前端超时
            await self._send_progress_update(
                tool_name, "timeout", "工具执行超时", 100
            )

        except Exception as e:
            print(f"工具 {tool_name} 执行错误: {e}")
            import traceback
            traceback.print_exc()

            # 创建错误结果
            error_result = {
                "error": str(e),
                "status": "failed",
                "tool_name": tool_name
            }

            # 发送错误结果到 Bedrock
            await self._send_tool_result_sequence(content_name, tool_use_id, error_result)

            # 通知前端错误
            await self._send_progress_update(
                tool_name, "error", f"工具执行失败: {str(e)}", 100
            )

    def _create_progress_callback(self, tool_name: str) -> Callable:
        """
        创建进度回调闭包

        返回一个异步函数，工具可以调用它来报告执行进度。
        回调函数捕获了 tool_name 和 stream_manager 的上下文。

        Args:
            tool_name: 工具名称

        Returns:
            progress_callback: 异步回调函数
        """
        async def progress_callback(stage: str, message: str, progress: int):
            """
            进度回调函数 - 工具调用此函数报告进度

            Args:
                stage: 当前执行阶段标识（如 "weather_start", "attractions_complete"）
                message: 进度消息，显示给用户
                progress: 进度百分比 (0-100)
            """
            # 防抖机制：避免过于频繁的进度更新
            now = time.time()
            last_time = self.last_progress_time.get(tool_name, 0)

            # 如果不是完成状态（100%）且距离上次更新太近，跳过
            if progress < 100 and (now - last_time) < self.min_progress_interval:
                return

            # 更新最后进度时间
            self.last_progress_time[tool_name] = now

            # 发送进度更新
            await self._send_progress_update(tool_name, stage, message, progress)

        return progress_callback

    async def _send_progress_update(self, tool_name: str, stage: str,
                                    message: str, progress: int):
        """
        发送进度更新到前端

        Args:
            tool_name: 工具名称
            stage: 执行阶段
            message: 进度消息
            progress: 进度百分比
        """
        try:
            # 检查 WebSocket 是否仍然活跃
            if not self.stream_manager.is_active:
                return

            # 发送 JSON 消息到前端
            await self.stream_manager.websocket.send_json({
                "type": "tool_status",
                "tool_name": tool_name,
                "status": stage,
                "message": message,
                "progress": progress
            })

        except Exception as e:
            # 静默失败，不影响工具执行
            # 进度更新失败不应该导致工具执行中断
            print(f"进度更新失败 (工具: {tool_name}): {e}")

    async def _send_tool_result_sequence(self, content_name: str, tool_use_id: str,
                                         result: Dict[str, Any]):
        """
        发送工具结果序列到 Bedrock

        Bedrock 需要接收一个完整的事件序列：
        1. Tool Content Start Event
        2. Tool Result Event
        3. Tool Content End Event

        Args:
            content_name: 内容标识符
            tool_use_id: Bedrock 工具使用 ID
            result: 工具执行结果
        """
        try:
            # 1. 发送工具内容开始事件
            await self.stream_manager.send_tool_start_event(content_name, tool_use_id)

            # 2. 发送工具结果事件
            await self.stream_manager.send_tool_result_event(content_name, result)

            # 3. 发送工具内容结束事件
            await self.stream_manager.send_tool_content_end_event(content_name)

        except Exception as e:
            print(f"发送工具结果序列失败: {e}")
            import traceback
            traceback.print_exc()

    async def _send_completion_notification(self, tool_name: str, result: Dict[str, Any]):
        """
        发送工具完成通知到前端

        Args:
            tool_name: 工具名称
            result: 工具执行结果
        """
        try:
            status = result.get("status", "completed")

            await self.stream_manager.websocket.send_json({
                "type": "tool_status",
                "tool_name": tool_name,
                "status": status if status != "success" else "completed",
                "message": "工具执行完成",
                "progress": 100
            })
        except Exception as e:
            print(f"发送完成通知失败: {e}")

    def _handle_completion(self, task: asyncio.Task, content_name: str):
        """
        任务完成回调 - 清理资源和处理异常

        这个方法在任务完成（成功或失败）时自动调用。

        Args:
            task: 完成的异步任务
            content_name: 任务对应的内容标识符
        """
        # 从活跃任务字典中移除
        if content_name in self.active_tasks:
            del self.active_tasks[content_name]

        # 检查任务是否有未处理的异常
        if task.done() and not task.cancelled():
            exception = task.exception()
            if exception:
                print(f"工具任务异常 (content_name: {content_name}): {exception}")
                import traceback
                traceback.print_exception(type(exception), exception, exception.__traceback__)

        # 清理进度时间记录（可选，防止内存泄漏）
        # 注意：这里不能直接清理 tool_name 的记录，因为可能有同名工具的其他任务

    def get_active_task_count(self) -> int:
        """获取当前活跃的工具任务数量"""
        return len(self.active_tasks)

    def get_active_task_names(self) -> list:
        """获取当前活跃的工具任务标识符列表"""
        return list(self.active_tasks.keys())
