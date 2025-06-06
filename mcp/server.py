from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from .redis_client import RedisClient
from .rabbitmq_client import RabbitMQClient
from typing import Dict, Any, List

app = FastAPI(title="MCP Server")
redis_client = RedisClient()
rabbitmq_client = RabbitMQClient()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize RabbitMQ connection on startup"""
    await rabbitmq_client.connect()

@app.on_event("shutdown")
def shutdown_event():
    """Close RabbitMQ connection on shutdown"""
    rabbitmq_client.close()

@app.get("/")
async def root():
    return {"message": "MCP Server is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/agent/{agent_id}/state")
async def update_agent_state(agent_id: str, state: Dict[str, Any]):
    """Update an agent's state in Redis"""
    success = await redis_client.set_agent_state(agent_id, state)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update agent state")
    return {"message": "State updated successfully"}

@app.get("/agent/{agent_id}/state")
async def get_agent_state(agent_id: str):
    """Get an agent's state from Redis"""
    state = await redis_client.get_agent_state(agent_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Agent state not found")
    return state

@app.post("/agent/{agent_id}/memory")
async def update_agent_memory(agent_id: str, memory: Dict[str, Any]):
    """Update an agent's memory in Redis"""
    success = await redis_client.update_agent_memory(agent_id, memory)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update agent memory")
    return {"message": "Memory updated successfully"}

@app.get("/agent/{agent_id}/memory")
async def get_agent_memory(agent_id: str):
    """Get an agent's memory from Redis"""
    memory = await redis_client.get_agent_memory(agent_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Agent memory not found")
    return memory

# New RabbitMQ-related endpoints

@app.post("/agent/{agent_id}/register")
async def register_agent(agent_id: str, background_tasks: BackgroundTasks):
    """Register a new agent and create its message queue"""
    success = await rabbitmq_client.create_agent_queue(agent_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register agent")
    return {"message": f"Agent {agent_id} registered successfully"}

@app.post("/agent/{agent_id}/send")
async def send_message_to_agent(
    agent_id: str, 
    message: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Send a message to a specific agent"""
    routing_key = f"agent.{agent_id}.message"
    success = await rabbitmq_client.send_message(routing_key, message)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send message")
    return {"message": "Message sent successfully"}

@app.post("/broadcast")
async def broadcast_message(
    message: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Broadcast a message to all agents"""
    routing_key = "agent.broadcast"
    success = await rabbitmq_client.send_message(routing_key, message)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to broadcast message")
    return {"message": "Broadcast sent successfully"} 