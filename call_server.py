#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from livekit import api
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Outbound Call API", version="1.0.0")

AGENT_NAME = "my-telephony-agent"
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

class CallRequest(BaseModel):
    phone_number: str
    custom_instructions: str = "You are making an outbound call. Be polite and professional. You are to identify yourself as Laura and always start your conversation with the following line: Hi, This is Laura with ABC roofing. We will be in your neighborhood tomorrow and wanted to come by for a free inspection. stick true to the goal of what ABC roofing stands for and even when the user tries to veer of conversations"

class CallResponse(BaseModel):
    success: bool
    message: str
    room_name: str = None
    call_id: str = None

@app.post("/make-call", response_model=CallResponse)
async def make_call(request: CallRequest):
    try:
        if not request.phone_number.startswith('+'):
            raise HTTPException(status_code=400, detail="Phone number must start with + (e.g., +15551234567)")
        clean_number = request.phone_number.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        room_name = f"outbound-call-{clean_number}"
        print(f"📞 Making call to {request.phone_number}")
        print(f"🏠 Room name: {room_name}")
        print(f"🤖 Agent name: {AGENT_NAME}")
        lkapi = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        )
        metadata = {
            "phone_number": request.phone_number,
            "custom_instructions": request.custom_instructions
        }
        print(f"📋 Metadata: {metadata}")
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
    try:
        lkapi = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        )
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
    try:
        lkapi = api.LiveKitAPI(
            url=LIVEKIT_URL,
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        )
        await lkapi.room.delete_room(
            api.DeleteRoomRequest(room=room_name)
        )
        return {"success": True, "message": f"Call in room {room_name} ended"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end call: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "outbound-call-api"}

@app.get("/")
async def root():
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