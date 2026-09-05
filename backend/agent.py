from livekit.agents import function_tool
from backend.tools.registry import get_tool
from backend.tools.executor import execute_tool
import logging
from dotenv import load_dotenv
from backend.state.conversation import Booking

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    UserStateChangedEvent,
    WorkerOptions,
    cli,
)
from livekit.plugins import deepgram, groq, rime, silero

from backend.config import GROQ_API_KEY, GROQ_MODEL
from backend.control.turn_controller import TurnController

load_dotenv()
logger = logging.getLogger("travel-agent")


class TravelAgent(Agent):
    def __init__(self, controller: TurnController):
        self.controller = controller

        super().__init__(
            instructions=(
    "You are a concise travel operations voice assistant. "
    "Help the user manage flights and hotels. "
    "Keep responses short because they are spoken aloud. "

    "You have tools for checking flight availability, modifying flights, "
    "and confirming hotels. "

    "When the user asks to reschedule, change, modify, or book a flight, "
    "you MUST use the flight availability and modification tools. "

    "When the user asks to keep or confirm a hotel, "
    "you MUST use the hotel confirmation tool. "

    "Do not ask for a booking ID if you can infer the booking from the "
    "conversation or available booking state. "

    "For a request involving multiple travel items, handle each relevant "
    "item using the appropriate tool before giving your final spoken response."
),
        )

    @function_tool
    async def check_flight_availability(self, destination: str) -> str:
        """Check flight availability.
        ALWAYS call this tool when the user asks to reschedule,
        change, modify, or move a flight.
        """

        generation = self.controller.current_generation

        if generation is None:
            return "No active generation."

        tool = get_tool("check_availability")

        result = await execute_tool(
            self.controller,
            generation.generation_id,
            "check_availability",
            tool,
            destination,
        )

        return str(result)

    @function_tool
    async def modify_flight(
        self,
        destination: str,
    ) -> str:
        """Modify a flight booking.
        
        ALWAYS call this tool when the user asks to reschedule,
        change, modify, or move a flight.
        """

        generation = self.controller.current_generation

        if generation is None:
            return "No active generation."

        tool = get_tool("modify_booking")

        booking_id = next(
            (
                booking.booking_id
                for booking in self.controller.state.bookings.values()
                if booking.booking_type == "flight"
                and booking.destination.lower() == destination.lower()
            ),
            None,
        )

        if booking_id is None:
            return f"No confirmed flight found for {destination}."

        result = await execute_tool(
            self.controller,
            generation.generation_id,
            "modify_booking",
            tool,
            booking_id,
            destination,
        )

        return str(result)

    @function_tool
    async def confirm_hotel(self, booking_id: str) -> str:
        """Confirm a hotel booking."""

        generation = self.controller.current_generation

        if generation is None:
            return "No active generation."

        tool = get_tool("confirm_booking")

        result = await execute_tool(
            self.controller,
            generation.generation_id,
            "confirm_booking",
            tool,
            booking_id,
        )

        return str(result)

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    controller = TurnController()
    controller.state.bookings = {
    "FL123": Booking(
        booking_id="FL123",
        booking_type="flight",
        destination="Tokyo",
        status="confirmed",
    ),
    "HT456": Booking(
        booking_id="HT456",
        booking_type="hotel",
        destination="Paris",
        status="confirmed",
    ),
}
    context = controller.start_generation()
    logger.info(
        "Started generation %s",
        context.generation.generation_id,
    )

    session = AgentSession(
        stt=deepgram.STT(),
        llm=groq.LLM(
            api_key=GROQ_API_KEY,
            model=GROQ_MODEL,
        ),
        tts=rime.TTS(
            model="coda",
            speaker="celeste",
            use_websocket=True,
            segment="bySentence",
        ),
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=TravelAgent(controller),
    )

    @session.on("user_state_changed")
    def on_user_state_changed(ev: UserStateChangedEvent):
        if ev.new_state != "speaking":
            return

        current = controller.current_generation

        if current is None:
            return

        generation_id = current.generation_id

        # Only invalidate the generation if there is active
        # asynchronous work that could still commit.
        if not controller.has_active_operations(generation_id):
            logger.info(
                "USER STARTED SPEAKING: no active operations in generation %s",
                generation_id,
            )
            return

        logger.info(
            "USER STARTED SPEAKING: invalidating generation %s",
            generation_id,
        )

        invalidated = controller.invalidate_current_generation()

        logger.info(
            "Generation %s invalidated: %s",
            generation_id,
            invalidated,
        )

    # Startup greeting
    await session.generate_reply(
        instructions="Say exactly: Hello! I'm your travel operations assistant. How can I help you?",
        allow_interruptions=False,
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )