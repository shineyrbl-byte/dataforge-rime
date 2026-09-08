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
            "passengers": [{"type": "adult"} for _ in range(max(1, adults))],
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

            results.append(
                {
                    "offer_id": offer.get("id"),
                    "airline": owner.get("name"),
                    "price": offer.get("total_amount"),
                    "currency": offer.get("total_currency"),
                    "duration": first_slice.get("duration"),
                    "stops": max(0, len(segments) - 1),
                    "departure": first_segment.get("departing_at"),
                    "arrival": last_segment.get("arriving_at"),
                }
            )

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
        if not offer_passengers:
            return {
                "tool": "create_flight_booking",
                "status": "error",
                "message": "The selected offer does not contain any passengers.",
            }

        passengers = []

        for i, passenger in enumerate(offer_passengers):
            if i == 0:
                passengers.append(
                    {
                        "id": passenger["id"],
                        "type": "adult",
                        "given_name": "Amelia",
                        "family_name": "Earhart",
                        "title": "ms",
                        "gender": "f",
                        "born_on": "1995-07-24",
                        "email": "amelia.earhart@example.com",
                        "phone_number": "+442080160509",
                    }
                )
            else:
                passengers.append(
                    {
                        "id": passenger["id"],
                        "type": "adult",
                        "given_name": "John",
                        "family_name": "Doe",
                        "title": "mr",
                        "gender": "m",
                        "born_on": "1994-05-15",
                        "email": "john.doe@example.com",
                        "phone_number": "+442080160510",
                    }
                )

        payload = {
            "data": {
                "type": "instant",
                "selected_offers": [offer_id],
                "payments": [],
                "passengers": passengers,
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


def get_currency_for_destination(destination: str) -> str | None:
    """Return the local currency for a destination."""

    COUNTRY_CURRENCY = {
        "kazakhstan": "KZT",
        "almaty": "KZT",
        "astana": "KZT",
        # Asia
        "india": "INR",
        "japan": "JPY",
        "china": "CNY",
        "south korea": "KRW",
        "korea": "KRW",
        "north korea": "KPW",
        "thailand": "THB",
        "vietnam": "VND",
        "indonesia": "IDR",
        "malaysia": "MYR",
        "singapore": "SGD",
        "macau": "MOP",
        "philippines": "PHP",
        "taiwan": "TWD",
        "hong kong": "HKD",
        "nepal": "NPR",
        "bhutan": "BTN",
        "sri lanka": "LKR",
        "bangladesh": "BDT",
        "pakistan": "PKR",
        "myanmar": "MMK",
        "cambodia": "KHR",
        "laos": "LAK",
        "mongolia": "MNT",
        "brunei": "BND",
        "timor-leste": "USD",
        "uae": "AED",
        "kyrgyzstan": "KGS",
        "united arab emirates": "AED",
        "saudi arabia": "SAR",
        "bahrain": "BHD",
        "kuwait": "KWD",
        "oman": "OMR",
        "jordan": "JOD",
        "qatar": "QAR",
        "israel": "ILS",
        "turkey": "TRY",
        "maldives": "MVR",
        "lebanon": "LBP",
        "iran": "IRR",
        "iraq": "IQD",
        "türkiye": "TRY",
        "uzbekistan": "UZS",
        "georgia": "GEL",
        "armenia": "AMD",
        "azerbaijan": "AZN",
        "tajikistan": "TJS",
        "turkmenistan": "TMT",
        # Europe
        "united kingdom": "GBP",
        "uk": "GBP",
        "england": "GBP",
        "scotland": "GBP",
        "wales": "GBP",
        "france": "EUR",
        "germany": "EUR",
        "italy": "EUR",
        "spain": "EUR",
        "portugal": "EUR",
        "netherlands": "EUR",
        "belgium": "EUR",
        "austria": "EUR",
        "ireland": "EUR",
        "greece": "EUR",
        "finland": "EUR",
        "luxembourg": "EUR",
        "malta": "EUR",
        "cyprus": "EUR",
        "estonia": "EUR",
        "latvia": "EUR",
        "lithuania": "EUR",
        "slovakia": "EUR",
        "slovenia": "EUR",
        "croatia": "EUR",
        "andorra": "EUR",
        "sweden": "SEK",
        "norway": "NOK",
        "denmark": "DKK",
        "monaco": "EUR",
        "san marino": "EUR",
        "vatican city": "EUR",
        "kosovo": "EUR",
        "switzerland": "CHF",
        "poland": "PLN",
        "czech republic": "CZK",
        "czechia": "CZK",
        "hungary": "HUF",
        "romania": "RON",
        "ukraine": "UAH",
        "bulgaria": "BGN",
        "serbia": "RSD",
        "iceland": "ISK",
        "albania": "ALL",
        "bosnia and herzegovina": "BAM",
        "montenegro": "EUR",
        "north macedonia": "MKD",
        "moldova": "MDL",
        "russia": "RUB",
        "belarus": "BYN",
        # North America
        "united states": "USD",
        "usa": "USD",
        "canada": "CAD",
        "mexico": "MXN",
        # Caribbean
        "bahamas": "BSD",
        "barbados": "BBD",
        "jamaica": "JMD",
        "trinidad and tobago": "TTD",
        "dominican republic": "DOP",
        "cuba": "CUP",
        "haiti": "HTG",
        # Central America
        "guatemala": "GTQ",
        "belize": "BZD",
        "honduras": "HNL",
        "el salvador": "USD",
        "nicaragua": "NIO",
        "costa rica": "CRC",
        "panama": "PAB",
        # South America
        "brazil": "BRL",
        "argentina": "ARS",
        "chile": "CLP",
        "colombia": "COP",
        "peru": "PEN",
        "uruguay": "UYU",
        "paraguay": "PYG",
        "bolivia": "BOB",
        "ecuador": "USD",
        "venezuela": "VES",
        "guyana": "GYD",
        "suriname": "SRD",
        # Oceania
        "australia": "AUD",
        "new zealand": "NZD",
        "fiji": "FJD",
        "samoa": "WST",
        "tonga": "TOP",
        "vanuatu": "VUV",
        "solomon islands": "SBD",
        "papua new guinea": "PGK",
        "palau": "USD",
        "micronesia": "USD",
        "marshall islands": "USD",
        "kiribati": "AUD",
        "tuvalu": "AUD",
        "nauru": "AUD",
        # Africa
        "south africa": "ZAR",
        "egypt": "EGP",
        "morocco": "MAD",
        "libya": "LYD",
        "kenya": "KES",
        "nigeria": "NGN",
        "ghana": "GHS",
        "tanzania": "TZS",
        "tunisia": "TND",
        "algeria": "DZD",
        "uganda": "UGX",
        "ethiopia": "ETB",
        "rwanda": "RWF",
        "mauritius": "MUR",
        "seychelles": "SCR",
        "botswana": "BWP",
        "namibia": "NAD",
        "zambia": "ZMW",
        "zimbabwe": "ZWG",
        "mozambique": "MZN",
        "angola": "AOA",
        "senegal": "XOF",
        "ivory coast": "XOF",
        "cote d'ivoire": "XOF",
        "cameroon": "XAF",
        "gabon": "XAF",
        "republic of the congo": "XAF",
        "congo": "XAF",
        "democratic republic of the congo": "CDF",
        "madagascar": "MGA",
        "malawi": "MWK",
        "sierra leone": "SLE",
        "liberia": "LRD",
        "cape verde": "CVE",
        "mali": "XOF",
        "burkina faso": "XOF",
        "niger": "XOF",
        "togo": "XOF",
        "benin": "XOF",
        "guinea-bissau": "XOF",
        "central african republic": "XAF",
        "chad": "XAF",
        "equatorial guinea": "XAF",
        "comoros": "KMF",
        "djibouti": "DJF",
        "eritrea": "ERN",
        "somalia": "SOS",
        "sudan": "SDG",
        "south sudan": "SSP",
        "mauritania": "MRU",
        "burundi": "BIF",
        # Europe / Caucasus
        "liechtenstein": "CHF",
        # Asia
        "afghanistan": "AFN",
        "yemen": "YER",
        "syria": "SYP",
        # Africa
        "eswatini": "SZL",
        "lesotho": "LSL",
        "gambia": "GMD",
        "guinea": "GNF",
        "somaliland": "SOS",
        # Caribbean
        "antigua and barbuda": "XCD",
        "dominica": "XCD",
        "grenada": "XCD",
        "saint kitts and nevis": "XCD",
        "saint lucia": "XCD",
        "saint vincent and the grenadines": "XCD",
    }

    CITY_CURRENCY = {
        # India
        "mumbai": "INR",
        "delhi": "INR",
        "new delhi": "INR",
        "bangalore": "INR",
        "bengaluru": "INR",
        "hyderabad": "INR",
        "chennai": "INR",
        "kolkata": "INR",
        "pune": "INR",
        "goa": "INR",
        "kyrgyzstan": "KGS",
        "bishkek": "KGS",
        "kazakhstan": "KZT",
        "almaty": "KZT",
        "astana": "KZT",
        # Japan
        "tokyo": "JPY",
        "osaka": "JPY",
        "kyoto": "JPY",
        # China
        "beijing": "CNY",
        "shanghai": "CNY",
        # South Korea
        "seoul": "KRW",
        "busan": "KRW",
        # Thailand
        "bangkok": "THB",
        "phuket": "THB",
        "pattaya": "THB",
        # Maldives
        "male": "MVR",
        "malé": "MVR",
        # Turkey
        "istanbul": "TRY",
        "ankara": "TRY",
        "antalya": "TRY",
        "izmir": "TRY",
        "bodrum": "TRY",
        # UAE
        "dubai": "AED",
        "abu dhabi": "AED",
        # Singapore
        "singapore": "SGD",
        # UK
        "london": "GBP",
        "manchester": "GBP",
        "edinburgh": "GBP",
        # Europe
        "paris": "EUR",
        "nice": "EUR",
        "lyon": "EUR",
        "berlin": "EUR",
        "rome": "EUR",
        "madrid": "EUR",
        "barcelona": "EUR",
        "amsterdam": "EUR",
        "vienna": "EUR",
        "lisbon": "EUR",
        "athens": "EUR",
        # Italy
        "milan": "EUR",
        "venice": "EUR",
        "florence": "EUR",
        # Spain
        "seville": "EUR",
        # Germany
        "munich": "EUR",
        "frankfurt": "EUR",
        # Switzerland
        "zurich": "CHF",
        "geneva": "CHF",
        "lucerne": "CHF",
        # USA
        "new york": "USD",
        "los angeles": "USD",
        "chicago": "USD",
        "san francisco": "USD",
        "las vegas": "USD",
        "miami": "USD",
        "seattle": "USD",
        "boston": "USD",
        "orlando": "USD",
        # Canada
        "toronto": "CAD",
        "vancouver": "CAD",
        "montreal": "CAD",
        # Australia
        "sydney": "AUD",
        "melbourne": "AUD",
        "brisbane": "AUD",
        "perth": "AUD",
        # New Zealand
        "auckland": "NZD",
        "wellington": "NZD",
        "queenstown": "NZD",
        # Brazil
        "rio de janeiro": "BRL",
        "sao paulo": "BRL",
        # Mexico
        "mexico city": "MXN",
        "cancun": "MXN",
        # Egypt
        "cairo": "EGP",
        "sharm el sheikh": "EGP",
        # Morocco
        "marrakech": "MAD",
        "casablanca": "MAD",
        # South Africa
        "cape town": "ZAR",
        "johannesburg": "ZAR",
        # Kenya
        "nairobi": "KES",
        # Indonesia
        "bali": "IDR",
        "jakarta": "IDR",
        # Vietnam
        "hanoi": "VND",
        "ho chi minh city": "VND",
        # Malaysia
        "kuala lumpur": "MYR",
        # Philippines
        "manila": "PHP",
        "cebu": "PHP",
        # Portugal
        "porto": "EUR",
        # Greece
        "santorini": "EUR",
        "mykonos": "EUR",
    }

    destination = destination.strip().lower()

    # First check whether the country is present.
    # Examples:
    # "Mumbai, India" -> INR
    # "Istanbul, Turkey" -> TRY
    # "Tokyo, Japan" -> JPY
    for country, currency in COUNTRY_CURRENCY.items():
        if country in destination:
            return currency

    # If only a city was provided, check the city mapping.
    for city, currency in CITY_CURRENCY.items():
        if city in destination:
            return currency

    # Safe fallback if destination cannot be identified.
    return None

async def search_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    adults: int,
    children: int = 0,
) -> dict:
    """Search for real, current hotels using SerpApi Google Hotels."""

    api_key = os.getenv("SERPAPI_KEY")

    if not api_key:
        return {
            "tool": "search_hotels",
            "status": "error",
            "message": "SerpApi key is not configured.",
        }

    currency = get_currency_for_destination(destination)

    params = {
        "engine": "google_hotels",
        "q": destination,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": adults,
        "children": children,
        "currency": currency or "USD",
        "hl": "en",
        "gl": "us",
        "api_key": api_key,
    }

    try:
        response = await asyncio.to_thread(
            requests.get,
            "https://serpapi.com/search.json",
            params=params,
            timeout=20,
        )

        response.raise_for_status()
        data = response.json()

        hotels = data.get("properties", [])

        results = []

        for hotel in hotels:
            rate_per_night = hotel.get("rate_per_night", {})
            total_rate = hotel.get("total_rate", {})

            price_per_night = rate_per_night.get("extracted_lowest")
            total_price = total_rate.get("extracted_lowest")

            results.append(
                {
                    "name": hotel.get("name"),
                    "rating": hotel.get("overall_rating"),
                    "votes": hotel.get("reviews"),
                    "price_per_night": price_per_night,
                    "total_price": total_price,
                    "currency": currency or "USD",
                    "description": hotel.get("description", ""),
                    "amenities": hotel.get("amenities", [])[:8],
                    "check_in_time": hotel.get("check_in_time"),
                    "check_out_time": hotel.get("check_out_time"),
                    "hotel_id": hotel.get("property_token"),
                }
            )

            if len(results) >= 5:
                break

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

    booking_id = (
        f"HTL-{abs(hash((hotel_name, destination, check_in, check_out))) % 100000:05d}"
    )

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
