"""
Data models for FlexMON API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, Enum):
    THRESHOLD = "threshold"
    RATIO = "ratio"
    ANOMALY = "anomaly"
    ABSENCE = "absence"
    LOG_QUERY = "log_query"


class UserRole(str, Enum):
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_REPORTER = "tenant_reporter"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"


# Metric Models
class MetricPoint(BaseModel):
    """Single metric data point"""
    timestamp: datetime
    tenant_id: str
    host: str
    metric_name: str
    value: float
    tags: Optional[Dict[str, str]] = {}


class CPUMetric(BaseModel):
    """CPU metrics"""
    timestamp: datetime
    tenant_id: str
    host: str
    cpu_percent: float
    cpu_user: float
    cpu_system: float
    cpu_idle: float
    cpu_iowait: Optional[float] = 0.0


class MemoryMetric(BaseModel):
    """Memory metrics"""
    timestamp: datetime
    tenant_id: str
    host: str
    memory_total: int
    memory_used: int
    memory_free: int
    memory_percent: float
    swap_total: int
    swap_used: int
    swap_free: int
    swap_percent: float


class DiskMetric(BaseModel):
    """Disk metrics"""
    timestamp: datetime
    tenant_id: str
    host: str
    device: str
    mountpoint: str
    total: int
    used: int
    free: int
    percent: float


class NetworkMetric(BaseModel):
    """Network metrics"""
    timestamp: datetime
    tenant_id: str
    host: str
    interface: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int
    drops_in: int
    drops_out: int


class ProcessMetric(BaseModel):
    """Process metrics"""
    timestamp: datetime
    tenant_id: str
    host: str
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
    username: Optional[str] = None


# Alert Models
class AlertRule(BaseModel):
    """Alert rule definition"""
    id: Optional[int] = None
    name: str
    description: str
    type: AlertType
    metric: str
    condition: Optional[str] = None  # >, <, >=, <=, ==
    threshold: Optional[float] = None
    duration_minutes: int = 5
    severity: Severity = Severity.WARNING
    enabled: bool = True
    tenant_id: Optional[str] = None
    tags: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Alert(BaseModel):
    """Alert instance"""
    id: Optional[int] = None
    rule_id: Optional[int] = None
    rule_name: str
    tenant_id: str
    host: str
    severity: Severity
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    tags: Dict[str, str] = {}


# User Models
class User(BaseModel):
    """User model"""
    id: Optional[int] = None
    username: str
    email: Optional[str] = None
    role: UserRole
    tenant_id: Optional[str] = None
    enabled: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class UserCreate(BaseModel):
    """User creation request"""
    username: str
    password: str
    email: Optional[str] = None
    role: UserRole
    tenant_id: Optional[str] = None


class UserLogin(BaseModel):
    """Login request"""
    username: str
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Discovery Models
class AgentFingerprint(BaseModel):
    """Agent fingerprint for discovery"""
    hostname: str
    uuid: str
    mac_address: str
    ip_address: str
    os: str
    os_version: str
    architecture: str


class AgentRegistration(BaseModel):
    """Agent registration request"""
    fingerprint: AgentFingerprint
    tenant_id: Optional[str] = None


class AgentInfo(BaseModel):
    """Agent information"""
    id: Optional[int] = None
    fingerprint: str
    hostname: str
    tenant_id: Optional[str] = None
    licensed: bool = False
    ignore_logs: bool = False
    ignore_alerts: bool = False
    collection_interval_sec: int = 30
    last_seen: Optional[datetime] = None
    registered_at: Optional[datetime] = None


# Notification Models
class NotificationConfig(BaseModel):
    """Notification channel configuration"""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any]  # Channel-specific configuration


class NotificationRequest(BaseModel):
    """Notification send request"""
    channel: NotificationChannel
    tenant_id: str
    severity: Severity
    subject: str
    message: str
    metadata: Optional[Dict[str, Any]] = {}


# Health Check
class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]
