import asyncio
import dataclasses
import sys
import time
import traceback
from collections.abc import Coroutine
from asyncio.coroutines import _format_coroutine  # type: ignore
from typing import Any, List, Optional

import janus

from .utils import _extract_stack_from_frame


@dataclasses.dataclass
class TerminatedTaskInfo:
    id: int
    name: str
    coro: str
    started_at: float
    terminated_at: float
    cancelled: bool
    termination_stack: Optional[List[traceback.FrameSummary]]
    canceller_stack: Optional[List[traceback.FrameSummary]] = None
    exc_repr: Optional[str] = None


@dataclasses.dataclass
class CancellationChain:
    target_id: int
    canceller_id: int
    canceller_stack: Optional[List[traceback.FrameSummary]] = None


class TracedTask(asyncio.Task):
    _orig_coro: Coroutine
    _termination_stack: Optional[List[traceback.FrameSummary]]

    def __init__(
        self,
        *args,
        termination_info_queue: janus._SyncQueueProxy[TerminatedTaskInfo],
        cancellation_chain_queue: janus._SyncQueueProxy[CancellationChain],
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._termination_info_queue = termination_info_queue
        self._cancellation_chain_queue = cancellation_chain_queue
        self._started_at = time.perf_counter()
        self._termination_stack = None
        self.add_done_callback(self._trace_termination)

    def get_trace_id(self) -> int:
        return hash(
            (
                id(self),
                self.get_name(),
            )
        )

    # TODO: catch self-raised cancelled error
    def _trace_termination(self, _: asyncio.Task[Any]) -> None:
        self_id = self.get_trace_id()
        if not self.cancelled() and self.exception() is None:
            exc_repr = None
            termination_stack = None  # completed
        else:
            if self.cancelled():
                exc_repr = "<cancelled>"
            else:
                exc_repr = repr(self.exception())
            termination_stack = self._termination_stack
        task_info = TerminatedTaskInfo(
            self_id,
            name=self.get_name(),
            coro=_format_coroutine(self._orig_coro).partition(" ")[0],
            cancelled=self.cancelled(),
            exc_repr=exc_repr,
            started_at=self._started_at,
            terminated_at=time.perf_counter(),
            termination_stack=termination_stack,
            canceller_stack=None,
        )
        self._termination_info_queue.put_nowait(task_info)

    def cancel(self, msg: Optional[str] = None) -> bool:
        try:
            canceller_task = asyncio.current_task()
        except RuntimeError:
            canceller_task = None
        if canceller_task is not None:
            assert isinstance(canceller_task, TracedTask)
            canceller_stack = _extract_stack_from_frame(sys._getframe())[:-1]
            self._cancellation_chain_queue.put_nowait(
                CancellationChain(
                    self.get_trace_id(),
                    canceller_task.get_trace_id(),
                    canceller_stack,
                )
            )
        return super().cancel(msg=msg)
