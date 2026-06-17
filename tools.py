"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    listings = load_listings()

    # Filter by price and size
    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]
    if size is not None:
        size_lower = size.lower()
        listings = [l for l in listings if size_lower in l["size"].lower()]

    # Score by keyword overlap against title, description, category, style_tags, and colors
    keywords = description.lower().split()

    def score(listing: dict) -> int:
        haystack = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing.get("style_tags", [])),
            " ".join(listing.get("colors", [])),
        ]).lower()
        return sum(1 for kw in keywords if kw in haystack)

    scored = [(score(l), l) for l in listings]
    scored = [(s, l) for s, l in scored if s > 0]   # drop zero-score listings
    scored.sort(key=lambda x: x[0], reverse=True)

    return [l for _, l in scored[:3]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    items = wardrobe.get("items", [])

    if not items:
        prompt = (
            f"A user is thrifting and considering buying this item:\n"
            f"  Name: {new_item['title']}\n"
            f"  Category: {new_item['category']}\n"
            f"  Colors: {', '.join(new_item.get('colors', []))}\n"
            f"  Style tags: {', '.join(new_item.get('style_tags', []))}\n\n"
            f"They have no existing wardrobe. Give them 1–2 sentences of general "
            f"styling advice for this item — what kinds of pieces it pairs well with, "
            f"what occasions it suits, or how to style it."
        )
        response = _get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    client = _get_groq_client()

    # Format wardrobe items into a readable list for the prompt
    wardrobe_lines = "\n".join(
        f"- {item['name']} ({item['category']}), "
        f"colors: {', '.join(item.get('colors', []))}, "
        f"tags: {', '.join(item.get('style_tags', []))}"
        for item in items
    )

    prompt = (
        f"A user is thrifting and considering buying this item:\n"
        f"  Name: {new_item['title']}\n"
        f"  Category: {new_item['category']}\n"
        f"  Colors: {', '.join(new_item.get('colors', []))}\n"
        f"  Style tags: {', '.join(new_item.get('style_tags', []))}\n\n"
        f"Their current wardrobe:\n{wardrobe_lines}\n\n"
        f"Suggest 1–2 complete outfits that pair the new item with specific named "
        f"pieces from the wardrobe. Each outfit should include at minimum a top, "
        f"bottom, and shoes if the new item isn't already one of those. "
        f"Write the suggestion as freeform sentences, referencing the wardrobe "
        f"pieces by name."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )

    suggestion = response.choices[0].message.content.strip()
    return suggestion if suggestion else "No outfit could be suggested."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    if not outfit or not outfit.strip():
        return "Could not generate fit card — outfit information was incomplete."
    
    if not new_item.get("title"):
        return "Missing item details — please re-run the listing search and try again."

    client = _get_groq_client()

    prompt = (
        f"Write a 2–4 sentence Instagram caption for this thrifted outfit.\n\n"
        f"Thrifted item: {new_item['title']}\n"
        f"Price: ${new_item['price']}\n"
        f"Platform: {new_item['platform']}\n"
        f"Full outfit: {outfit}\n\n"
        f"Rules:\n"
        f"- Sound like a real person's OOTD post, casual and authentic\n"
        f"- Mention the item name, price, and platform once each, naturally\n"
        f"- Capture the specific vibe of the outfit (don't be generic)\n"
        f"- You can use 1–2 emojis if they fit the tone\n"
        f"- Do NOT sound like a product description or ad copy\n"
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.2,
    )

    caption = response.choices[0].message.content.strip()
    return caption if caption else (
        "Couldn't generate a fit card. Please provide more outfit details and try again."
    )
