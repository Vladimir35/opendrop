import math
from typing import Optional, Tuple

from opendrop.utility.bindable import Bindable
from opendrop.utility.geometry import Rect2, Vector2, Line2


class DefineLinePluginModel:
    def __init__(self, in_line: Bindable[Line2[int]], in_clip: Bindable[Optional[Rect2[int]]]) -> None:
        self.bn_line = in_line
        self._bn_clip = in_clip

        self._begin_define_pos = None

    def begin_define(self, begin_pos: Vector2[float]) -> None:
        assert not self.is_defining
        self._begin_define_pos = begin_pos

    def commit_define(self, end_pos: Vector2[float]) -> None:
        assert self.is_defining
        start_pos = self._begin_define_pos
        self._begin_define_pos = None

        if start_pos == end_pos:
            return

        line = Line2(
            p0=start_pos,
            p1=end_pos,
        )

        self.bn_line.set(line)

    def discard_define(self) -> None:
        assert self.is_defining
        self._begin_define_pos = None

    @property
    def is_defining(self) -> bool:
        return self._begin_define_pos is not None

    @property
    def begin_define_pos(self) -> Vector2:
        return self._begin_define_pos

    def nudge_up(self) -> None:
        # Decreasing image y-coordinate is upwards
        self._nudge((0, -1))

    def nudge_down(self) -> None:
        self._nudge((0, 1))

    def _nudge(self, delta: Tuple[float, float]) -> None:
        line = self.bn_line.get()
        if line is None:
            return

        new_line = Line2(
            p0=line.p0 + delta,
            p1=line.p1 + delta
        )

        self.bn_line.set(new_line)

    def nudgerot_clockwise(self) -> None:
        self._nudgerot(-0.001)

    def nudgerot_anticlockwise(self) -> None:
        self._nudgerot(0.001)

    def _nudgerot(self, delta: float) -> None:
        """Rotate the currently selected line anticlockwise by `delta` radians.
        """
        line = self.bn_line.get()
        if line is None:
            return

        clip = self._bn_clip.get()
        if clip is not None:
            center_x = (clip.x0 + clip.x1)/2
        else:
            center_x = line.p0.x

        line_angle = math.atan(line.gradient)
        new_line_angle = line_angle - delta

        new_p0 = line.eval_at(x=center_x)
        new_p1 = new_p0 + (math.cos(new_line_angle), math.sin(new_line_angle))

        new_line = Line2(p0=new_p0, p1=new_p1)

        self.bn_line.set(new_line)
