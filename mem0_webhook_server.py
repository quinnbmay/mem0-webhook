"""
Mem0 Webhook Server - Standalone service for posting memories via webhook
Can be deployed alongside your existing Railway app or as a separate service
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
from mem0 import AsyncMemoryClient
import hashlib
import hmac

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mem0_webhook")

# Initialize FastAPI
app = FastAPI(
    title="Mem0 Webhook API",
    description="Webhook endpoint for posting memories to Mem0",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for your specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment configuration
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "m0-IQGqsMWB42QhWG77RuzpSdNcyEppgRHeBhz0KcNu")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-here")  # Set this for security
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "quinn_may")

# Initialize Mem0 client
mem0_client = AsyncMemoryClient(api_key=MEM0_API_KEY)

# Request/Response models
class MemoryWebhookRequest(BaseModel):
    """Structure for incoming webhook memory requests"""
    content: str = Field(..., description="The memory content to store")
    user_id: Optional[str] = Field(DEFAULT_USER_ID, description="User ID for the memory")
    category: Optional[str] = Field("webhook", description="Memory category")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    client: Optional[str] = Field("webhook", description="Client identifier")
    project_type: Optional[str] = Field("webhook_post", description="Project type")
    source: Optional[str] = Field("webhook", description="Memory source")

class MemoryBatchRequest(BaseModel):
    """Structure for batch memory requests"""
    memories: list[MemoryWebhookRequest] = Field(..., description="List of memories to store")

class MemoryResponse(BaseModel):
    """Response structure for memory operations"""
    success: bool
    message: str
    memory_id: Optional[str] = None
    timestamp: str
    user_id: str

class WebhookHealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    mem0_connected: bool
    webhook_ready: bool

# Security functions
def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature for security (optional)"""
    if not secret or secret == "your-webhook-secret-here":
        return True  # Skip verification if no secret is configured
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

