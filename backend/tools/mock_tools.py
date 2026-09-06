import asyncio
import os
import requests
from dotenv import load_dotenv

async def check_availability(destination: str) -> dict:
    await asyncio.sleep(0.5)

    return {
        "tool": "check_availability",
        "destination": destination,
        "available": True,
    }


async def modify_booking(booking_id: str, destination: str) -> dict:
    try:
        await asyncio.sleep(8.0)
    except asyncio.CancelledError:
        # Deliberately ignore cancellation to simulate
        # an external operation that cannot be stopped.
        await asyncio.sleep(2.0)

    return {
        "tool": "modify_booking",
        "booking_id": booking_id,
        "destination": destination,
        "status": "modified",
    }


async def confirm_booking(booking_id: str) -> dict:
    await asyncio.sleep(0.8)

    return {
        "tool": "confirm_booking",
        "booking_id": booking_id,
        "status": "confirmed",
    }
import os
import requests
from dotenv import load_dotenv

load_dotenv()

async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int,
    cabin_class: str = "economy",
) -> dict:
    """Search for real flight offers using Duffel test mode."""

    token = os.getenv("DUFFEL_API_TOKEN")

    if not token:
        return {
            "tool": "search_flights",
            "status": "error",
            "message": "Duffel API token is not configured.",
        }

    payload = {
        "data": {
            "slices": [
                {
                    "origin": origin.upper(),
                    "destination": destination.upper(),
                    "departure_date": departure_date,
                }
            ],
            "passengers": [
                {"type": "adult"}
                for _ in range(max(1, adults))
            ],
            "cabin_class": cabin_class,
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Duffel-Version": "v2",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        response = await asyncio.to_thread(
            requests.post,
            "https://api.duffel.com/air/offer_requests",
            headers=headers,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()
        data = response.json().get("data", {})

        offers = data.get("offers", [])[:5]

        results = []

        for offer in offers:
            slices = offer.get("slices", [])
            first_slice = slices[0] if slices else {}
            segments = first_slice.get("segments", [])
            first_segment = segments[0] if segments else {}
            last_segment = segments[-1] if segments else {}

            owner = offer.get("owner") or {}

            results.append({
                "offer_id": offer.get("id"),
                "airline": owner.get("name"),
                "price": offer.get("total_amount"),
                "currency": offer.get("total_currency"),
                "duration": first_slice.get("duration"),
                "stops": max(0, len(segments) - 1),
                "departure": first_segment.get("departing_at"),
                "arrival": last_segment.get("arriving_at"),
            })

        return {
            "tool": "search_flights",
            "status": "success",
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departure_date": departure_date,
            "adults": adults,
            "cabin_class": cabin_class,
            "offers": results,
        }

    except Exception as e:
        return {
            "tool": "search_flights",
            "status": "error",
            "message": f"Flight search failed: {str(e)}",
        }

async def create_flight_booking(offer_id: str) -> dict:
    """Create a flight order using Duffel test mode."""

    token = os.getenv("DUFFEL_API_TOKEN")

    if not token:
        return {
            "tool": "create_flight_booking",
            "status": "error",
            "message": "Duffel API token is not configured.",
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Duffel-Version": "v2",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        # First retrieve the offer so we know its price/currency.
        offer_response = await asyncio.to_thread(
            requests.get,
            f"https://api.duffel.com/air/offers/{offer_id}",
            headers=headers,
            timeout=30,
        )
        offer_response.raise_for_status()

        offer_data = offer_response.json().get("data", {})
        offer_passengers = offer_data.get("passengers", [])
        if len(offer_passengers) < 2:
            return {
                "tool": "create_flight_booking",
                "status": "error",
                "message": "The selected offer does not contain two passengers.",
            }

        passenger_0_id = offer_passengers[0]["id"]
        passenger_1_id = offer_passengers[1]["id"]

        payload = {
            "data": {
                "type": "instant",
                "selected_offers": [offer_id],
                "payments": [],
                "passengers": [
                    {
                        "id": passenger_0_id,
                        "type": "adult",
                        "given_name": "Amelia",
                        "family_name": "Earhart",
                        "title": "ms",
                        "gender": "f",
                        "born_on": "1995-07-24",
                        "email": "amelia.earhart@example.com",
                        "phone_number": "+442080160509",
                    },
                    {
                        "id": passenger_1_id,
                        "type": "adult",
                        "given_name": "John",
                        "family_name": "Doe",
                        "title": "mr",
                        "gender": "m",
                        "born_on": "1994-05-15",
                        "email": "john.doe@example.com",
                        "phone_number": "+442080160510",
                    },
                ],
            }
        }

        amount = offer_data.get("total_amount")
        currency = offer_data.get("total_currency")

        if not amount or not currency:
            return {
                "tool": "create_flight_booking",
                "status": "error",
                "message": "The selected offer has no valid price.",
            }

        payload["data"]["payments"] = [
            {
                "type": "balance",
                "amount": amount,
                "currency": currency,
            }
        ]

        response = await asyncio.to_thread(
            requests.post,
            "https://api.duffel.com/air/orders",
            headers=headers,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json().get("data", {})

        return {
            "tool": "create_flight_booking",
            "status": "created",
            "booking_id": data.get("id"),
            "booking_reference": data.get("booking_reference"),
            "offer_id": offer_id,
            "total_amount": data.get("total_amount"),
            "total_currency": data.get("total_currency"),
        }

    except requests.HTTPError as e:
        message = str(e)

        try:
            error_data = response.json()
            message = error_data.get("errors", error_data)
        except Exception:
            pass

        return {
            "tool": "create_flight_booking",
            "status": "error",
            "message": str(message),
        }

    except Exception as e:
        return {
            "tool": "create_flight_booking",
            "status": "error",
            "message": f"Flight booking failed: {str(e)}",
        }

def get_currency_for_destination(destination: str) -> str:
    """Return the currency for a destination without a network lookup."""

    CURRENCY_BY_DESTINATION = {
        "japan": "JPY",
        "tokyo": "JPY",
        "osaka": "JPY",

        "france": "EUR",
        "paris": "EUR",

        "germany": "EUR",
        "berlin": "EUR",

        "italy": "EUR",
        "rome": "EUR",

        "spain": "EUR",
        "madrid": "EUR",

        "united kingdom": "GBP",
        "uk": "GBP",
        "london": "GBP",

        "india": "INR",
        "mumbai": "INR",
        "delhi": "INR",

        "united states": "USD",
        "usa": "USD",
        "new york": "USD",
        "los angeles": "USD",

        "canada": "CAD",
        "toronto": "CAD",
        "vancouver": "CAD",

        "australia": "AUD",
        "sydney": "AUD",
        "melbourne": "AUD",

        "singapore": "SGD",

        "dubai": "AED",
        "uae": "AED",
        "united arab emirates": "AED",

        "switzerland": "CHF",
        "zurich": "CHF",
        "geneva": "CHF",
    }

    key = destination.strip().lower()
    return CURRENCY_BY_DESTINATION.get(key, "USD")

async def search_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    adults: int,
    children: int = 0,
) -> dict:
    """Search for real, current hotels using StayAPI."""

    api_key = os.getenv("STAYAPI_KEY")

    if not api_key:
        return {
            "tool": "search_hotels",
            "status": "error",
            "message": "StayAPI key is not configured.",
        }

    params = {
        "location": destination,
        "check_in": check_in,
        "check_out": check_out,
        "adults": adults,
        "currency": get_currency_for_destination(destination),
    }

    try:
        response = await asyncio.to_thread(
            requests.get,
            "https://api.stayapi.com/v1/google_hotels/search",
            headers={"X-API-Key": api_key},
            params=params,
            timeout=20,
        )

        response.raise_for_status()
        data = response.json()

        hotels = data.get("hotels", [])[:5]

        results = []

        for hotel in hotels:
            price = hotel.get("price", {})
            rating = hotel.get("rating", {})

            results.append({
                "name": hotel.get("name"),
                "rating": rating.get("value"),
                "votes": rating.get("votes"),
                "price_per_night": price.get("price_per_night"),
                "currency": price.get("currency") or params["currency"],
                "description": hotel.get("description"),
                "amenities": hotel.get("amenities", [])[:8],
                "check_in_time": hotel.get("check_in_time"),
                "check_out_time": hotel.get("check_out_time"),
                "hotel_id": hotel.get("hotel_id"),
            })

        return {
            "tool": "search_hotels",
            "status": "success",
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "hotels": results,
        }

    except Exception as e:
        return {
            "tool": "search_hotels",
            "status": "error",
            "message": f"Hotel search failed: {str(e)}",
        }
async def create_hotel_booking(
    hotel_name: str,
    destination: str,
    check_in: str,
    check_out: str,
    adults: int,
    children: int = 0,
    price_per_night: float | None = None,
    currency: str | None = None,
) -> dict:
    """Create a mock hotel booking after the user selects a hotel.

    This simulates an external booking operation that may finish
    even after the user interrupts the conversation.
    """

    # Simulate an external booking system.
    try:
        await asyncio.sleep(3.0)
    except asyncio.CancelledError:
        # Deliberately ignore cancellation so the Generation Fence
        # has to reject the late result.
        await asyncio.sleep(2.0)

    booking_id = f"HTL-{abs(hash((hotel_name, destination, check_in, check_out))) % 100000:05d}"

    return {
        "tool": "create_hotel_booking",
        "status": "created",
        "booking_id": booking_id,
        "booking_type": "hotel",
        "hotel_name": hotel_name,
        "destination": destination,
        "check_in": check_in,
        "check_out": check_out,
        "adults": adults,
        "children": children,
        "price_per_night": price_per_night,
        "currency": currency,
    }
