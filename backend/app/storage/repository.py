import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()


class CameraRecord(Base):
    __tablename__ = "cameras"

    camera_id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    source_ref = Column(String(512), nullable=False)
    enabled = Column(Boolean, default=True)
    config_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AlertEventRecord(Base):
    __tablename__ = "alert_events"

    event_id = Column(String(64), primary_key=True)
    camera_id = Column(String(64), nullable=False, index=True)
    type = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False)
    status = Column(String(32), default="new", index=True)
    occurred_at = Column(DateTime, nullable=False, index=True)
    confidence = Column(Float, default=1.0)
    evidence_json = Column(Text, default="{}")
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)


class AnalyticsSnapshotRecord(Base):
    __tablename__ = "analytics_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(64), nullable=False, index=True)
    sampled_at = Column(DateTime, nullable=False, index=True)
    visible_count = Column(Integer, default=0)
    active_count = Column(Integer, default=0)
    density_class = Column(String(16), default="LOW")
    density_score = Column(Float, default=0.0)
    inference_ms = Column(Float, default=0.0)
    pipeline_ms = Column(Float, default=0.0)
    sample_age_ms = Column(Integer, default=0)


class Repository:
    """
    Person B SQLite Database Repository:
    Provides persistence for cameras, analytics snapshots, and alerts.
    """

    def __init__(self, db_url: str = "sqlite:///metro_safety.db"):
        self.engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    # --- Camera CRUD ---
    def save_camera(self, camera_id: str, name: str, source_ref: str, config: Optional[Dict[str, Any]] = None) -> CameraRecord:
        with self.get_session() as session:
            record = session.query(CameraRecord).filter(CameraRecord.camera_id == camera_id).first()
            if not record:
                record = CameraRecord(
                    camera_id=camera_id,
                    name=name,
                    source_ref=source_ref,
                    config_json=json.dumps(config or {})
                )
                session.add(record)
            else:
                record.name = name
                record.source_ref = source_ref
                record.config_json = json.dumps(config or {})
            session.commit()
            session.refresh(record)
            return record

    def list_cameras(self) -> List[CameraRecord]:
        with self.get_session() as session:
            return session.query(CameraRecord).all()

    def get_camera(self, camera_id: str) -> Optional[CameraRecord]:
        with self.get_session() as session:
            return session.query(CameraRecord).filter(CameraRecord.camera_id == camera_id).first()

    # --- Alert CRUD ---
    def save_alert(self, event_id: str, camera_id: str, event_type: str, severity: str,
                   confidence: float, evidence: dict, occurred_at: datetime) -> AlertEventRecord:
        with self.get_session() as session:
            record = session.query(AlertEventRecord).filter(AlertEventRecord.event_id == event_id).first()
            if not record:
                record = AlertEventRecord(
                    event_id=event_id,
                    camera_id=camera_id,
                    type=event_type,
                    severity=severity,
                    confidence=confidence,
                    evidence_json=json.dumps(evidence),
                    occurred_at=occurred_at
                )
                session.add(record)
            else:
                record.occurred_at = occurred_at
                record.evidence_json = json.dumps(evidence)
                record.confidence = confidence
            session.commit()
            session.refresh(record)
            return record

    def acknowledge_alert(self, event_id: str, actor_id: str = "operator") -> Optional[AlertEventRecord]:
        with self.get_session() as session:
            record = session.query(AlertEventRecord).filter(AlertEventRecord.event_id == event_id).first()
            if record:
                record.status = "acknowledged"
                record.acknowledged_at = datetime.now(timezone.utc)
                evidence = json.loads(record.evidence_json or "{}")
                evidence["acknowledged_by"] = actor_id
                record.evidence_json = json.dumps(evidence)
                session.commit()
                session.refresh(record)
                return record
            return None

    def list_alerts(self, camera_id: Optional[str] = None, severity: Optional[str] = None, limit: int = 50) -> List[AlertEventRecord]:
        with self.get_session() as session:
            q = session.query(AlertEventRecord)
            if camera_id:
                q = q.filter(AlertEventRecord.camera_id == camera_id)
            if severity:
                q = q.filter(AlertEventRecord.severity == severity)
            return q.order_by(AlertEventRecord.occurred_at.desc()).limit(limit).all()

    # --- Analytics Snapshots ---
    def record_snapshot(self, camera_id: str, sampled_at: datetime, visible_count: int,
                        active_count: int, density_class: str, density_score: float,
                        inference_ms: float, pipeline_ms: float, sample_age_ms: int):
        with self.get_session() as session:
            snapshot = AnalyticsSnapshotRecord(
                camera_id=camera_id,
                sampled_at=sampled_at,
                visible_count=visible_count,
                active_count=active_count,
                density_class=density_class,
                density_score=density_score,
                inference_ms=inference_ms,
                pipeline_ms=pipeline_ms,
                sample_age_ms=sample_age_ms
            )
            session.add(snapshot)
            session.commit()
