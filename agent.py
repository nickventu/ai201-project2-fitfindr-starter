"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse query with regex
    import re

    size_match = re.search(r'\bsize\s+(\S+)', query, re.IGNORECASE)
    price_match = re.search(r'under\s+\$?([\d.]+)', query, re.IGNORECASE)

    size = size_match.group(1) if size_match else None
    max_price = float(price_match.group(1)) if price_match else None
    # Strip size/price phrases to get a cleaner description
    description = re.sub(r'(size\s+\S+|under\s+\$?[\d.]+)', '', query, flags=re.IGNORECASE).strip()

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    # Step 3: search_listings
    results = search_listings(
        description=description,
        size=size,
        max_price=max_price,
    )
    session["search_results"] = results

    if not results:
        session["error"] = "I couldn't find any listings that matched. Try a different description, size, or price."
        return session

    # Step 4: Select top result
    session["selected_item"] = results[0]

    # Step 5: suggest_outfit
    outfit_suggestion = suggest_outfit(
        new_item=session["selected_item"],
        wardrobe=wardrobe,
    )
    session["outfit_suggestion"] = outfit_suggestion

    if not outfit_suggestion or "empty" in outfit_suggestion.lower() or "no outfit" in outfit_suggestion.lower():
        session["error"] = outfit_suggestion or "Wardrobe is empty or no outfit could be suggested."
        return session

    # Step 6: create_fit_card (with one retry via suggest_outfit if incomplete)
    fit_card = create_fit_card(
        outfit=outfit_suggestion,
        new_item=session["selected_item"],
    )

    if not fit_card or "more information" in fit_card.lower() or "incomplete" in fit_card.lower():
        # Re-run suggest_outfit then retry create_fit_card
        outfit_suggestion = suggest_outfit(
            new_item=session["selected_item"],
            wardrobe=wardrobe,
        )
        session["outfit_suggestion"] = outfit_suggestion
        fit_card = create_fit_card(
            outfit=outfit_suggestion,
            new_item=session["selected_item"],
        )

    session["fit_card"] = fit_card

    # Step 7: Return session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
