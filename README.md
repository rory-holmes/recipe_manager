# recipe_manager
Recipes


# High-Level Design: Personal Recipe Manager

**Version 1.2 · Python · Local-First · Self-Hosted AI Architecture · Intelligent Meal Planning**

---

## 1. Executive Summary

The **Personal Recipe Manager** is a local-first Python application that manages recipes, discovers new meals, learns user taste preferences over time, and builds an optimized weekly cooking plan.

The application is built around **three independent, decoupled operational pillars**:

1. **Core Application Engine (Offline & Deterministic):** Manages recipe persistence, state transitions, quantity scaling, ingredient canonicalization, unit conversions, shopping lists, preference history, and rules-based logic with zero external or LLM dependencies.
2. **Local Intelligence Gateway (Local AI):** Utilizes a self-hosted LLM (e.g., via Ollama, vLLM, or any OpenAI-compatible local endpoint) for semantic recipe extraction, ingredient attribute classification, contextual recommendation explanations, and batch prep synthesis.
3. **External Discovery Adapters (Online Optional):** Connects to external recipe APIs and live web search when explicitly enabled to retrieve fresh recipe candidates and web content.

The system defaults to **two cooking sessions per week**, with each session producing four portions (designed to cover two days for two people). Users can override session counts, serving quantities, prep constraints, and dietary preferences at any time.

---

## 2. Goals and Scope

### 2.1 Functional Goals

1. **Multi-Source Ingestion:** Accept recipe text, URLs, or raw copied content.
2. **Hybrid Ingestion Pipeline:** Parse unstructured content into structured schemas via a local LLM, followed by deterministic validation and duplicate/variation evaluation.
3. **Structured Domain Normalization:** Map ingredients to canonical IDs, forms, prep methods, and standard dimensional units for reliable shopping aggregation and prep scheduling.
4. **Multi-Source Candidate Discovery:** Query external recipe APIs and web search providers when online discovery is enabled.
5. **Stateful Preference Learning:** Track user feedback events to update feature-level preference weights, distinguishing between *selection likelihood* (convenience) and *predicted enjoyment* (taste).
6. **Transient & One-Off Guidance:** Apply temporary directional filters (e.g., "Quick Mediterranean") or one-off prep/time constraints without polluting long-term profile weights.
7. **Interactive Weekly Planning:** Offer step-by-step candidate selection with explicit state transitions (`Candidate` $\rightarrow$ `Accepted for Week`, `Saved for Later`, `Skipped`, or `Discarded`).
8. **Batch Prep & Synergy Optimization:** Group compatible prep operations (e.g., bulk-chopping aromatics) across accepted recipes while preserving structural food safety and execution dependencies.
9. **Freshness & Perishability Scheduling:** Order weekly meals based on ingredient shelf-life and shopping schedules (e.g., cooking fresh proteins early in the week).
10. **State Persistence:** Retain all recipes, plans, shopping lists, and feedback history across application restarts in a transactional local SQLite database.

### 2.2 Non-Functional Goals

* **Local-First Architecture:** Core functionality remains operational offline without active LLM or internet access.
* **Deterministic Privacy & Network Boundaries:** Local AI models handle semantic tasks locally. External network requests occur exclusively during explicitly user-initiated web discovery or URL extraction.
* **Graceful Degradation:** When the local LLM server is unavailable or offline, the UI provides clear status indicators and falls back to deterministic rule-based workflows.
* **Replaceable Provider Interfaces:** Abstract external APIs and LLM backends behind generic interfaces.
* **Data Integrity:** Require user review for external/LLM-extracted data before canonical database persistence.

### 2.3 Out of Scope for Initial Release

* Multi-user accounts or shared household sync.
* Native mobile applications.
* Supermarket API integrations or automated grocery checkout.
* Guaranteed clinical/medical dietary advice.
* Unsupervised automated modifications to submitted plans.

---

## 3. System Operating Modes & Network Boundaries

### 3.1 Operating Modes

| Operational Feature | Online Mode | Offline Mode | Local AI Unavailable Mode |
| --- | --- | --- | --- |
| **Saved Library & History** | Fully Available | Fully Available | Fully Available |
| **Deterministic Planning & Shopping** | Fully Available | Fully Available | Fully Available |
| **Local LLM Parsing & Extraction** | Fully Available | Fully Available | **Unavailable** (Requires Manual Input/Rule-Based Fallback) |
| **LLM Prep Synergy & Explanations** | Fully Available | Fully Available | **Unavailable** (Deterministic Prep Grouping Only) |
| **External Web / API Discovery** | Fully Available | **Unavailable** (Uses Cached Candidates Only) | **Unavailable** |

