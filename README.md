# FitFindr

A secondhand shopping agent that takes a natural language query, finds matching listings, suggests outfits using your existing wardrobe, and generates a shareable fit card — all in one planning loop.

---

## Tool Inventory

### `search_listings`
**File:** `tools.py`

| Parameter | Type | Description |
|---|---|---|
| `description` | `str` | Keywords describing the item (e.g. "vintage graphic tee") |
| `size` | `str \| None` | Size filter, e.g. `"M"` or `"8"` |
| `max_price` | `float \| None` | Upper price bound in dollars |

**Returns:** `list[dict]` — up to 3 matching listing dicts, sorted by keyword relevance score descending. Returns an empty list if nothing matches.

**Purpose:** Loads all 40 mock listings from `data/listings.json`, filters by price and size, then scores each remaining listing by keyword overlap across its `title`, `description`, `category`, `style_tags`, and `colors` fields. Listings with zero keyword overlap are dropped entirely. The top 3 are returned.

---

### `suggest_outfit`
**File:** `tools.py`

| Parameter | Type | Description |
|---|---|---|
| `new_item` | `dict` | The selected listing dict |
| `wardrobe` | `dict` | The user's wardrobe in the schema format |

**Returns:** `str` — 1–2 sentences of freeform styling advice or outfit pairings referencing specific wardrobe pieces by name. Returns `"No outfit could be suggested."` if the LLM returns empty.

**Purpose:** Sends a prompt to `llama-3.3-70b-versatile` via Groq. If the wardrobe has items, the prompt asks the LLM to pair the new item with named pieces from the wardrobe. If the wardrobe is empty, it falls back to general styling advice for the item's category and style tags.

---

### `create_fit_card`
**File:** `tools.py`

| Parameter | Type | Description |
|---|---|---|
| `outfit` | `str` | The outfit suggestion string from `suggest_outfit` |
| `new_item` | `dict` | The selected listing dict |

**Returns:** `str` — A 2–4 sentence Instagram-style OOTD caption mentioning the item name, price, and platform.

**Purpose:** Sends a prompt to `llama-3.3-70b-versatile` at `temperature=1.2` to generate a casual, authentic-sounding fit card. The elevated temperature intentionally introduces variety so the output doesn't read like ad copy.

---

## How the Planning Loop Works

The loop lives in `run_agent()` in `agent.py`. It runs as a linear pipeline — each step depends on the previous one succeeding — but includes two guard conditions that can cause early termination and one retry.

**Step 1 — Parse the query.** The agent uses regex to extract a `size` token (`size M`, `size 8`, etc.) and a `max_price` token (`under $30`) from the raw query string. Both are optional. What remains after stripping those tokens becomes the `description` string passed to search. This is deterministic and requires no LLM call.

**Step 2 — Search.** `search_listings` runs with the parsed parameters. If it returns an empty list, the agent immediately sets `session["error"]` and exits — there is no point asking the LLM to style an item that doesn't exist.

**Step 3 — Select top result.** The agent picks `results[0]` (the highest-scoring listing) as `selected_item`. No ranking decision is made here; the sort order from `search_listings` is trusted.

**Step 4 — Guard on wardrobe.** Before calling `suggest_outfit`, the loop checks whether `wardrobe["items"]` is non-empty. An empty wardrobe triggers a specific error message telling the user to add pieces and try again. This is a separate guard from the no-results guard because the failure mode and the user-facing message are different.

**Step 5 — Suggest outfit.** `suggest_outfit` is called with the selected item and the wardrobe. If the LLM returns an empty string or a string containing "no outfit", the agent treats this as an unrecoverable soft failure and sets an error.

**Step 6 — Create fit card, with one retry.** `create_fit_card` is called on the outfit suggestion. If the result is empty or contains "could not generate fit card", the agent re-calls `suggest_outfit` to generate a fresh outfit suggestion, then calls `create_fit_card` a second time. This handles the case where the first outfit suggestion was grammatically valid but too thin to produce a good caption.

**Step 7 — Return session.** The full session dict is returned. `session["error"]` is `None` on success; all three output values (`selected_item`, `outfit_suggestion`, `fit_card`) are populated.

The Gradio `handle_query()` function in `app.py` maps the session to the three output panels: listing text, outfit suggestion, and fit card. An error in the session surfaces in the listing panel with the other two panels left empty.

---

## State Management

A single `session` dict is the only state object. It is created at the start of `run_agent()` and passed by reference through all steps. No global state is used, and no state persists between calls — each user query initializes a completely fresh session.

Fields written by each step:

| Step | Fields set |
|---|---|
| Init | `query`, `wardrobe`, `parsed`, `search_results`, `selected_item`, `outfit_suggestion`, `fit_card`, `error` (all defaults) |
| Parse | `session["parsed"]` |
| Search | `session["search_results"]` |
| Select | `session["selected_item"]` |
| Suggest | `session["outfit_suggestion"]` |
| Fit card | `session["fit_card"]` |
| Any failure | `session["error"]` |

The Gradio layer maintains no state of its own. The wardrobe choice (example vs. empty) is re-loaded from disk on every request via `get_example_wardrobe()` or `get_empty_wardrobe()`.

---

## Error Handling

Each failure point in the pipeline produces a distinct error string that surfaces in the Gradio listing panel.

**`search_listings` returns empty list**

The filter + keyword scorer drops any listing with zero keyword overlap. If the combined price, size, and keyword constraints produce no results, `session["error"]` is set to:

> "I couldn't find any listings that matched. Try a different description, size, or price."

Concrete test case from the CLI test in `agent.py`: query `"designer ballgown size XXS under $5"`. No listings match all three constraints simultaneously, so the search returns `[]` and the loop exits immediately without making any LLM calls.

**Empty wardrobe**

If `wardrobe["items"]` is an empty list (the user selected "Empty wardrobe" in the Gradio UI), the agent exits with:

> "Your wardrobe is empty — add some pieces and try again."

Note: `suggest_outfit` itself also handles an empty wardrobe gracefully by switching to general styling advice. The agent-level guard catches this before the LLM call to avoid wasting a Groq request when the output would be generic.

**`suggest_outfit` returns empty or "no outfit"**

If the LLM response is empty or explicitly signals no outfit is possible, the agent sets `session["error"]` to the LLM's returned string (or a fallback). This handles cases where the new item is so niche that the model cannot construct a coherent pairing.

**`create_fit_card` returns incomplete output**

Rather than failing, the agent retries once: it re-generates the outfit suggestion with a fresh `suggest_outfit` call, then passes the new suggestion to `create_fit_card`. If the retry also fails, the partial fit card is stored anyway (the second call's output is accepted regardless). This avoids surfacing an error to the user for what is typically just LLM variance.

---

## Spec Reflection

The spec made implementing the tools individually very smooth, Claude had no problem generating them because of how solid I made it. Where the implementation started diverging was after going through Milestone 5 testing failure modes. To both return a generic styling string when triggering `suggest_outfit` with an empty wardrobe and correctly return a descriptive error message string when triggering `create_fit_card` with an empty outfit string the empty wardrobe check needed to be done right before `suggest_outfit` instead. 

---

## AI Usage

**Instance 1 — `create_fit_card` prompt tone**
(attached tools.py and data_loader.py)
"Implement this function into tools.py using load_listings() from data_loader.py
Here is the spec block:"

    ### Tool 1: search_listings

    **What it does:**
    <!-- Describe what this tool does in 1–2 sentences -->
    Searches for available item listings based on details the user gives as input to find and return the best matching listing.

    **Input parameters:**
    <!-- List each parameter, its type, and what it represents -->
    - `description` (str): A string that provides a detailed description of the item
    - `size` (str): A freeform string that represents sizes for different pieces of clothing (example S, W30 L30, US7)
    - `max_price` (float): The maximum price a returned item can be, anything equal to or lower is allowed.

    **What it returns:**
    <!-- Describe the return value — what fields does a result contain? -->
    Returns three listings that best match the description, the top result is given as a result new_item.

    **What happens if it fails or returns nothing:**
    <!-- What should the agent do if no listings match? -->
    Return an empty list and tell the user there is no available match then return early. 

Generated a good function that didn't need changes

**Instance 2 — `suggest_outfit` empty wardrobe branch**

"Now implement this function into tools.py using get_example_wardrobe(), get_empty_wardrobe() from the data loader.
Here is the spec block:"

    ### Tool 2: suggest_outfit

    **What it does:**
    <!-- Describe what this tool does in 1–2 sentences -->
    Given an item and the users wardrobe returns a outfit suggestion made up of the item and matching items from the wardrobe (example given a shoe adds on a top and bottom at least)

    **Input parameters:**
    <!-- List each parameter, its type, and what it represents -->
    - `new_item` (dict): The new item returned by tool 1
    - `wardrobe` (dict): A dictionary with an "items" key containing a list of clothing item objects, each with fields: id, name, category, colors, style_tags, and notes.

    **What it returns:**
    <!-- Describe the return value -->
    Returns a string that is a freeform sentence description of an outfit suggestion named suggestion.

    **What happens if it fails or returns nothing:**
    <!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
    Return a string that says that wardrobe is empty or no outfit could be suggested respectively then return early

As said in the spec reflection to pass Milestone 5's failure tests the empty wardrobe case had to be checked right before `suggest_outfit`.



