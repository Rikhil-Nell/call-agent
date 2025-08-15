from dotenv import load_dotenv
from livekit import agents, api
from livekit.agents import AgentSession, Agent, RoomInputOptions, get_job_context
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import json
import asyncio

load_dotenv()

class Assistant(Agent):
    def __init__(self, custom_instructions=None) -> None:
        instructions = custom_instructions or """
        You are a helpful voice AI assistant making an outbound phone call."""
        super().__init__(instructions=instructions)
    
    async def detected_answering_machine(self):
        """Call this tool if you have detected a voicemail system, AFTER hearing the voicemail greeting"""
        await self.session.generate_reply(
            instructions="Leave a voicemail message letting the user know you'll call back later."
        )
        await asyncio.sleep(0.5)
        await hangup_call()
    
    async def end_call(self):
        """Called when the user wants to end the call"""
        await hangup_call()

async def hangup_call():
    """End the call for all participants"""
    ctx = get_job_context()
    if ctx is None:
        return
    
    await ctx.api.room.delete_room(
        api.DeleteRoomRequest(
            room=ctx.room.name,
        )
    )

async def entrypoint(ctx: agents.JobContext):
    print(f"🚀 Agent starting - Room: {ctx.room.name}")
    print(f"📋 Job metadata: {ctx.job.metadata}")
    
    await ctx.connect()
    
    phone_number = None
    custom_instructions = None
    if ctx.job.metadata:
        try:
            dial_info = json.loads(ctx.job.metadata)
            phone_number = dial_info.get("phone_number")
            custom_instructions = dial_info.get("custom_instructions")
            print(f"📞 Phone number: {phone_number}")
            print(f"📝 Custom instructions: {custom_instructions}")
        except json.JSONDecodeError:
            print("❌ Invalid metadata format")
    
    if phone_number:
        print(f"📞 Placing outbound call to {phone_number}")
        
        sip_participant_identity = phone_number
        
        try:
            print(f"🔗 Creating SIP participant with trunk: ")
            await ctx.api.sip.create_sip_participant(api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id='ST_rEvidSM4Yoyn',
                sip_call_to=phone_number,
                participant_identity=sip_participant_identity,
                wait_until_answered=True,
            ))

            print("✅ Call picked up successfully")
        except api.TwirpError as e:
            print(f"❌ Error creating SIP participant: {e.message}, "
                  f"SIP status: {e.metadata.get('sip_status_code')} "
                  f"{e.metadata.get('sip_status')}")
            ctx.shutdown()
            return
    
    print("🤖 Starting agent session...")
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=cartesia.TTS(model="sonic-2", voice="c8605446-247c-4d39-acd4-8f4c28aa363c"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )
    
    await session.start(
        room=ctx.room,
        agent=Assistant(custom_instructions),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )
    
    print("✅ Agent session started successfully")
    
    if phone_number is None:
        print("👋 Sending greeting for inbound call...")
        await session.generate_reply(
            instructions="Greet the user and offer your assistance."
        )
    else:
        print("📞 Outbound call - waiting for recipient to speak first...")

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="my-telephony-agent"
    ))