### 3.2 Privacy & Security Guarantees

* **Inference Privacy:** All recipe parsing, preference analysis, and prep-planning LLM prompts execute locally. No recipe content or personal preference history is transmitted to cloud LLM providers.
* **Controlled External Egress:** Search terms, request metadata, and API keys leave the local machine *only* during active external recipe discovery queries.
* **SSRF Protections:** Web page extraction blocks private loopback/internal IP addresses, enforces timeout limits, and treats scraped web content as untrusted data rather than system instructions (protecting against prompt injection).

---

## 4. Logical Architecture & Component Responsibilities

```text
               +-------------------------------------------------+
               |             Presentation Layer                  |
               |             (Streamlit Web UI)                  |
               +-----------------------+-------------------------+
                                       |
               +-----------------------v-------------------------+
               |             Application Services                |
               |  Ingestion · Discovery · Recommendation         |
               |  Planning · Prep · Shopping · Canonicalization  |
               +---+-+-------------------+-----------------+-----+
                   | |                   |                 |
     +-------------+ |                   |                 +-------------+
     |               v                   v                               |
+----v-------+  +----+--------------+  +-+-------------------+  +--------v-------+
| Core Domain|  |  Canonicalization |  |  Local AI Gateway   |  | External Web & |
| & Persistence | Unit Conversion   |  | (OpenAI Interface / |  | Discovery APIs |
| (SQLite)   |  | Engine            |  |  Ollama / Mock)     |  | (HTTP Adapters)|
+------------+  +-------------------+  +---------------------+  +----------------+

```

### 4.1 Component Responsibilities

* **UI (Streamlit):** Renders views, handles state changes, displays recommendation explanations, and manages interactive review screens.
* **Recipe Ingestion Service:** Fetches permitted source content, coordinates LLM semantic extraction, executes duplicate/variation checks, and presents review UI payloads.
* **Canonicalization Service:** Maps raw ingredient strings to standard `CanonicalIngredient` records, determines forms/preparations, manages regional alias mappings, and flags unknown ingredients.
* **Unit Conversion Service:** Performs dimensional conversions (mass-to-mass, volume-to-volume) using an explicit density registry for cross-dimensional mappings (e.g., volume-to-mass).
* **Recommendation Engine:** Calculates hybrid ranking scores, enforces hard constraint filters, manages candidate cooldowns, and generates human-readable ranking explanations.
* **Preference Service:** Processes `FeedbackEvent` records, maintains separate feature profiles for *selection likelihood* vs. *predicted enjoyment*, and handles manual weight overrides.
* **Planning Service:** Manages draft and submitted plans, session portion scaling, meal sequence ordering, and plan revisions.
* **Preparation Planner:** Validates task dependencies, groups compatible prep operations, calculates schedule timings, and checks food-safety constraints.
* **Shopping Service:** Aggregates quantities using canonical IDs and unit conversions, groups items by aisle category, and tracks ownership status.
* **Local LLM Gateway:** Handles local model connectivity, schema-constrained output validation, retries, cost/token tracking, and fallback handling. Includes a `MockLLMProvider` for test suites.
* **Persistence Layer:** Manages SQLite database transactions, foreign key enforcement, and schema migrations.

---

## 5. Domain Model & Ingredient Representation

### 5.1 Three-Tier Ingredient Model

To ensure accurate shopping list aggregation and prevent invalid batch-prep task grouping, raw ingredient strings are parsed into three distinct structural components:

```python
from decimal import Decimal
from pydantic import BaseModel

class RecipeIngredient(BaseModel):
    original_text: str
    canonical_ingredient_id: str | None  # e.g., "onion_yellow"
    quantity: Decimal | None
    unit: str | None                     # e.g., "g", "ml", "cup", "clove"
    ingredient_form: str | None          # e.g., "fresh", "frozen", "canned", "dried"
    preparation: str | None              # e.g., "diced", "thinly_sliced", "caramelized"
    is_quantity_estimated: bool = False  # Flagged if derived from vague quantities (e.g., "1 medium onion")
    confidence: float | None             # LLM extraction confidence score

```

1. **Canonical Ingredient (`onion_yellow`):** Identifies the core identity for base matching and alias resolution (e.g., "scallion" $\rightarrow$ `green_onion`).
2. **Ingredient Form (`fresh`, `canned`, `frozen`):** Prevents improper shopping list aggregation (e.g., keeping fresh tomatoes separate from canned crushed tomatoes).
3. **Preparation Specification (`diced`, `caramelized`):** Determines prep-task compatibility. Two recipes sharing `onion_yellow` in `fresh` form can share a chopping prep task *only* if their preparation specifications are compatible.

### 5.2 Deterministic Canonicalization Pipeline

Canonicalization runs in a strict two-stage sequence:

1. **Semantic Parsing (LLM):** The LLM extracts raw text into candidate fields (`canonical_suggestion`, `form`, `preparation`, `quantity`, `unit`).
2. **Deterministic Matching (Python):** The `CanonicalizationService` maps the suggested name against a managed lookup registry and configurable alias dictionary. Unresolved ingredients are added to an `unresolved_ingredients` queue for explicit user verification, preventing the LLM from hallucinating new canonical IDs.

### 5.3 Dimensional Unit Conversion Model

The `UnitConversionService` evaluates conversion requests strictly within physical dimensions:

* **Mass $\leftrightarrow$ Mass:** Exact conversion (e.g., grams, kilograms, ounces, pounds).
* **Volume $\leftrightarrow$ Volume:** Conversion based on standard regional cup definitions (e.g., 1 US Legal Cup = 240 ml).
* **Cross-Dimensional (Volume $\leftrightarrow$ Mass):** Permitted **only** when an explicit density factor exists in the registry for that specific `CanonicalIngredient` (e.g., $1\text{ cup of flour} \approx 120\text{g}$).
* **Uncertain / Count-Based Quantities:** Count units (e.g., "2 cloves of garlic") preserved with estimated mass conversions clearly flagged as `is_quantity_estimated = True`. Incompatible units are listed separately on the shopping list rather than forcibly merged.

---

## 6. Recipe Ingestion & Duplicate Evaluation

### 6.1 Multi-Outcome Duplicate Strategy

Rather than automatically merging records based on a single fuzzy threshold, the ingestion pipeline evaluates candidates using a tiered resolution workflow:

```text
                                [New Recipe Input]
                                        │
                                        ▼
                        {Exact Canonical Source URL Match?}
                          ├── YES ──► [Offer to Open or Update Existing Recipe]
                          └── NO
                                │
                                ▼
                       {Matching External Provider ID?}
                          ├── YES ──► [Offer to Open or Update Existing Recipe]
                          └── NO
                                │
                                ▼
                   {Fuzzy Match: Title + Author/Domain > 85%?}
                          ├── YES
                          │     │
                          │     ▼
                          │   {High Similarity in Ingredients & Steps?}
                          │     ├── YES ──► [Flag as Likely Duplicate: Prompt User]
                          │     └── NO  ──► [Flag as Recipe Variation: Link as Related]
                          │
                          └── NO ──► [Treat as New Recipe Record]

```

---

## 7. Preference Engine & Dual-Target Recommendation Model

### 7.1 Separation of Selection Likelihood vs. Predicted Enjoyment

To prevent convenience-driven decisions (e.g., picking a quick 15-minute meal on a busy weeknight) from distorting long-term taste preferences, the system maintains two separate prediction vectors:

1. **Selection Likelihood ($S_{select}$):** Predicts how likely the user is to accept the recipe for a specific week based on convenience, preparation time, ingredient overlap with other accepted recipes, and current weekly constraints.
2. **Predicted Enjoyment ($E_{taste}$):** Predicts how much the user will enjoy eating the dish based on historical ratings, spice preferences, flavor profiles, and cuisine affinity.

### 7.2 Feature-Based Scoring Formulation

Candidate score $R(c)$ for a given discovery session is calculated deterministically in Python:

$$R(c) = w_e \cdot E_{\text{taste}}(c) + w_s \cdot S_{\text{select}}(c) + w_d \cdot D_{\text{dir}}(c) + w_v \cdot V_{\text{novelty}}(c) - P_{\text{cooldown}}(c)$$

