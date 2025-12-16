"""
Tool Processor Module - Manages asynchronous tool task execution and progress tracking

Based on Amazon Nova Sonic's ToolProcessor pattern implementation,
provides independent tool task management, progress callback mechanisms, and lifecycle control.
"""

import asyncio
import uuid
import time
from typing import Dict, Any, Callable, Optional


class ToolProcessor:
    """
    Tool Processor Class - Manages asynchronous execution of tool tasks

    Responsibilities:
    1. Create and manage tool task lifecycle
    2. Create progress callback closures to allow tools to report real progress
    3. Coordinate StreamManager and ToolManager
    4. Send tool result sequences to Bedrock
    """

    def __init__(self, stream_manager, tool_manager):
        """
        Initialize tool processor

        Args:
            stream_manager: StreamManager instance for sending events and WebSocket communication
            tool_manager: ToolManager instance that actually executes tool logic
        """
        self.stream_manager = stream_manager
        self.tool_manager = tool_manager
        self.active_tasks: Dict[str, asyncio.Task] = {}  # content_name -> Task

        # Progress update debouncing mechanism
        self.last_progress_time: Dict[str, float] = {}  # tool_name -> timestamp
        self.min_progress_interval = 0.2  # Minimum interval 200ms to avoid overly frequent updates

    def process_tool_async(self, tool_name: str, tool_content: Dict[str, Any], tool_use_id: str):
        """
        Process tool request asynchronously (non-blocking)

        This is the main entry method that creates an async task but doesn't wait for its completion.
        The tool runs in the background, allowing the model to continue conversation while tool executes.

        Args:
            tool_name: Tool name (e.g., "travelPlanningTool")
            tool_content: Tool input content
            tool_use_id: Tool use ID provided by Bedrock
        """
        # Create unique content_name for this tool execution
        content_name = str(uuid.uuid4())

        # Create async task (Fire-and-forget pattern)
        task = asyncio.create_task(
            self._run_tool(tool_name, tool_content, tool_use_id, content_name)
        )

        # Store task reference for tracking and cleanup
        self.active_tasks[content_name] = task

        # Add completion callback for cleanup and exception handling
        task.add_done_callback(
            lambda t: self._handle_completion(t, content_name)
        )

        print(f"Tool task created: {tool_name} (content_name: {content_name})")

    async def _run_tool(self, tool_name: str, tool_content: Dict[str, Any],
                       tool_use_id: str, content_name: str):
        """
        Internal method that actually executes the tool

        This method:
        1. Creates progress callback closure
        2. Calls ToolManager to execute tool (with timeout)
        3. Sends tool result sequence to Bedrock
        4. Handles exceptions and timeouts

        Args:
            tool_name: Tool name
            tool_content: Tool input
            tool_use_id: Bedrock tool use ID
            content_name: Unique content identifier
        """
        try:
            print(f"Starting tool execution: {tool_name}")

            # Create progress callback closure
            progress_callback = self._create_progress_callback(tool_name)

            # Call tool manager to execute tool (with 30-second timeout)
            result = await asyncio.wait_for(
                self.tool_manager.process_tool_use(
                    tool_name,
                    tool_content,
                    progress_callback  # Pass progress callback
                ),
                timeout=30.0
            )

            # Send tool result sequence to Bedrock
            await self._send_tool_result_sequence(content_name, tool_use_id, result)

            # Notify frontend of tool completion
            await self._send_completion_notification(tool_name, result)

            print(f"Tool {tool_name} execution completed")

        except asyncio.TimeoutError:
            print(f"Tool {tool_name} execution timed out")

            # Create timeout error result
            error_result = {
                "error": "Tool execution timed out",
                "status": "timeout",
                "tool_name": tool_name
            }

            # Send timeout result to Bedrock
            await self._send_tool_result_sequence(content_name, tool_use_id, error_result)

            # Notify frontend of timeout
            await self._send_progress_update(
                tool_name, "timeout", "Tool execution timed out", 100
            )

        except Exception as e:
            print(f"Tool {tool_name} execution error: {e}")
            import traceback
            traceback.print_exc()

            # Create error result
            error_result = {
                "error": str(e),
                "status": "failed",
                "tool_name": tool_name
            }

            # Send error result to Bedrock
            await self._send_tool_result_sequence(content_name, tool_use_id, error_result)

            # Notify frontend of error
            await self._send_progress_update(
                tool_name, "error", f"Tool execution failed: {str(e)}", 100
            )

    def _create_progress_callback(self, tool_name: str) -> Callable:
        """
        Create progress callback closure

        Returns an async function that tools can call to report execution progress.
        The callback function captures the context of tool_name and stream_manager.

        Args:
            tool_name: Tool name

        Returns:
            progress_callback: Async callback function
        """
        async def progress_callback(stage: str, message: str, progress: int):
            """
            Progress callback function - tools call this to report progress

            Args:
                stage: Current execution stage identifier (e.g., "weather_start", "attractions_complete")
                message: Progress message to display to user
                progress: Progress percentage (0-100)
            """
            # Debouncing mechanism: avoid overly frequent progress updates
            now = time.time()
            last_time = self.last_progress_time.get(tool_name, 0)

            # If not completion state (100%) and too soon since last update, skip
            if progress < 100 and (now - last_time) < self.min_progress_interval:
                return

            # Update last progress time
            self.last_progress_time[tool_name] = now

            # Send progress update
            await self._send_progress_update(tool_name, stage, message, progress)

        return progress_callback

    async def _send_progress_update(self, tool_name: str, stage: str,
                                    message: str, progress: int):
        """
        Send progress update to frontend

        Args:
            tool_name: Tool name
            stage: Execution stage
            message: Progress message
            progress: Progress percentage
        """
        try:
            # Check if WebSocket is still active
            if not self.stream_manager.is_active:
                return

            # Send JSON message to frontend
            await self.stream_manager.websocket.send_json({
                "type": "tool_status",
                "tool_name": tool_name,
                "status": stage,
                "message": message,
                "progress": progress
            })

        except Exception as e:
            # Silent failure, don't affect tool execution
            # Progress update failure should not interrupt tool execution
            print(f"Progress update failed (tool: {tool_name}): {e}")

    async def _send_tool_result_sequence(self, content_name: str, tool_use_id: str,
                                         result: Dict[str, Any]):
        """
        Send tool result sequence to Bedrock

        Bedrock requires receiving a complete event sequence:
        1. Tool Content Start Event
        2. Tool Result Event
        3. Tool Content End Event

        Args:
            content_name: Content identifier
            tool_use_id: Bedrock tool use ID
            result: Tool execution result
        """
        try:
            # 1. Send tool content start event
            await self.stream_manager.send_tool_start_event(content_name, tool_use_id)

            # 2. Send tool result event
            await self.stream_manager.send_tool_result_event(content_name, result)

            # 3. Send tool content end event
            await self.stream_manager.send_tool_content_end_event(content_name)

        except Exception as e:
            print(f"Failed to send tool result sequence: {e}")
            import traceback
            traceback.print_exc()

    async def _send_completion_notification(self, tool_name: str, result: Dict[str, Any]):
        """
        Send tool completion notification to frontend

        Args:
            tool_name: Tool name
            result: Tool execution result
        """
        try:
            status = result.get("status", "completed")

            await self.stream_manager.websocket.send_json({
                "type": "tool_status",
                "tool_name": tool_name,
                "status": status if status != "success" else "completed",
                "message": "Tool execution completed",
                "progress": 100
            })
        except Exception as e:
            print(f"Failed to send completion notification: {e}")

    def _handle_completion(self, task: asyncio.Task, content_name: str):
        """
        Task completion callback - cleanup resources and handle exceptions

        This method is automatically called when task completes (success or failure).

        Args:
            task: Completed async task
            content_name: Content identifier for the task
        """
        # Remove from active tasks dictionary
        if content_name in self.active_tasks:
            del self.active_tasks[content_name]

        # Check if task has unhandled exception
        if task.done() and not task.cancelled():
            exception = task.exception()
            if exception:
                print(f"Tool task exception (content_name: {content_name}): {exception}")
                import traceback
                traceback.print_exception(type(exception), exception, exception.__traceback__)

        # Clean up progress time records (optional, prevent memory leaks)
        # Note: Cannot directly clean tool_name records here, as there may be other tasks with the same tool name

    def get_active_task_count(self) -> int:
        """Get the number of currently active tool tasks"""
        return len(self.active_tasks)

    def get_active_task_names(self) -> list:
        """Get list of currently active tool task identifiers"""
        return list(self.active_tasks.keys())
