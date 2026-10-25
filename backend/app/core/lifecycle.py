import asyncio
import logging
import cv2
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
import numpy as np

from app.sources.camera_source import CameraSourceWorker
from app.sampling.random_sampler import RandomBucketSampler
from app.analytics.pipeline import PipelineOrchestrator
from app.vision.detection_schema import AnalyticsSnapshot, AlertEvent
from app.api.ws import manager as ws_manager

logger = logging.getLogger("metro.lifecycle")


class CameraLifecycleManager:
    """
    Manages active camera workers, background 1 Hz sampling loops,
    and automatic WebSocket broadcasting of snapshots and alerts.
    """

    def __init__(self, orchestrator: Optional[PipelineOrchestrator] = None):
        self.orchestrator = orchestrator or PipelineOrchestrator()
        self.workers: Dict[str, CameraSourceWorker] = {}
        self.samplers: Dict[str, RandomBucketSampler] = {}
        self.latest_snapshots: Dict[str, AnalyticsSnapshot] = {}
        self.latest_jpeg_frames: Dict[str, bytes] = {}

        self._sampling_task: Optional[asyncio.Task] = None
        self._running = False

    def start_manager(self):
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._sampling_task = loop.create_task(self._sampling_event_loop())
                logger.info("CameraLifecycleManager background event loop started.")
            except RuntimeError:
                logger.warning("No running asyncio event loop detected; sampling loop will start upon first request.")

    def stop_manager(self):
        self._running = False
        if self._sampling_task and not self._sampling_task.done():
            self._sampling_task.cancel()
        for cam_id in list(self.workers.keys()):
            self.stop_camera(cam_id)
        logger.info("CameraLifecycleManager stopped.")

    def start_camera(self, camera_id: str, source_ref: str) -> bool:
        """Starts decoding thread and initializes 1 Hz bucket sampler."""
        if camera_id in self.workers and self.workers[camera_id].status == "CONNECTED":
            return True

        worker = CameraSourceWorker(camera_id=camera_id, source_ref=source_ref)
        worker.start()
        self.workers[camera_id] = worker
        self.samplers[camera_id] = RandomBucketSampler(seed=None)
        logger.info(f"Registered and started camera '{camera_id}' ({source_ref})")
        return True

    def stop_camera(self, camera_id: str):
        """Stops video decode worker and cleans up sampler state."""
        if camera_id in self.workers:
            self.workers[camera_id].stop()
            del self.workers[camera_id]
        if camera_id in self.samplers:
            del self.samplers[camera_id]
        logger.info(f"Stopped camera '{camera_id}'")

    def get_snapshot(self, camera_id: str) -> Optional[AnalyticsSnapshot]:
        return self.latest_snapshots.get(camera_id)

    def get_latest_jpeg(self, camera_id: str) -> Optional[bytes]:
        return self.latest_jpeg_frames.get(camera_id)

    async def _sampling_event_loop(self):
        """
        Background loop ticking at ~20 Hz (50 ms).
        For each camera, queries sampler to check if it's time to process this second's jittered frame.
        """
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                for camera_id, worker in list(self.workers.items()):
                    if worker.status != "CONNECTED":
                        continue

                    sampler = self.samplers.get(camera_id)
                    if not sampler:
                        continue

                    frame, captured_at, w, h = worker.get_latest_frame()
                    if frame is None or captured_at is None:
                        continue

                    # Check 1 Hz random bucket condition
                    decision = sampler.evaluate_sample(
                        camera_id=camera_id,
                        current_time=now,
                        latest_slot_frame=frame,
                        frame_captured_at=captured_at
                    )

                    if decision.status == "ACCEPTED":
                        # Run through Pipeline Orchestrator (Person A detector + Person B tracking & rules)
                        loop = asyncio.get_running_loop()
                        snapshot, alerts = await loop.run_in_executor(
                            None,
                            self.orchestrator.process_sampled_frame,
                            camera_id,
                            decision.frame_data,
                            decision.actual_capture_time,
                            decision.bucket_start,
                            decision.target_offset_ms
                        )

                        # Update cache for REST queries
                        self.latest_snapshots[camera_id] = snapshot

                        # Cache JPEG bytes for GET /frame.jpg
                        ret, buffer = cv2.imencode(".jpg", decision.frame_data)
                        if ret:
                            self.latest_jpeg_frames[camera_id] = buffer.tobytes()

                        # 1. Broadcast snapshot delta over WebSocket
                        await ws_manager.broadcast(
                            event_type="analytics.snapshot.updated",
                            camera_id=camera_id,
                            data=snapshot.model_dump(by_alias=True, mode="json"),
                            event_id=f"snap_{int(now.timestamp())}"
                        )

                        # 2. Broadcast any new alerts immediately
                        for alert in alerts:
                            await ws_manager.broadcast(
                                event_type="alert.created",
                                camera_id=camera_id,
                                data=alert.model_dump(by_alias=True, mode="json"),
                                event_id=alert.event_id
                            )

                await asyncio.sleep(0.05)  # 50 ms tick
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sampling event loop: {e}", exc_info=True)
                await asyncio.sleep(0.1)


# Global singleton lifecycle manager instance
lifecycle_manager = CameraLifecycleManager()