Where:

* $E_{\text{taste}}(c)$: Weighted sum of canonical flavor, spice, cuisine, and ingredient ratings.
* $S_{\text{select}}(c)$: Fit with time limits, active prep capacity, and shared prep opportunities.
* $D_{\text{dir}}(c)$: Alignment with transient user direction (e.g., "Focus on Korean dishes").
* $V_{\text{novelty}}(c)$: Diversity score preventing repetitive suggestions.
* $P_{\text{cooldown}}(c)$: Heavy penalty applied to recipes suggested or cooked within a configurable cooldown window.

### 7.3 Feedback Event Logging

All user interactions generate immutable `FeedbackEvent` records:

```python
class FeedbackEvent(BaseModel):
    event_id: str
    recipe_id: str
    event_type: str  # "EXPLICIT_RATING", "THUMBS_UP", "ACCEPTED_FOR_WEEK", "SKIPPED", "DISCARDED"
    rating_value: float | None  # e.g., 1.0 to 5.0 for explicit ratings; +1/-1 for thumbs
    context_tags: list[str]     # e.g., ["busy_week", "one_off_request"]
    timestamp_utc: str

```

* **Explicit High/Low Ratings:** Strongly impact $E_{\text{taste}}(c)$.
* **Acceptances / Rejections:** Moderate impact on $S_{\text{select}}(c)$, with minimal impact on $E_{\text{taste}}(c)$ unless accompanied by an explicit rating or contextual feedback.
* **Discards:** Reduces recommendation frequency for similar recipe attributes.

---

## 8. Interactive Weekly Planning & Preparation Optimization

### 8.1 Plan & Candidate State Lifecycle

```text
[Candidate] ──► Accept ──────► [Accepted For Week] ──► Submit Week ──► [Submitted Plan] ──► Cook ──► [Cooked Session]
     │               │                                                        │
     ├── Save Only ──┼───────► [Saved Library Recipe]                         └── Reopen Edit ──► [Draft Plan Revision]
     ├── Skip        └───► [Skipped (No State Change)]
     └── Discard     ───────► [Discarded (Logged Feedback Event)]

```

* **Candidate:** Transient discovery item.
* **Accepted for Week:** Linked to current draft plan; automatically stored in saved recipe library.
* **Saved for Later:** Added to library; excluded from current week's shopping list and plan.
* **Discarded:** Removed from view; updates candidate filtering to avoid similar items.
* **Plan Revisions:** Reopening a submitted plan creates a new revision version while retaining historical plan logs.

### 8.2 Batch Preparation & Task Dependency Pipeline

The preparation service separates shared ingredient purchasing from shared prep execution:

1. **Task Extraction:** Recipe instructions are parsed into discrete `PrepTask` records (e.g., chop, marinate, simmer, roast).
2. **Synergy Identification (Python):** Tasks sharing identical `canonical_ingredient_id`, compatible `ingredient_form`, and compatible `preparation` specifications are evaluated for batch prep.
3. **Safety & Storage Validation:** Python rules enforce shelf-life constraints (e.g., diced raw onions can be prepped 48 hours ahead; fresh seafood marinades are limited to short windows).
4. **Schedule Generation:** Generates a structured Weekend Prep Guide displaying active time, passive time, storage container requirements, and execution steps.

```python
class PrepTask(BaseModel):
    task_id: str
    recipe_ids: list[str]
    canonical_ingredient_id: str
    operation: str               # "CHOP", "MARINATE", "ROAST"
    active_minutes: int
    can_prep_ahead: bool
    max_ahead_hours: int         # Safety threshold
    storage_method: str          # "airtight_fridge", "room_temp"
    dependent_task_ids: list[str]

```

### 8.3 Perishability-Aware Meal Sequencing

Upon plan submission, the system orders meals based on ingredient shelf-life and weekend shopping patterns:

* **Early Session (Days 1–2):** Meals containing highly perishable ingredients (e.g., fresh fish, raw poultry, delicate leafy greens).
* **Late Session (Days 3–4+):** Meals utilizing hardy produce (e.g., root vegetables, cabbage), cured items, or pantry staples.

---

## 9. Data Schema & Persistence Model

The persistence layer uses local SQLite with foreign key enforcement and transactional updates.