# Core memory functions
async def create_memory(
    content: str,
    user_id: str,
    category: str = "webhook",
    metadata: Optional[Dict] = None,
    client: str = "webhook",
    project_type: str = "webhook_post",
    source: str = "webhook"
) -> Dict:
    """Create a memory in Mem0 with structured metadata"""
    try:
        # Build complete metadata
        full_metadata = {
            "category": category,
            "day": datetime.now().strftime("%Y-%m-%d"),
            "month": datetime.now().strftime("%Y-%m"),
            "year": str(datetime.now().year),
            "client": client,
            "project_type": project_type,
            "device": "webhook_api",
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "webhook_received": datetime.now().isoformat()
        }
        
        # Add any custom metadata
        if metadata:
            full_metadata.update(metadata)
        
        # Create the memory
        messages = [{"role": "user", "content": content}]
        result = await mem0_client.add(
            messages,
            user_id=user_id,
            metadata=full_metadata,
            output_format="v1.1"
        )
        
        logger.info(f"Memory created for user {user_id}: {content[:50]}...")
        
        # Extract memory ID from result
        memory_id = None
        if isinstance(result, dict):
            memory_id = result.get('id') or result.get('results', [{}])[0].get('id')
        elif isinstance(result, list) and result:
            memory_id = result[0].get('id')
        
        return {
            "success": True,
            "memory_id": memory_id,
            "user_id": user_id,
            "content": content,
            "metadata": full_metadata
        }
        
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with service information"""
    html_content = """
    <html>
    <head>
        <title>Mem0 Webhook API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
            code { background: #e0e0e0; padding: 2px 5px; border-radius: 3px; }
            .status { color: green; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🧠 Mem0 Webhook API</h1>
        <p class="status">✅ Service is running!</p>
        
        <h2>Available Endpoints:</h2>
        
        <div class="endpoint">
            <strong>POST /webhook/memory</strong><br>
            Create a single memory<br>
            <code>{"content": "your memory", "user_id": "quinn_may"}</code>
        </div>
        
        <div class="endpoint">
            <strong>POST /webhook/memories/batch</strong><br>
            Create multiple memories<br>
            <code>{"memories": [{"content": "memory 1"}, {"content": "memory 2"}]}</code>
        </div>
        
        <div class="endpoint">
            <strong>POST /webhook/zapier</strong><br>
            Zapier integration endpoint
        </div>
        
        <div class="endpoint">
            <strong>POST /webhook/generic</strong><br>
            Generic webhook (accepts any JSON)
        </div>
        
        <div class="endpoint">
            <strong>GET /health</strong><br>
            Health check endpoint
        </div>
        
        <h3>Test with curl:</h3>
        <pre>curl -X POST https://mem0-webhook-api-production.up.railway.app/webhook/memory \\
  -H "Content-Type: application/json" \\
  -d '{"content": "Test memory", "user_id": "quinn_may"}'</pre>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health", response_model=WebhookHealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Test Mem0 connection
        test_search = await mem0_client.search("test", user_id=DEFAULT_USER_ID, limit=1)
        mem0_connected = True
    except:
        mem0_connected = False
    
    return WebhookHealthResponse(
        status="healthy" if mem0_connected else "degraded",
        timestamp=datetime.now().isoformat(),
        mem0_connected=mem0_connected,
        webhook_ready=True
    )

@app.post("/webhook/memory", response_model=MemoryResponse)
async def webhook_memory_endpoint(
    request: MemoryWebhookRequest,
    x_webhook_signature: Optional[str] = Header(None)
):
    """
    Main webhook endpoint for creating memories
    
    Example usage:
    ```
    curl -X POST https://your-railway-app.railway.app/webhook/memory \
      -H "Content-Type: application/json" \
      -d '{
        "content": "User completed the tutorial on Python basics",
        "user_id": "john_doe",
        "category": "learning",
        "metadata": {"course": "python-101", "lesson": 5}
      }'
    ```
    """
    try:
        # Optional: Verify webhook signature for security
        # if x_webhook_signature and not verify_webhook_signature(...):
        #     raise HTTPException(status_code=401, detail="Invalid signature")
        
        result = await create_memory(
            content=request.content,
            user_id=request.user_id,
            category=request.category,
            metadata=request.metadata,
            client=request.client,
            project_type=request.project_type,
            source=request.source
        )
        
        return MemoryResponse(
            success=True,
            message="Memory created successfully",
            memory_id=result.get("memory_id"),
            timestamp=datetime.now().isoformat(),
            user_id=request.user_id
        )
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/memories/batch")
async def webhook_batch_memories(request: MemoryBatchRequest):
    """
    Batch endpoint for creating multiple memories at once
    
    Example usage:
    ```
    curl -X POST https://your-railway-app.railway.app/webhook/memories/batch \
      -H "Content-Type: application/json" \
      -d '{
        "memories": [
          {"content": "Memory 1", "user_id": "user1"},
          {"content": "Memory 2", "user_id": "user1", "category": "work"}
        ]
      }'
    ```
    """
    results = []
    errors = []
    
    for memory_req in request.memories:
        try:
            result = await create_memory(
                content=memory_req.content,
                user_id=memory_req.user_id,
                category=memory_req.category,
                metadata=memory_req.metadata,
                client=memory_req.client,
                project_type=memory_req.project_type,
                source=memory_req.source
            )
            results.append(result)
        except Exception as e:
            errors.append({
                "content": memory_req.content[:50],
                "error": str(e)
            })
    
    return {
        "success": len(errors) == 0,
        "created": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors if errors else None,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/zapier")
async def zapier_webhook(request: Request):
    """
    Special endpoint for Zapier integration
    Accepts flexible JSON structure
    """
    try:
        body = await request.json()
        
        # Extract content - Zapier might send it in different formats
        content = body.get("content") or body.get("message") or body.get("text") or str(body)
        user_id = body.get("user_id") or body.get("userId") or DEFAULT_USER_ID
        category = body.get("category") or "zapier"
        
        # Extract any additional fields as metadata
        metadata = {k: v for k, v in body.items() 
                   if k not in ["content", "message", "text", "user_id", "userId", "category"]}
        
        result = await create_memory(
            content=content,
            user_id=user_id,
            category=category,
            metadata=metadata,
            client="zapier",
            project_type="automation",
            source="zapier_webhook"
        )
        
        return {
            "success": True,
            "message": "Memory created via Zapier",
            "memory_id": result.get("memory_id"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Zapier webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/generic")
async def generic_webhook(request: Request):
    """
    Generic webhook endpoint that accepts any JSON structure
    Useful for integrations that can't be customized
    """
    try:
        body = await request.json()
        
        # Convert the entire payload to a memory
        content = json.dumps(body, indent=2)
        
        # Try to extract user_id from common fields
        user_id = (body.get("user_id") or 
                  body.get("userId") or 
                  body.get("user") or 
                  body.get("email") or 
                  DEFAULT_USER_ID)
        
        result = await create_memory(
            content=f"Webhook data received: {content}",
            user_id=user_id,
            category="generic_webhook",
            metadata={"raw_payload": body},
            client="generic",
            project_type="webhook",
            source="generic_webhook"
        )
        
        return {
            "success": True,
            "message": "Data stored as memory",
            "memory_id": result.get("memory_id"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Generic webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Run the server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    print("\n🚀 Mem0 Webhook Server")
    print(f"📍 Starting on port {port}")
    print(f"🧠 Mem0 API Key: {'✅ Configured' if MEM0_API_KEY else '❌ Missing'}")
    print(f"🔐 Webhook Secret: {'✅ Set' if WEBHOOK_SECRET != 'your-webhook-secret-here' else '⚠️  Not configured (optional)'}")
    print(f"👤 Default User ID: {DEFAULT_USER_ID}")
    print("\n📝 Available endpoints:")
    print("  POST /webhook/memory - Main memory webhook")
    print("  POST /webhook/memories/batch - Batch memory creation")
    print("  POST /webhook/zapier - Zapier integration")
    print("  POST /webhook/generic - Generic webhook (any JSON)")
    print("  GET /health - Health check")
    print("\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )