#!/usr/bin/env python3
"""
FastAPI server to trigger outbound calls
Run this to create an HTTP endpoint for making calls
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from livekit import api
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Outbound Call API", version="1.0.0")

# Configuration
AGENT_NAME = "my-telephony-agent"  # Must match your agent.py
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

class CallRequest(BaseModel):
    phone_number: str
    custom_instructions: str = "You are making an outbound call. Be polite and professional."

class CallResponse(BaseModel):
    success: bool
    message: str
    room_name: str = None
    call_id: str = None

@app.post("/make-call", response_model=CallResponse)
async def make_call(request: CallRequest):
    """
    Make an outbound call to the specified phone number
    """
    try:
        # Validate phone number format
        if not request.phone_number.startswith('+'):
            raise HTTPException(status_code=400, detail="Phone number must start with + (e.g., +15551234567)")
        
        # Create unique room name
        clean_number = request.phone_number.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        room_name = f"outbound-call-{clean_number}"
        
        print(f"📞 Making call to {request.phone_number}")
        print(f"🏠 Room name: {room_name}")
        print(f"🤖 Agent name: {AGENT_NAME}")
        
        # Create LiveKit API client
        lkapi = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        )
        
        # Prepare metadata with phone number and custom instructions
        metadata = {
            "phone_number": request.phone_number,
            "custom_instructions": request.custom_instructions
        }
        
        print(f"📋 Metadata: {metadata}")
        
        # Dispatch the agent to make the call
        dispatch_response = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room_name,
                metadata=json.dumps(metadata)
            )
        )
        
        print(f"✅ Dispatch created successfully")
        print(f"🆔 Response: {dispatch_response}")
        
        return CallResponse(
            success=True,
            message=f"Call initiated to {request.phone_number}",
            room_name=room_name,
            call_id=getattr(dispatch_response, 'dispatch_id', 'unknown')
        )
        
    except Exception as e:
        print(f"❌ Error making call: {str(e)}")
        print(f"📊 Error type: {type(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")


@app.get("/call-status/{room_name}")
async def get_call_status(room_name: str):
    """
    Get the status of an ongoing call
    """
    try:
        lkapi = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        )
        
        # Get room info
        room_info = await lkapi.room.list_rooms(
            api.ListRoomsRequest(names=[room_name])
        )
        
        if not room_info.rooms:
            return {"status": "not_found", "message": "Call room not found"}
        
        room = room_info.rooms[0]
        
        return {
            "status": "active" if room.num_participants > 0 else "ended",
            "participants": room.num_participants,
            "creation_time": room.creation_time,
            "room_name": room_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get call status: {str(e)}")

@app.delete("/end-call/{room_name}")
async def end_call(room_name: str):
    """
    End an ongoing call
    """
    try:
        lkapi = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        )
        
        # Delete the room to end the call
        await lkapi.room.delete_room(
            api.DeleteRoomRequest(room=room_name)
        )
        
        return {"success": True, "message": f"Call in room {room_name} ended"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end call: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "outbound-call-api"}

@app.get("/")
async def root():
    """
    API documentation
    """
    return {
        "message": "Outbound Call API",
        "endpoints": {
            "POST /make-call": "Make an outbound call",
            "GET /call-status/{room_name}": "Get call status",
            "DELETE /end-call/{room_name}": "End a call",
            "GET /health": "Health check"
        },
        "example_usage": {
            "curl": "curl -X POST http://localhost:8000/make-call -H 'Content-Type: application/json' -d '{\"phone_number\": \"+15551234567\"}'"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI call server...")
    print(f"📋 Agent name: {AGENT_NAME}")
    print(f"🔗 LiveKit URL: {LIVEKIT_URL}")
    print("📖 API docs will be available at: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)