```
+-------------------+        +------------------------+        +---------------------+
|      RECIPE       |        |   RECIPE_INGREDIENT    |        | CANONICAL_INGREDIENT|
+-------------------+        +------------------------+        +---------------------+
| id (PK)           |<-------| recipe_id (FK)         |   +--->| id (PK)             |
| title             |        | canonical_id (FK) -----|---+    | default_slug        |
| source_url        |        | original_text          |        | category            |
| prep_minutes      |        | quantity, unit         |        | storage_life_days   |
| cook_minutes      |        | form, preparation      |        +---------------------+
| perishability_score|       +------------------------+
+---------+---------+
          |                  +------------------------+        +---------------------+
          |                  |    COOKING_SESSION     |        |    WEEKLY_PLAN      |
          |                  +------------------------+        +---------------------+
          +----------------->| recipe_id (FK)         |   +--->| id (PK)             |
                             | plan_id (FK) ----------|---+    | week_start_date     |
                             | sequence_order         |        | status, revision    |
                             +------------------------+        +---------------------+

```

---

## 10. Self-Hosted LLM Provider Architecture & Fallbacks

### 10.1 Generic OpenAI-Compatible Local Adapter Interface

The LLM integration is abstracted via a generic provider interface, decoupling the application from specific local runtimes.

```python
from typing import Protocol, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LocalLLMProvider(Protocol):
    def generate_structured(
        self, 
        prompt: str, 
        response_schema: Type[T], 
        system_instruction: str | None = None,
        temperature: float = 0.2
    ) -> T:
        """Executes local LLM inference returning guaranteed validated Pydantic models."""
        ...

```

* **`OpenAILocalProvider`:** Connects to any local server exposing OpenAI-compatible endpoints (Ollama, vLLM, LM Studio, LocalAI).
* **`MockLLMProvider`:** Returns recorded JSON fixtures and simulates error modes (timeouts, malformed outputs) for offline automated testing.

### 10.2 Structured Output & Semantic Validation

1. **Schema Enforcement:** System prompts request JSON adhering to a target Pydantic schema.
2. **Pydantic Validation:** Raw JSON responses are validated directly against domain models.
3. **Bounded Retries & Fallback:** If JSON validation fails, the provider attempts up to two retries with explicit error feedback in the retry prompt. If validation continues to fail, the operation degrades gracefully to manual user input or rule-based processing.

---

## 11. Concrete Acceptance Test Suite

To verify system behavior during development, the implementation must pass these core acceptance tests:

1. **Offline Core Operation:** Disable all network interfaces. Verify that searching saved recipes, creating a weekly plan from local recipes, generating a shopping list, scaling portion quantities, and logging feedback operate without errors.
2. **Local AI Unavailable Fallback:** Stop the local LLM inference server. Verify that the UI displays a clear "Local AI Offline" indicator, allows manual recipe entry, and executes deterministic meal planning without crashing.
3. **Canonicalization & Aliasing:** Ingest a recipe with "2 green onions, chopped" and another with "1 cup scallions, sliced". Verify both map to canonical ID `green_onion` while retaining original preparation text.
4. **Ingredient Form Segregation:** Ingest Recipe A ("400g canned crushed tomatoes") and Recipe B ("2 fresh tomatoes, diced"). Verify the aggregated shopping list displays canned and fresh tomatoes as separate line items.
5. **Unit Conversion Dimensional Boundaries:** Request conversion of "200g flour" to cups. Verify conversion succeeds using the flour density registry factor ($1\text{ cup} \approx 120\text{g}$). Request conversion of "200g chicken breast" to cups; verify system flags units as incompatible and keeps them separate.
6. **Perishability Sequencing:** Create a plan containing a fresh cod recipe and a squash/pantry staple recipe. Verify the planner automatically assigns the fresh cod recipe to Session 1 (earliest days).
7. **Duplicate vs. Variation Resolution:** Ingest a recipe matching an existing title and domain with identical steps; verify system prompts for duplicate review. Ingest a recipe with the same title but significantly different ingredients; verify system flags it as a "Recipe Variation" and offers to link records.
8. **Preference Learning Signal Separation:** Accept a quick 15-minute meal due to time constraints but give it a 2/5 explicit rating after cooking. Verify that $S_{\text{select}}$ for quick meals increases while $E_{\text{taste}}$ for that specific cuisine/flavor profile decreases.