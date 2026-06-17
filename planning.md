# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

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

---

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
Returns general styling advice for the item, then return early

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given an outfit from tool 2 and a new_item from tool 1 generates a short, shareable description of a complete outfit - the kind of thing someone would caption an Instagram post with.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (string): An outfit string returned by tool 2
- `new_item` (dict): The new_item returned by tool 1

**What it returns:**
<!-- Describe the return value -->
Return a freeform sentence string that is a short, shareable description of a complete outfit (ex "thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 full look in my stories")

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
Return a string asking for more information on the outfit and prompt the user to input that information, then run tool 2 and try running tool 3 again with the resulting output.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

Given a query run search_listings then check if results is empty
If yes send an error message that return an empty list and tell the user there is no available match then return early
If not set new_item = results[0] and proceed to suggest_outfit
Check if wardrobe is empty, if yes says that wardrobe is empty then return early
Run suggest_outfit then check if an outfit cannot be suggested
If yes send an error message that says outfit could not be suggested respectively then return early
If not set outfit_suggestion = "..." and proceed to create_fit_card
Run create_fit_card then check if outfit_suggestion and new_item are empty/incomplete
If yes send an error message asking for more information and prompt the user to input that information, then run tool 2 and try running tool 3 again with the resulting output.
If not set fit_card = "..." and return it, ending the program.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
The agent uses a session dictionary initialized by _new_session() at the start of each interaction. It tracks the following fields throughout the run:

query — the original user query string
parsed — a dict containing the extracted description, size, and max_price parsed from the query via regex
search_results — the list of matching listing dicts returned by search_listings
selected_item — the top result (search_results[0]), passed as new_item into suggest_outfit and create_fit_card
wardrobe — the wardrobe dict passed in at the start, checked directly by the agent before calling suggest_outfit
outfit_suggestion — the string returned by suggest_outfit, passed as outfit into create_fit_card
fit_card — the string returned by create_fit_card, the final output of a successful interaction
error — set to a descriptive string if the interaction ends early; None on success

State is never passed globally — each tool receives only what it needs as arguments, and results are written back into the session dict immediately after each tool call.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query |"I couldn't find any listings that matched. Try a different description, size, or price."|
| suggest_outfit | Wardrobe is empty |Agent detects empty wardrobe before calling the tool and sets error: "Your wardrobe is empty — add some pieces and try again."|
| suggest_outfit | No outfit could be suggested from wardrobe items |"No outfit could be suggested." → return early|
| create_fit_card | Outfit input is missing or incomplete |"Could not generate fit card — outfit information was incomplete." → re-run suggest_outfit → retry create_fit_card|

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->
User query
    │
    ▼
Planning Loop ────────────────────────────────────────────────┐
    │                                                         │
    ├─► search_listings(description, size, max_price)         │
    │       │                                                 │
    │       ├── results=[]                                    │
    │       │       └──► [ERROR] "No listings found" → return │
    │       │                                                 │
    │       └── results=[item, ...]                           │
    │               │                                         │
    │           Session: new_item = results[0]                │
    │               │                                         │
    ├─► suggest_outfit(new_item, wardrobe)                    │
    │       │                                                 │
    │       ├── wardrobe empty OR no outfit found             │
    │       │       └──► [ERROR] "Wardrobe empty / no match" → return
    │       │                                                 │
    │       └── outfit found                                  │
    │               │                                         │
    │           Session: outfit_suggestion = "..."            │
    │               │                                         │
    ├─► create_fit_card(outfit_suggestion, new_item)          │
    │       │                                                 │
    │       ├── outfit data incomplete                        │
    │       │       └──► [ERROR] "Need more info"             │
    │       │               │                                 │
    │       │           re-run suggest_outfit ────────────────┘
    │       │                                                 
    │       └── success                                       
    │               │                                         
    │           Session: fit_card = "..."                     
    │               │                                         
    └───────────────▼                                         
            Return session

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
For search_listings, I'll give Claude the Tool 1 block from planning.md (inputs, return value, failure mode) and ask it to implement the function using load_listings() from the data loader. Before running it, I'll check that the generated code filters by all three parameters and handles the empty-results case. Then I'll test it with 3 queries(one normal match, one empty result, max_price = 0)

For suggest_outfit, I'll give Claude the Tool 2 block from planning.md (inputs, return value, failure mode) and ask it to implement the function using get_example_wardrobe(), get_empty_wardrobe() from the data loader. Before running it I'll check that the generated code is actually getting items from the wardrobe and handles the empty wardrobe or no available outfit cases. Then I'll test it with 3 queries.(one with example wardrobe, another with empty wardrobe, and one with a wardrobe with only one item)

For create_fit_card, I'll give Claude the Tool 3 block from planning.md (inputs, return value, failure mode) and ask it to implement the function using mock outputs from the test runs of Tools 1/2. Before running I'll check that the generated code is receiving those outputs and handles the incomplete outfit data case. Then I'll test it with 3 queries(one with normal input, one with an incomplete outfit, and one with no new_item)

**Milestone 4 — Planning loop and state management:**
Give Claude the planning loop section and ASCII diagram, ask it to wire the three tools together with the conditional logic, then verify the branching matches my diagram exactly and test with an example query to make sure it is wired correctly.
---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
Agent calls tool search_listings with the inputs: description vintage graphic tee, size any, max_price 30.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
The tool returns three matching listings, chooses the most relevant matching item and then calls tool suggest_outfit with the inputs: new_item matching item and wardrobe user's wardrobe

**Step 3:**
<!-- Continue until the full interaction is complete -->
Step 2 returns an outfit suggestion which alongside the matching item is part of the input for the third tool create_fit_card: outfit suggestion and new_item matching item.

**Final output to user:**
<!-- What does the user actually see at the end? -->
The user is given a matching piece of clothing, outfit suggestion with that item, and a short, shareable description of a complete outfit.
