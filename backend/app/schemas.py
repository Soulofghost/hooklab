from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class CreateEndpointRequest(BaseModel):
    name: str = Field(..., description="Endpoint label, e.g. Stripe Payment Ingest")
    secret: Optional[str] = Field(default="", description="Optional HMAC-SHA256 signing secret")
    forward_url: Optional[str] = Field(default="", description="Optional forwarding destination URL")

class EndpointResponse(BaseModel):
    id: str
    token: str
    name: str
    secret: str
    forward_url: str
    status: str
    total_events: int
    webhook_url: str
    created_at: str

class WebhookEventResponse(BaseModel):
    id: str
    endpoint_id: str
    method: str
    path: str
    headers: Dict[str, str]
    query_params: str
    body: str
    signature_verified: bool
    client_ip: str
    received_at: str

class ReplayRequest(BaseModel):
    target_url: Optional[str] = Field(default=None, description="Target destination URL for webhook replay")

class ReplayResponse(BaseModel):
    attempt_id: str
    event_id: str
    target_url: str
    http_status: int
    response_time_ms: float
    success: bool
    attempted_at: str
