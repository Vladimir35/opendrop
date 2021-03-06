import asyncio
from typing import Optional

import numpy as np

from opendrop.processing.conan import (
    apply_foreground_detection,
    extract_drop_profile,
)
from opendrop.utility.bindable import BoxBindable, AccessorBindable, thread_safe_bindable_collection, Bindable
from opendrop.utility.updaterworker import UpdaterWorker


class FeatureExtractorParams:
    def __init__(self) -> None:
        self.bn_drop_region_px = BoxBindable(None)
        self.bn_thresh = BoxBindable(30)


class FeatureExtractor:
    _Data = thread_safe_bindable_collection(
        fields=[
            'bn_foreground_detection',
            'bn_drop_profile_px',
        ]
    )

    def __init__(self, image: Bindable[np.ndarray], params: 'FeatureExtractorParams', *,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._loop = loop or asyncio.get_event_loop()

        self._bn_image = image

        self.params = params

        self._data = self._Data(
            _loop=self._loop,
            bn_foreground_detection=None,
            bn_drop_profile_px=None,
        )

        self.is_busy = AccessorBindable(getter=self.get_is_busy)
        self._updater_worker = UpdaterWorker(
            do_update=self._update,
            on_idle=self.is_busy.poke,
            loop=self._loop,
        )

        self.bn_foreground_detection = self._data.bn_foreground_detection  # type: Bindable[Optional[np.ndarray]]
        self.bn_drop_profile_px = self._data.bn_drop_profile_px  # type: Bindable[Optional[np.ndarray]]

        # Update extracted features whenever image or params change.
        self._bn_image.on_changed.connect(self._queue_update)
        self.params.bn_drop_region_px.on_changed.connect(self._queue_update)
        self.params.bn_thresh.on_changed.connect(self._queue_update)

        # First update to initialise features.
        self._queue_update()

    def _queue_update(self) -> None:
        was_busy = self._updater_worker.is_busy
        self._updater_worker.queue_update()
        if not was_busy:
            self.is_busy.poke()

    # This method will be run on different threads (could be called by UpdaterWorker), so make sure it stays
    # thread-safe.
    def _update(self) -> None:
        editor = self._data.edit(timeout=1)
        assert editor is not None

        try:
            new_foreground_detection = self._apply_foreground_detection()
            new_drop_profile_px = self._extract_drop_profile_px(new_foreground_detection)

            editor.set_value('bn_foreground_detection', new_foreground_detection)
            editor.set_value('bn_drop_profile_px', new_drop_profile_px)
        except Exception as exc:
            # If any exceptions occur, discard changes and re-raise the exception.
            editor.discard()
            raise exc
        else:
            # Otherwise commit the changes.
            editor.commit()

    def _apply_foreground_detection(self) -> Optional[np.ndarray]:
        image = self._bn_image.get()
        if image is None:
            return None

        return apply_foreground_detection(
            image=image,
            thresh=self.params.bn_thresh.get(),
        )

    def _extract_drop_profile_px(self, binary_image: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if binary_image is None:
            return None

        drop_region = self.params.bn_drop_region_px.get()
        if drop_region is None:
            return None

        drop_region = drop_region.as_type(int)

        drop_image = binary_image[drop_region.y0:drop_region.y1, drop_region.x0:drop_region.x1]

        drop_profile_px = extract_drop_profile(drop_image)
        drop_profile_px += drop_region.pos

        return drop_profile_px

    def get_is_busy(self) -> bool:
        return self._updater_worker.is_busy

    async def wait_until_not_busy(self) -> None:
        while self.is_busy.get():
            await self.is_busy.on_changed.wait()
