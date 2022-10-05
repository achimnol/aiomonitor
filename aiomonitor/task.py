import asyncio
import dataclasses
import sys
import time
import traceback
from asyncio.coroutines import _format_coroutine  # type: ignore
from typing import Any, List, Optional

from .utils import _extract_stack_from_frame


@dataclasses.dataclass
class CancelledTaskInfo:
    id: int
    name: str
    coro: str
    started_at: float
    cancelled_at: float
    stack: List[traceback.FrameSummary]


class TracedTask(asyncio.Task):
    def __init__(
        self, *args, cancelled_tasks=None, cancelled_task_chains=None, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._cancelled_tasks = cancelled_tasks
        self._cancelled_task_chains = cancelled_task_chains
        self._started_at = time.perf_counter()

    def get_trace_id(self) -> int:
        return hash(
            (
                id(self),
                self.get_name(),
            )
        )

    # TODO: catch self-raised cancelled error
    def _trace_self_cancellation(self, task: asyncio.Task[Any]) -> None:
        if self.cancelled():
            print("self-cancellation", self.get_trace_id(), sys.exc_info())

    def cancel(self, msg: Optional[str] = None) -> bool:
        try:
            canceller_task = asyncio.current_task()
        except RuntimeError:
            canceller_task = None
        self_id = self.get_trace_id()
        if canceller_task is not None and self._cancelled_task_chains is not None:
            assert isinstance(canceller_task, TracedTask)
            self._cancelled_task_chains[
                self_id,
            ] = canceller_task.get_trace_id()
        if self._cancelled_tasks is not None:
            print("recording external-cancellation", self.get_trace_id())
            # TODO: trim the old historical entries to prevent memory leak
            self._cancelled_tasks[self_id] = CancelledTaskInfo(
                self_id,
                name=self.get_name(),
                coro=_format_coroutine(self.get_coro()).partition(" ")[0],
                started_at=self._started_at,
                cancelled_at=time.perf_counter(),
                stack=_extract_stack_from_frame(sys._getframe())[:-1],
            )
        return super().cancel(msg=msg)
