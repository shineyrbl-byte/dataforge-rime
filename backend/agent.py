from typing import Annotated
from livekit.agents import RunContext, function_tool
from backend.tools.registry import get_tool
from backend.tools.executor import execute_tool
import logging
from dotenv import load_dotenv
from backend.state.conversation import Booking
import time
from datetime import date

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
        today = date.today().isoformat()

        super().__init__(
    instructions=(
        f"Today's date is {today}. "
        "Use today's date as the reference when interpreting natural-language dates. "

        "You are a concise travel operations voice assistant. "
        "Help the user manage flights and hotels. "
        "Keep responses short because they are spoken aloud. "

        "You HAVE tools for real flight search, flight availability, "
        "flight modification, hotel search, and hotel booking. "

        "IMPORTANT FLIGHT RULE: "
        "Whenever the user asks to find, search, look up, or show "
        "flight options, you MUST call the search_flights tool. "
        "Do not say that you cannot search flights. "
        "Do not answer a flight-search request without calling the tool. "

        "For flight searches, obtain the origin airport, destination airport, "
        "departure date, and number of adults. "
        "Convert natural-language dates into YYYY-MM-DD. "
        "Use economy unless another cabin is explicitly requested. "

        "IMPORTANT FLIGHT MODIFICATION RULE: "
        "When the user asks to reschedule, change, modify, or move an existing "
        "flight, use the existing confirmed flight booking in state. "
        "Do NOT ask for the original departure city, departure date, passenger count, "
        "or other flight-search parameters. "
        "If the user provides the destination airport code, use it directly. "
        "For example, if the user says 'Modify my Tokyo flight to TYO', immediately "
        "call modify_flight with destination='TYO'. "
        "Use the flight availability and modification tools as required by the workflow. "

        "IMPORTANT HOTEL SEARCH RULE: "
        "Treat requests for hotels, motels, accommodations, or places to stay "
        "as hotel-search requests. "
        "When the user asks to search for hotels, first check whether all required "
        "hotel search information is available: destination, check-in date, check-out date, "
        "and number of adults. "
        "If ANY required value is missing, DO NOT call search_hotels. "
        "Instead, ask the user only for the missing information. "
        "Never invent or assume missing dates or guest counts. "
        "Once all required information is available, call search_hotels. "
        "Convert natural-language dates into YYYY-MM-DD using today's date as the reference. "

"IMPORTANT HOTEL BOOKING RULE: "
"When the user explicitly selects a hotel and wants to book it, "
"you MUST use the hotel booking tool. "
"Do not ask for information that is already available from the "
"hotel search results or conversation state. "

        "IMPORTANT RESPONSE TIMING RULE: "
        "For operations that may take noticeable time, acknowledge the user's request briefly "
        "before waiting for the tool result. "
        "Examples: "
        "Hotel search: \"Sure, I'll search for some hotels in Paris.\" "
        "Hotel booking: \"Sure, I'll book that hotel for you.\" "
        "Flight search: \"Sure, I'll check the available flights.\" "
        "Flight modification: \"Sure, I'll update your flight.\" "
        "Keep acknowledgements short and natural. "
        "Do not invent results or booking details in the acknowledgement. "
        "The acknowledgement should not imply that the operation has completed."
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

        logger.info(
            "DEBUG BOOKINGS BEFORE MODIFY: %s",
            {
                booking_id: {
                    "type": booking.booking_type,
                    "destination": booking.destination,
                    "status": booking.status,
                }
                for booking_id, booking in self.controller.state.bookings.items()
            },
        )

        logger.info(
            "DEBUG MODIFY DESTINATION: %r",
            destination,
        )

        booking_id = next(
            (
                booking.booking_id
                for booking in self.controller.state.bookings.values()
                if booking.booking_type == "flight"
                and (
                    booking.destination.lower() == destination.lower()
                    or (
                        booking.destination.lower() == "tokyo"
                        and destination.lower() == "tyo"
                    )
                )
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
    
    @function_tool(on_duplicate="reject")
    async def search_hotels(
        self,
        ctx: RunContext,
        destination: Annotated[str, "City or destination where the user wants a hotel"],
        check_in: Annotated[str, "Check-in date in YYYY-MM-DD format"],
        check_out: Annotated[str, "Check-out date in YYYY-MM-DD format"],
        adults: Annotated[int, "Number of adult guests"],
        children: Annotated[int, "Number of child guests"] = 0,
    ) -> str:
        """Find five real hotels using live hotel data.
        Required information:
        - destination
        - check-in date in YYYY-MM-DD format
        - check-out date in YYYY-MM-DD format
        - number of adults
        Optional:
        - number of children, default 0
        
        If any required information is missing, ask the user for it before calling this tool.
        Convert natural-language dates such as "September 15th" into YYYY-MM-DD.
        Never invent dates or guest counts.
        """

        generation = self.controller.current_generation
        await ctx.update("Sure, I'll search up some hotels for you.")
        
        if not check_in or not check_out:
            return "Please provide both check-in and check-out dates."
        if not adults or adults < 1:
            adults = 1
        if children is None:
            children = 0

        if generation is None:
            return "No active conversation generation."

        logger.info(
            "TIMING: hotel_search execute_tool START %.3f",
            time.perf_counter(),
        )

        result = await execute_tool(
            self.controller,
            generation.generation_id,
            "hotel_search",
            get_tool("search_hotels"),
            destination,
            check_in,
            check_out,
            adults,
            children,
        )

        logger.info(
            "TIMING: hotel_search execute_tool END %.3f",
            time.perf_counter(),
        )

        if result.get("status") == "stale_rejected":
            return "The hotel search became outdated because the user changed the request."

        if result.get("status") == "error":
            return f"Hotel search failed: {result.get('message', 'Unknown error')}"

        hotels = result.get("hotels", [])

        if not hotels:
            return f"I couldn't find hotels for {destination}."

        response = [
            f"I found {len(hotels)} hotels in {destination}."
        ]

        for i, hotel in enumerate(hotels, 1):
            name = hotel.get("name", "Unknown hotel")
            rating = hotel.get("rating")
            price = hotel.get("price_per_night")
            currency = hotel.get("currency", "EUR")
            description = hotel.get("description", "")

            details = f"{i}. {name}"

            if rating is not None:
                details += f", rated {rating} out of 5"

            if price is not None:
                details += f", about {price} {currency} per night"

            if description:
                details += f". {description}"

            response.append(details)

        return " ".join(response)

    @function_tool(on_duplicate="reject")
    async def create_flight_booking(
        self,
        ctx: RunContext,
        option_number: Annotated[
            int,
            "The numbered flight option selected by the user, from 1 to 5"
        ],
    ) -> str:
        """Book a selected flight offer using Duffel test mode.

        The user must first search for flights and select one of the
        numbered options. This creates a test-mode Duffel order.
        """

        generation = self.controller.current_generation
        await ctx.update("Sure, I'll book that flight for you.")

        if generation is None:
            return "No active conversation generation."

        offers = self.controller.state.flight_search_results

        if not offers:
            return "There are no flight search results to book."

        if option_number < 1 or option_number > len(offers):
            return (
                f"Please choose a flight option between 1 and "
                f"{len(offers)}."
            )

        offer = offers[option_number - 1]
        offer_id = offer.get("offer_id")

        if not offer_id:
            return "The selected flight does not have a valid offer ID."

        result = await execute_tool(
            self.controller,
            generation.generation_id,
            "flight_booking",
            get_tool("create_flight_booking"),
            offer_id,
        )

        if result.get("status") == "stale_rejected":
            return (
                "The flight booking request became outdated because "
                "the user changed the request."
            )

        if result.get("status") == "error":
            return (
                f"Flight booking failed: "
                f"{result.get('message', 'Unknown error')}"
            )

        booking_id = result.get("booking_id")
        self.controller.state.bookings[booking_id]= Booking(
            booking_id=booking_id,
            booking_type="flight",
            destination=offers[option_number - 1].get("destination", "TYO"),
            status="confirmed",
        )


        return (
            f"Flight booked successfully in Duffel test mode. "
            f"Booking reference {result.get('booking_reference') or booking_id}. "
            f"This is a test booking and no real payment was made."
        )

    @function_tool
    async def search_flights(
        self,
        ctx: RunContext,
        origin: Annotated[str, "3-letter IATA airport code for departure, e.g. BOM for Mumbai"],
        destination: Annotated[str, "3-letter IATA airport code for arrival, e.g. NRT for Tokyo"],
        departure_date: Annotated[str, "Departure date in YYYY-MM-DD format"],
        adults: Annotated[int, "Number of adult passengers"],
        cabin_class: Annotated[str, "Cabin class: economy, premium_economy, business, or first"] = "economy",
    ) -> str:
        """Search real flight offers using Duffel test mode.

        Required:
        - origin airport IATA code
        - destination airport IATA code
        - departure date
        - number of adults

        Convert natural-language dates into YYYY-MM-DD.
        Never invent dates or passenger counts.
        Use economy unless the user requests another cabin.
        """

        generation = self.controller.current_generation
        await ctx.update("Sure, I'll check the available flights.")

        if generation is None:
            return "No active conversation generation."

        if not origin or not destination:
            return "Please provide the departure and arrival airports."

        if not departure_date:
            return "Please provide the departure date."

        if not adults or adults < 1:
            adults = 1

        result = await execute_tool(
            self.controller,
            generation.generation_id,
            "flight_search",
            get_tool("search_flights"),
            origin,
            destination,
            departure_date,
            adults,
            cabin_class,
        )

        if result.get("status") == "stale_rejected":
            return (
                "The flight search became outdated because "
                "the user changed the request."
            )

        if result.get("status") == "error":
            return f"Flight search failed: {result.get('message', 'Unknown error')}"

        offers = result.get("offers", [])
        self.controller.state.flight_search_results = offers

        if not offers:
            return (
                f"I couldn't find available flights from "
                f"{origin} to {destination} on {departure_date}."
            )

        response = [
            f"I found {len(offers)} flight options from "
            f"{origin} to {destination}."
        ]

        for i, offer in enumerate(offers, 1):
            details = f"{i}. {offer.get('airline', 'Airline unknown')}"

            price = offer.get("price")
            currency = offer.get("currency")

            if price is not None:
                details += f", {price} {currency}"

            departure = offer.get("departure")
            arrival = offer.get("arrival")

            if departure:
                details += f", departing {departure}"

            if arrival:
                details += f", arriving {arrival}"

            duration = offer.get("duration")

            if duration:
                details += f", duration {duration}"

            stops = offer.get("stops")

            if stops is not None:
                if stops == 0:
                    details += ", nonstop"
                else:
                    details += f", {stops} stop(s)"

            response.append(details)

        return " ".join(response)

    @function_tool(on_duplicate="reject")
    async def create_hotel_booking(
        self,
        ctx: RunContext,
        hotel_name: Annotated[str, "Exact hotel name selected by the user"],
        destination: Annotated[str, "City or destination of the hotel"],
        check_in: Annotated[str, "Check-in date in YYYY-MM-DD format"],
        check_out: Annotated[str, "Check-out date in YYYY-MM-DD format"],
        adults: Annotated[int, "Number of adult guests"],
        children: Annotated[int, "Number of child guests"] = 0,
        price_per_night: Annotated[float | None, "Price per night of the selected hotel"] = None,
        currency: Annotated[str | None, "Currency of the hotel price"] = None,
    ) -> str:
        """Create a demo hotel booking for a hotel selected by the user.

        This is a simulated booking operation. No real reservation or payment
        is made.

        The user must explicitly select a hotel before this tool is called.
        """

        generation = self.controller.current_generation
        await ctx.update("Sure, I'll book that hotel for you.")

        if generation is None:
            return "No active conversation generation."

        if not hotel_name:
            return "Please tell me which hotel you want to book."

        if not check_in or not check_out:
            return "Please provide the check-in and check-out dates."

        if not adults or adults < 1:
            adults = 1

        if children is None:
            children = 0

        for existing_booking in self.controller.state.bookings.values():
            if (
                existing_booking.booking_type == "hotel"
                and existing_booking.hotel_name
                and existing_booking.hotel_name.lower() == hotel_name.lower()
                and existing_booking.destination.lower() == destination.lower()
                and existing_booking.check_in == check_in
                and existing_booking.check_out == check_out
                and existing_booking.status == "confirmed"
            ):
                return (
                    f"That hotel is already booked. "
                    f"Booking ID {existing_booking.booking_id}."
                )    
        
        result = await execute_tool(
            self.controller,
            generation.generation_id,
            "hotel_booking",
            get_tool("create_hotel_booking"),
            hotel_name,
            destination,
            check_in,
            check_out,
            adults,
            children,
            price_per_night,
            currency,
        )

        if result.get("status") == "stale_rejected":
            return (
                "The booking request became outdated because "
                "the user changed the request."
            )

        if result.get("status") == "error":
            return f"Hotel booking failed: {result.get('message', 'Unknown error')}"

        booking_id = result.get("booking_id")

        self.controller.state.bookings[booking_id] = Booking(
            booking_id=booking_id,
            booking_type="hotel",
            destination=destination,
            status="confirmed",
            hotel_name=hotel_name,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            price_per_night=price_per_night,
            currency=currency,
        )


        return (
            f"Demo booking created for {hotel_name} in {destination}. "
            f"Booking ID {booking_id}. "
            f"No real reservation or payment was made."
        )

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
            use_websocket=False,
            segment="bySentence",
        ),
        vad=silero.VAD.load(),
        preemptive_generation=False,
    )

    logger.info(
        "TIMING: starting AgentSession at %.3f",
        time.perf_counter(),
    )

    await session.start(
        room=ctx.room,
        agent=TravelAgent(controller),
    )

    logger.info(
        "TIMING: AgentSession started at %.3f",
        time.perf_counter(),
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

    logger.info(
        "TIMING: about to generate startup greeting at %.3f",
        time.perf_counter(),
    )
    # Startup greeting
    await session.generate_reply(
        instructions="Say exactly: Hello! I'm your travel operations assistant. How can I help you?",
        allow_interruptions=False,
    )
    logger.info(
        "TIMING: startup greeting generate_reply returned at %.3f",
        time.perf_counter(),
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
