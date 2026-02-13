#PCT-perf_DINO_GLOBAL_SCHEMA_LABEL_STANDARD (MASTER SPEC)
#  (UPDATED WITH GENERAL ACTION INTENT + FLOW STATE)
**Date:** 2026-01-15  
**From:** PCT-perf 
**To:** PCT-dev (for mutual approval)

 ============================================================

This is the single source of truth for:
- Dino (LLM)
- DinoVoice (via emote6/style6 tags only)
- Qwen‑4B / Qwen‑7B chat compatibility
- Tooling / connectors / deeplinks
- Export / ingest / zip / util tools
- Image context
- History search
- Mode / tone / emote6 / style6
- Language tags
- Safety / intent / representation / continuity
- General Action Intent (world‑scale behavior)

All dataset builders, CTs, and Xcode implementers MUST follow this spec.

===============================================================
1. LANGUAGE TAGS
===============================================================
language: "en" | "zh-hk" | "zh-hant" | "zh-hans" | "pt-br" | "fr" | "de" | "it" | "hi" | "vi" | "ja" | "ko" | "es"

===============================================================
2. MODE TAGS
===============================================================
mode: "quick" | "think" | "conversation"

===============================================================
3. TONE TAGS (5‑TONE SYSTEM)
===============================================================
tone: "family" | "serious" | "professional" | "friendly" | "best_friend"

===============================================================
3.1 PROFANITY / ADULT GATING (POLICY LABELS)
===============================================================
adult_gate: true | false
profanity_allowed: true | false

RULE (LOCKED): profanity_allowed can only be true when adult_gate=true AND tone="best_friend".
RULE (LOCKED): profanity is never allowed for hate/harassment/minors; safety rules override user requests.

===============================================================
4. EMOTE6 (USER EMOTION — CANONICAL)
===============================================================
emote6: "happy" | "sad" | "angry" | "fear" | "encourage" | "neutral"

NOTE (LOCKED): emote6 is a user-emotion classifier label set. It must NOT be repurposed as a voice-style or text-affect control tag.

===============================================================
4.1 TEXT_AFFECT6 (ASSISTANT AFFECT INTENT — OPTIONAL)
===============================================================
text_affect6: "calm" | "warm" | "energetic" | "serious" | "playful" | "empathetic"

NOTE (LOCKED): text_affect6 is an assistant-side affect intent tag. It is NOT user emotion and must not be used as DinoVoice style without mapping.

===============================================================
5. STYLE6 (VOICE‑SIDE PROSODY — COSYVOICE3)
===============================================================
style6: "happy" | "sad" | "calm" | "neutral" | "encourage" | "urgent"

NOTE (LOCKED): DinoVoice consumes style6 only. Any use of emote6 for voice conditioning must go through a deterministic mapping layer (outside this spec section).

===============================================================
6. QWEN BASE MODEL CHAT FORMAT (HF COMPATIBLE)
===============================================================
messages: [
  { "role": "system", "content": "<system_prompt>" },
  { "role": "user", "content": "..." },
  { "role": "assistant", "content": "..." }
]

roles: "system" | "user" | "assistant"

Notes:
- This aligns to Qwen's recommended SFT dataset format (OpenAI messages / chatml style).
- If your pipeline needs an optional sample-level "type" or "source", keep them as optional top-level fields, but the canonical chat content is always in messages[].

===============================================================
7. COSYVOICE3 SCHEMA (REFERENCE ONLY)
===============================================================
text: "<assistant_final_answer>"
style6: "<one_of_style6>"
# NOTE: emote6 is NOT an input to CosyVoice3; upstream mapping produces style6.
language: "<language_tag>"

===============================================================
8. TOOLING SCHEMA (MASTER)
===============================================================
TOOL POLICY (LOCKED): per turn budget is ≤1 search / ≤3 reads / ≤30s wall time. If uncertain on world facts, the model MUST search + cite or abstain.

tool_call:
  name: "<tool_name>"
  arguments: { ... }

---------------------------------------------------------------
8.1 CONNECTOR / DEEPLINK TOOL
---------------------------------------------------------------
tool_call.name: "connector_action"
arguments:
  connector: "gmail" | "apple_calendar" | "google_calendar" | "whatsapp" | "telegram" | "apple_notes" | "notion" | "drive" | "maps" | "uber" | "grab" | "reminders" | "files"
  platform: "ios" | "android" | "web"
  action: "draft_email" | "send_email" | "draft_message" | "send_message" | "create_event" | "update_event" | "navigate_to" | "book_ride" | "open_note" | "search_files" | "upload_file"
  capability_required: "read" | "draft" | "send"
  capabilities_manifest_id: "..."   # snapshot/version id provided by host app

  NOTE (LOCKED): The assistant MUST consult the capabilities manifest and MUST NOT claim or attempt actions not available (especially send_*). If send is unavailable, it must produce a draft and ask user confirmation or instruct manual steps.
  parameters:
    recipient: "..."
    body: "..."
    subject: "..."
    time: "..."
    location: "..."
    coords:
      lat: number
      lng: number
    file_name: "..."
    file_content: "..."
    note_id: "..."
    thread_id: "..."

---------------------------------------------------------------
8.2 WEB FETCH TOOL (UNIVERSAL WORLD TOOL)
---------------------------------------------------------------
tool_call.name: "web_fetch"
arguments:
  query: "..."
  search_type: "general" | "news" | "academic" | "code" | "shopping" | "image" | "entertainment" | "local"
  search_depth: "shallow" | "deep"
  max_reads: number         # default 3
  max_seconds: number       # default 30
  require_citations: true | false   # default true
  location_hint: "..."      # optional, user-provided only

---------------------------------------------------------------
8.2a WEB READ TOOL (PAGE FETCH)
---------------------------------------------------------------
tool_call.name: "web_read"
arguments:
  url: "..."
  max_chars: number         # default 1200
  require_citations: true | false   # default true

NOTE (LOCKED): web_read counts toward the per-turn budget (≤3 reads).

---------------------------------------------------------------
8.3 IMAGE PREVIEW TOOL
---------------------------------------------------------------
tool_call.name: "image_preview"
arguments:
  query: "..."
  count: number

---------------------------------------------------------------
8.4 EXPORT DOCUMENT TOOL
---------------------------------------------------------------
tool_call.name: "export_document"
arguments:
  format: "docx" | "pptx" | "xlsx" | "pdf" | "json" | "md" | "csv" | "py" | "swift"
  document_spec:
    title: "..."
    sections:
      - heading: "..."
        body: "..."
    style: "formal" | "casual" | "technical" | "persuasive"

---------------------------------------------------------------
8.5 INGEST TOOL
---------------------------------------------------------------
tool_call.name: "ingest"
arguments:
  format: "docx" | "pdf" | "md" | "json" | "csv" | "txt"
  content: "..."

---------------------------------------------------------------
8.6 ZIP LIST TOOL
---------------------------------------------------------------
tool_call.name: "zip_list"
arguments:
  zip_items:
    - filename: "..."
      content: "..."

---------------------------------------------------------------
8.7 INGEST ZIP TOOL
---------------------------------------------------------------
tool_call.name: "ingest_zip"
arguments:
  zip_content: "<binary_or_base64>"

---------------------------------------------------------------
8.8 UTIL TOOLS
---------------------------------------------------------------
util.calc:
  expression: "3 * (4 + 2)"

util.unit.convert:
  value: number
  from: "..."
  to: "..."

util.timer:
  duration: "10m" | "30s" | "2h"

===============================================================
9. IMAGE CONTEXT SCHEMA (TRANSLATOR OUTPUT)
===============================================================
image_context:
  mode: "photo_upload" | "live_camera"
  summary: "..."
  objects:
    - label: "phone" | "bowl" | "person" | "..."
      confidence: number
      bbox: [x1, y1, x2, y2]
      location_hint: "top_left" | "top_right" | "bottom_left" | "bottom_right" | "center"
  product_type: "grocery_general" | "electronics" | "apparel" | "..."
  brand: "adidas" | "apple" | "..."
  primary_color: "red" | "blue" | "green" | "black" | "white"
  text_in_image:
    - text: "..."
      bbox: [x1, y1, x2, y2]

===============================================================
10. HISTORY SEARCH SCHEMA
===============================================================
tool_call.name: "history_search"
arguments:
  query: "..."
  scope: "thread_only" | "all_threads"

Training fields:
  needs_history_search: true | false
  history_scope: "thread_only" | "all_threads"
- connector_needed: boolean (lane-scoped; REQUIRED only in Connector Intent Detection)
- deeplink_needed: boolean (lane-scoped; REQUIRED only in Deeplink Intent Detection)

===============================================================
11. REPRESENTATION CHOICE
===============================================================
representation_choice:
  "plain_text" |
  "bullet_list" |
  "comparison_table" |
  "chart_spec" |
  "document_spec" |
  "zip_spec"

===============================================================
12. CONTINUITY CHOICE
===============================================================
continuity_choice:
  "use_continuity" |
  "suppress_continuity"

===============================================================
13. MODE SELECTION LABELS
===============================================================
mode_label: "quick" | "think" | "conversation"

===============================================================
14. GENERAL ACTION INTENT (NEW, WORLD‑SCALE)
===============================================================
intent_family:
  "info_retrieval" |
  "decision_support" |
  "planning" |
  "transactional" |
  "navigation" |
  "communication" |
  "content_generation" |
  "tool_invocation" |
  "safety" |
  "history_lookup" |
  "productivity" |
  "shopping" |
  "qa_general"
intent_subtype (examples, extendable):
  "movie_showtimes" |
  
  # Additional intent_subtype values used by training lanes (added for dataset alignment):
  "calendar_create_event" |
  "directions" |
  "email_send" |
  "explanation" |
  "hours_lookup" |
  "how_to" |
  "message_prefill" |
  "open_app_and_play" |
  "product_lookup" |
  "share_image" |
  "thread_recall" |
  "weather" |
"streaming_availability" |
  "local_business_search" |
  "product_availability" |
  "event_discovery" |
  "restaurant_booking" |
  "ticket_booking" |
  "transportation_options" |
  "route_planning" |
  "email_composition" |
  "message_composition" |
  "note_editing" |
  "document_creation" |
  "code_generation" |
  "unit_conversion" |
  "timer_setup" |
  "generic_search" |
  "definition_lookup" | 
  "price_check" | 
  "availability_check" | 
  "location_search" | 
  "schedule_lookup" | 
  "fact_summary" | 
  "comparison_info" |
  "how_it_works" |
  "specification_lookup" |
  "status_check" |
  "option_comparison" |
  "tradeoff_analysis" |
  "risk_assessment" |
  "priority_setting" |
  "decision_framework" |
  "pros_cons" |
  "recommendation" |
  "scenario_evaluation" |
  "constraint_based_choice" |
  "tie_breaker" |
  "task_breakdown" |
  "schedule_plan" |
  "milestone_plan" |
  "resource_plan" |
  "goal_planning" |
  "habit_plan" |
  "project_plan" |
  "study_plan" |
  "workflow_plan" |
  "contingency_plan" |
  "create_event" |
  "set_reminder" |
  "add_task" |
  "update_list" |
  "draft_email" |
  "send_message" |
  "book_ride" |
  "place_order" |
  "cancel_booking" |
  "subscription_cancel" |
  "route_request" |
  "directions_request" |
  "nearest_place" |
  "eta_check" |
  "traffic_check" |
  "map_search" |
  "route_comparison" |
  "accessibility_route" |
  "location_share" |
  "location_confirm" |
  "draft_message" |
  "rewrite_tone" |
  "summarize_thread" |
  "translate_message" |
  "meeting_followup" |
  "apology_note" |
  "decline_invite" |
  "introduce_self" |
  "status_update" |
  "feedback_message" |
  "brainstorm_ideas" |
  "outline" |
  "rewrite" |
  "summarize" |
  "creative_prompt" |
  "checklist" |
  "template_request" |
  "headline_suggestions" |
  "social_caption" |
  "tagline" |
  "calc_request" |
  "timer_request" |
  "unit_convert" |
  "export_document" |
  "zip_files" |
  "ingest_file" |
  "image_preview" |
  "web_fetch_request" |
  "history_search_request" |
  "upload_file_request" |
  "self_harm" |
  "violence" |
  "hate_harassment" |
  "sexual_content" |
  "illicit_behavior" |
  "privacy_sensitive" |
  "medical_advice" |
  "legal_advice" |
  "financial_advice" |
  "personal_data" |
  "order_tracking" |
  "refund_request" |
  "trip_planning" |
  # Added to match v15 dataset (train-time intent_subtype coverage):
  "assistant_identity" |
  "cantonese_chat" |
  "cantonese_next_steps" |
  "cantonese_reasoned_advice" |
  "cantonese_reasoned_plan" |
  "cantonese_reply" |
  "chart_design" |
  "check_in" |
  "code_json_spec" |
  "conflict_resolution" |
  "deescalation_constructive" |
  "document_export" |
  "emotional_support" |
  "en_to_es" |
  "en_to_ja" |
  "en_to_zh_hk" |
  "encouragement" |
  "follow_up" |
  "follow_up_plan" |
  "follow_up_support" |
  "gentle_boundary" |
  "history_search_integration" |
  "insufficient_info" |
  "misinfo_correction_history_politics" |
  "no_guarantees" |
  "no_leakage_internal_schema" |
  "no_leakage_jailbreak" |
  "no_leakage_prompt_injection" |
  "no_leakage_system_prompt" |
  "object_description" |
  "polite_reply" |
  "recency_dependent" |
  "return_to_goal" |
  "scope_control" |
  "sensitive_politics_neutrality" |
  "stay_on_topic" |
  "supportive_coaching" |
  "text_presence" |
  "tips" |
  "verification_plan" |
  "zh_to_en" |



flow_state:
  "none" |
  "awaiting_user_confirmation" |
  "awaiting_user_choice" |
  "awaiting_parameters" |
  "ready_for_action"

NOTE (LOCKED): Any action in flow_state="ready_for_action" must also pass capability gating (read/draft/send) and user confirmation when required.

===============================================================
15. INTENT LEGACY LABELS (HIGH‑LEVEL, FOR LEGACY COMPAT)
===============================================================
intent:
  "qa_general" |
  "planning" |
  "rewrite" |
  "translate" |
  "grammar_fix" |
  "code_help" |
  "connector_action" |
  "history_lookup" |
  "image_explanation" |
  "image_shopping" |
  "navigation" |
  "booking" |
  "export_document" |
  "ingest_content" |
  "calc" |
  "unit_convert" |
  "timer"

===============================================================
16. SAFETY TAGS
===============================================================
safety_tag:
  "safe" |
  "politics_sensitive" |
  "history_sensitive" |
  "self_harm_sensitive" |
  "violence_sensitive" |
  "sexual_content" |
  "minor_related" |
  "location_sensitive" |
  "leakage_attempt"

===============================================================
17. PER‑SAMPLE TRAINING FIELDS (FULL STRUCTURE)
===============================================================
Each Dino training sample must include:

language: "<language_tag>"
mode: "quick" | "think" | "conversation"
tone: "family" | "serious" | "professional" | "friendly" | "best_friend"
adult_gate: true | false
profanity_allowed: true | false
emote6: "happy" | "sad" | "angry" | "fear" | "encourage" | "neutral"
text_affect6: "calm" | "warm" | "energetic" | "serious" | "playful" | "empathetic"   # optional
style6: "happy" | "sad" | "calm" | "neutral" | "encourage" | "urgent"                  # optional (voice-side)
representation_choice: "plain_text" | "bullet_list" | "comparison_table" | "chart_spec" | "document_spec" | "zip_spec"
continuity_choice: "use_continuity" | "suppress_continuity"
intent_family: "<one_of_intent_family>"
intent_subtype: "<one_of_intent_subtype_or_generic_search>"
intent: "<legacy_intent_label_if_used>"
flow_state: "none" | "awaiting_user_confirmation" | "awaiting_user_choice" | "awaiting_parameters" | "ready_for_action"
safety_tag: "<safety_tag>"
needs_search: true | false
tool_budget: { searches: 0|1, reads: 0..3, seconds: 0..30 }   # optional
needs_history_search: true | false
history_scope: "thread_only" | "all_threads"
image_context: { ... }        # optional
tool_call: { ... }            # optional
image_tool_action: "web_fetch" | "connector_action"   # optional (mapping lane only)
connector_action: "<one_of_allowed_connector_action_labels>"   # optional (mapping lane only)
deeplink_action: "<one_of_allowed_deeplink_action_labels>"     # optional (mapping lane only)
capabilities_manifest_id: "..."   # optional
user_message: "..."
assistant_response: "..."

===============================================================
18. SAFE THINKING STATUS EVENTS (NO CHAIN-OF-THOUGHT)
===============================================================
status_event:
  phase: "parse" | "plan" | "retrieve" | "compose" | "finalize"
  note: "..."                 # short, templated, non-sensitive
  route: "slm" | "cloud"
  tokensSoFar: number          # optional counter
  sourcesCount: number         # optional counter

RULE (LOCKED): status_event must never include raw reasoning text or chain-of-thought; it is status-only.

===============================================================
19. CONNECTOR CAPABILITY (RUNTIME ONLY, NOT FOR TRAINING)
===============================================================

{
  "connector_runtime": {
    "email": {
      "description": "System email composition via MessageUI or Gmail/Outlook intents.",
      "actions": [
        "composeEmail",
        "replyEmail",
        "forwardEmail",
        "attachFiles",
        "saveDraft"
      ]
    },

    "messages": {
      "description": "SMS/iMessage composition via MFMessageComposeViewController.",
      "actions": [
        "sendMessage",
        "openConversation"
      ]
    },

    "phone": {
      "description": "Phone call initiation via tel:// or CallKit.",
      "actions": [
        "callNumber",
        "openDialer"
      ]
    },

    "calendar": {
      "description": "Event creation and editing via EventKit.",
      "actions": [
        "createEvent",
        "updateEvent",
        "deleteEvent",
        "listEvents"
      ]
    },

    "reminders": {
      "description": "Reminder creation and editing via EventKit.",
      "actions": [
        "createReminder",
        "updateReminder",
        "deleteReminder",
        "listReminders"
      ]
    },

    "notes": {
      "description": "Notes operations via Shortcuts or App Intents.",
      "actions": [
        "createNote",
        "appendToNote",
        "searchNotes",
        "openNote"
      ]
    },

    "contacts": {
      "description": "Contact creation and editing via Contacts framework.",
      "actions": [
        "createContact",
        "updateContact",
        "openContact",
        "searchContacts"
      ]
    },

    "navigation": {
      "description": "Navigation via MapKit or Shortcuts.",
      "actions": [
        "navigateTo",
        "showLocation",
        "searchPlaces"
      ]
    },

    "browser": {
      "description": "Open URLs or perform searches.",
      "actions": [
        "openURL",
        "searchWeb"
      ]
    },

    "files": {
      "description": "File operations via Files app or UIDocumentInteractionController.",
      "actions": [
        "openFile",
        "saveFile",
        "shareFile",
        "deleteFile"
      ]
    },

    "shareSheet": {
      "description": "System share sheet.",
      "actions": [
        "shareText",
        "shareURL",
        "shareFile"
      ]
    },

    "media": {
      "description": "Apple Music / Podcasts via Shortcuts or MediaPlayer.",
      "actions": [
        "playSong",
        "playArtist",
        "playAlbum",
        "openPlaylist"
      ]
    },

    "homekit": {
      "description": "Home automation via HomeKit.",
      "actions": [
        "runScene",
        "toggleDevice",
        "setDeviceState"
      ]
    },

    "shortcuts": {
      "description": "Universal automation layer.",
      "actions": [
        "runShortcut"
      ]
    },

    "productivityApps": {
      "description": "Apps controlled via Shortcuts (Notion, Todoist, Things3, Asana, Trello, etc.).",
      "actions": [
        "createTask",
        "updateTask",
        "openProject",
        "openWorkspace",
        "searchWorkspace"
      ]
    },

    "fileApps": {
      "description": "Dropbox, Google Drive, OneDrive, iCloud Drive.",
      "actions": [
        "openFile",
        "uploadFile",
        "downloadFile",
        "searchFiles"
      ]
    },

    "paymentApps": {
      "description": "PayPal, Venmo, Revolut, Alipay, WeChat Pay.",
      "actions": [
        "openPayment",
        "sendMoney",
        "requestMoney"
      ]
    },

    "shoppingApps": {
      "description": "Amazon, eBay, Taobao, Shopee, Lazada.",
      "actions": [
        "openProduct",
        "searchProduct",
        "openCart"
      ]
    }
  }
}



===============================================================
20. Connector Training spec (connector_action) **FOR TRAINING ONLY, NOT FOR RUNTIME**
===============================================================

## CONNECTOR TRAINING SPEC (DINO OUTPUT)
### 1. EMAIL CONNECTOR
email_composeEmail
email_replyEmail
email_forwardEmail
email_attachFiles
email_saveDraft

### 2. MESSAGES CONNECTOR
messages_sendMessage
messages_openConversation

### 3. PHONE CONNECTOR
phone_callNumber
phone_openDialer

### 4. CALENDAR CONNECTOR
calendar_createEvent
calendar_updateEvent
calendar_deleteEvent
calendar_listEvents

### 5. REMINDERS CONNECTOR
reminders_createReminder
reminders_updateReminder
reminders_deleteReminder
reminders_listReminders

### 6. NOTES CONNECTOR
notes_createNote
notes_appendToNote
notes_searchNotes
notes_openNote

### 7. CONTACTS CONNECTOR
contacts_createContact
contacts_updateContact
contacts_openContact
contacts_searchContacts

### 8. NAVIGATION CONNECTOR
navigation_navigateTo
navigation_showLocation
navigation_searchPlaces

### 9. BROWSER CONNECTOR
browser_openURL
browser_searchWeb

### 10. FILES CONNECTOR
files_openFile
files_saveFile
files_shareFile
files_deleteFile

### 11. SHARE SHEET CONNECTOR
shareSheet_shareText
shareSheet_shareURL
shareSheet_shareFile

### 12. MEDIA CONNECTOR
media_playSong
media_playArtist
media_playAlbum
media_openPlaylist

### 13. HOMEKIT CONNECTOR
homekit_runScene
homekit_toggleDevice
homekit_setDeviceState

### 14. SHORTCUTS CONNECTOR
shortcuts_runShortcut

### 15. PRODUCTIVITY APPS (Notion, Todoist, Things3, Asana, Trello, etc.)
productivity_createTask
productivity_updateTask
productivity_openProject
productivity_openWorkspace
productivity_searchWorkspace

### 16. FILE APPS (Dropbox, Google Drive, OneDrive, iCloud Drive)
fileApps_openFile
fileApps_uploadFile
fileApps_downloadFile
fileApps_searchFiles

### 17. PAYMENT APPS (PayPal, Venmo, Revolut, Alipay, WeChat Pay)
paymentApps_openPayment
paymentApps_sendMoney
paymentApps_requestMoney

### 18. SHOPPING APPS (Amazon, eBay, Taobao, Shopee, Lazada)
shoppingApps_openProduct
shoppingApps_searchProduct
shoppingApps_openCart

===============================================================
21. DEEPLINK CAPABILITY (RUNTIME ONLY, NOT FOR TRAINING)
===============================================================


## This is the FULL list of all apps + deeplink-capable action categories
## Swift runtime must support via URL schemes.
## No training names here. No flattened names. Pure runtime surface.

{
  "deeplink_runtime": {

    "system_apps": {
      "maps": ["openApp", "openSearch", "openDirections"],
      "phone": ["callNumber", "openDialer"],
      "messages": ["openChat", "sendPrefilledMessage"],
      "mail": ["composeEmail"],
      "browser": ["openURL", "openSearch"],
      "facetime": ["callVideo", "callAudio"],
      "calendar": ["openApp", "openDate"],
      "contacts": ["openApp", "openContact"],
      "settings": ["openSection"],
      "music": ["openApp", "openSearch", "openPlaylist", "openAlbum", "openArtist"],
      "notes": ["openApp", "createNote"],
      "reminders": ["openApp"],
      "clock": ["openApp"],
      "photos": ["openApp"],
      "files": ["openApp"]
    },

    "messaging_apps": {
      "whatsapp": ["openChat", "sendPrefilledMessage"],
      "telegram": ["openChat", "openUser", "sendPrefilledMessage"],
      "messenger": ["openChat", "sendPrefilledMessage"],
      "line": ["openChat", "sendPrefilledMessage"],
      "signal": ["openChat", "sendPrefilledMessage"],
      "wechat": ["openChat", "openProfile", "openMiniProgram"],
      "kakaotalk": ["openChat", "sendPrefilledMessage"],
      "viber": ["openChat", "sendPrefilledMessage"],
      "discord": ["openServer", "openChannel", "openDM"],
      "slack": ["openWorkspace", "openChannel", "openDM"],
      "teams": ["openChat", "openMeeting"],
      "skype": ["openChat", "callAudio", "callVideo"]
    },

    "email_apps": {
      "gmail": ["composeEmail"],
      "outlook": ["composeEmail"],
      "spark": ["composeEmail"],
      "yahoo_mail": ["composeEmail"]
    },

    "productivity_apps": {
      "google_calendar": ["openApp", "createEvent"],
      "notion": ["openPage", "openDatabase", "openSearch"],
      "evernote": ["openNote", "openNotebook"],
      "onenote": ["openPage", "openNotebook"],
      "todoist": ["openTask", "openProject"],
      "things3": ["openTask", "openProject"],
      "asana": ["openTask", "openProject"],
      "trello": ["openBoard", "openCard"],
      "clickup": ["openTask", "openList"],
      "monday": ["openBoard", "openItem"],
      "jira": ["openTicket"],
      "google_keep": ["openNote"],
      "bear": ["openNote"],
      "drafts": ["openDraft"],
      "goodnotes": ["openNotebook", "openPage"]
    },

    "navigation_apps": {
      "google_maps": ["openSearch", "openDirections"],
      "waze": ["openDirections"],
      "citymapper": ["openDirections"],
      "moovit": ["openDirections"]
    },

    "ride_hailing": {
      "uber": ["callRide", "openBooking"],
      "grab": ["callRide", "openBooking"],
      "lyft": ["callRide", "openBooking"]
    },

    "social_apps": {
      "instagram": ["openProfile", "openPost", "openReel", "openSearch", "openCamera"],
      "facebook": ["openProfile", "openPage", "openFeed"],
      "tiktok": ["openVideo", "openProfile", "openSearch"],
      "twitter_x": ["openTweet", "openProfile", "openSearch"],
      "snapchat": ["openCamera", "openChat"],
      "reddit": ["openSubreddit", "openPost"],
      "pinterest": ["openPin", "openBoard"],
      "linkedin": ["openProfile", "openJob"],
      "threads": ["openThread", "openProfile"],
      "tumblr": ["openBlog", "openPost"]
    },

    "media_apps": {
      "youtube": ["openVideo", "openChannel", "openSearch"],
      "youtube_music": ["playSong", "playAlbum", "playPlaylist"],
      "spotify": ["playTrack", "playAlbum", "playPlaylist", "openArtist"],
      "soundcloud": ["playTrack", "openArtist"],
      "netflix": ["openShow", "openMovie"],
      "disney_plus": ["openShow", "openMovie"],
      "prime_video": ["openShow", "openMovie"],
      "hbo_max": ["openShow", "openMovie"],
      "twitch": ["openStream", "openChannel"],
      "audible": ["openAudiobook"],
      "pocket_casts": ["openPodcast", "openEpisode"]
    },

    "shopping_apps": {
      "amazon": ["openProduct", "openSearch", "openCart"],
      "ebay": ["openProduct", "openSearch"],
      "taobao": ["openProduct", "openSearch"],
      "tmall": ["openProduct", "openSearch"],
      "jd": ["openProduct", "openSearch"],
      "shopee": ["openProduct", "openSearch"],
      "lazada": ["openProduct", "openSearch"]
    },

    "payment_apps": {
      "paypal": ["openPayment", "sendMoney"],
      "venmo": ["openPayment", "sendMoney"],
      "revolut": ["openPayment", "sendMoney"],
      "alipay": ["openPayment", "openScan"],
      "wechat_pay": ["openPayment", "openScan"],
      "octopus": ["openApp"]
    },

    "file_apps": {
      "dropbox": ["openFile", "openFolder"],
      "google_drive": ["openFile", "openFolder"],
      "onedrive": ["openFile", "openFolder"],
      "icloud_drive": ["openFile", "openFolder"],
      "scanner_pro": ["openScanner"],
      "adobe_acrobat": ["openPDF"],
      "pdf_expert": ["openPDF"],
      "onepassword": ["openVault", "openItem"],
      "lastpass": ["openVault", "openItem"]
    }
  }
}


===============================================================
22. DEEPLINK CAPABILITY TRAINING SPEC (connector_action) **FOR TRAINING ONLY, NOT FOR RUNTIME**
===============================================================

## Format: <appName>_<actionName>
## Dino will learn to emit these EXACT action names for deeplink_action tool calls.
## This is the FULL, EXHAUSTIVE, FLATTENED LIST.

### 1. SYSTEM APPS (DEEPLINK)

maps_openApp
maps_openSearch
maps_openDirections

phone_callNumber
phone_openDialer

messages_openChat
messages_sendPrefilledMessage

mail_composeEmail

browser_openURL
browser_openSearch

facetime_callVideo
facetime_callAudio

calendar_openApp
calendar_openDate

contacts_openApp
contacts_openContact

settings_openSection

music_openApp
music_openSearch
music_openPlaylist
music_openAlbum
music_openArtist

notes_openApp
notes_createNote

reminders_openApp

clock_openApp

photos_openApp

files_openApp


### 2. MESSAGING APPS

whatsapp_openChat
whatsapp_sendPrefilledMessage

telegram_openChat
telegram_openUser
telegram_sendPrefilledMessage

messenger_openChat
messenger_sendPrefilledMessage

line_openChat
line_sendPrefilledMessage

signal_openChat
signal_sendPrefilledMessage

wechat_openChat
wechat_openProfile
wechat_openMiniProgram

kakaotalk_openChat
kakaotalk_sendPrefilledMessage

viber_openChat
viber_sendPrefilledMessage

discord_openServer
discord_openChannel
discord_openDM

slack_openWorkspace
slack_openChannel
slack_openDM

teams_openChat
teams_openMeeting

skype_openChat
skype_callAudio
skype_callVideo


### 3. EMAIL APPS


gmail_composeEmail
outlook_composeEmail
spark_composeEmail
yahooMail_composeEmail


### 4. PRODUCTIVITY APPS

googleCalendar_openApp
googleCalendar_createEvent

notion_openPage
notion_openDatabase
notion_openSearch

evernote_openNote
evernote_openNotebook

onenote_openPage
onenote_openNotebook

todoist_openTask
todoist_openProject

things3_openTask
things3_openProject

asana_openTask
asana_openProject

trello_openBoard
trello_openCard

clickup_openTask
clickup_openList

monday_openBoard
monday_openItem

jira_openTicket

googleKeep_openNote

bear_openNote

drafts_openDraft

goodnotes_openNotebook
goodnotes_openPage


### 5. NAVIGATION APPS

googleMaps_openSearch
googleMaps_openDirections

waze_openDirections

citymapper_openDirections

moovit_openDirections


### 6. RIDE-HAILING APPS

uber_callRide
uber_openBooking

grab_callRide
grab_openBooking

lyft_callRide
lyft_openBooking

### 7. SOCIAL APPS

instagram_openProfile
instagram_openPost
instagram_openReel
instagram_openSearch
instagram_openCamera

facebook_openProfile
facebook_openPage
facebook_openFeed

tiktok_openVideo
tiktok_openProfile
tiktok_openSearch

twitterX_openTweet
twitterX_openProfile
twitterX_openSearch

snapchat_openCamera
snapchat_openChat

reddit_openSubreddit
reddit_openPost

pinterest_openPin
pinterest_openBoard

linkedin_openProfile
linkedin_openJob

threads_openThread
threads_openProfile

tumblr_openBlog
tumblr_openPost


### 8. MEDIA APPS

youtube_openVideo
youtube_openChannel
youtube_openSearch

youtubeMusic_playSong
youtubeMusic_playAlbum
youtubeMusic_playPlaylist

spotify_playTrack
spotify_playAlbum
spotify_playPlaylist
spotify_openArtist

soundcloud_playTrack
soundcloud_openArtist

netflix_openShow
netflix_openMovie

disneyPlus_openShow
disneyPlus_openMovie

primeVideo_openShow
primeVideo_openMovie

hboMax_openShow
hboMax_openMovie

twitch_openStream
twitch_openChannel

audible_openAudiobook

pocketCasts_openPodcast
pocketCasts_openEpisode


### 9. SHOPPING APPS

amazon_openProduct
amazon_openSearch
amazon_openCart

ebay_openProduct
ebay_openSearch

taobao_openProduct
taobao_openSearch

tmall_openProduct
tmall_openSearch

jd_openProduct
jd_openSearch

shopee_openProduct
shopee_openSearch

lazada_openProduct
lazada_openSearch

### 10. PAYMENT APPS

paypal_openPayment
paypal_sendMoney

venmo_openPayment
venmo_sendMoney

revolut_openPayment
revolut_sendMoney

alipay_openPayment
alipay_openScan

wechatPay_openPayment
wechatPay_openScan

octopus_openApp


### 11. FILE APPS

dropbox_openFile
dropbox_openFolder

googleDrive_openFile
googleDrive_openFolder

onedrive_openFile
onedrive_openFolder

icloudDrive_openFile
icloudDrive_openFolder

scannerPro_openScanner

adobeAcrobat_openPDF

pdfExpert_openPDF

onepassword_openVault
onepassword_openItem

lastpass_openVault
lastpass_openItem



END OF MASTER SPEC
===========================================

# Appendix — Intention Labels (Deduped)

Intention Schema
1. DEEPLINK CAPABILITY TRAINING SPEC AND MAPPING (deeplink_action) FOR TRAINING ONLY, NOT FOR RUNTIME 
Format: <appName>_<actionName>
Dino will learn to emit these EXACT action names for deeplink_action tool calls.
This is the FULL, EXHAUSTIVE, FLATTENED LIST.
1. SYSTEM APPS (DEEPLINK)
maps_openApp maps_openSearch maps_openDirections
phone_callNumber phone_openDialer
messages_openChat messages_sendPrefilledMessage
browser_openURL browser_openSearch
facetime_callVideo facetime_callAudio
calendar_openApp calendar_openDate
contacts_openApp contacts_openContact
music_openApp music_openSearch music_openPlaylist music_openAlbum music_openArtist
notes_openApp notes_createNote
2. MESSAGING APPS
whatsapp_openChat whatsapp_sendPrefilledMessage
telegram_openChat telegram_openUser telegram_sendPrefilledMessage
messenger_openChat messenger_sendPrefilledMessage
line_openChat line_sendPrefilledMessage
signal_openChat signal_sendPrefilledMessage
wechat_openChat wechat_openProfile wechat_openMiniProgram
kakaotalk_openChat kakaotalk_sendPrefilledMessage
viber_openChat viber_sendPrefilledMessage
discord_openServer discord_openChannel discord_openDM
slack_openWorkspace slack_openChannel slack_openDM
teams_openChat teams_openMeeting
skype_openChat skype_callAudio skype_callVideo
3. EMAIL APPS
gmail_composeEmail outlook_composeEmail spark_composeEmail yahooMail_composeEmail
4. PRODUCTIVITY APPS
googleCalendar_openApp googleCalendar_createEvent
notion_openPage notion_openDatabase notion_openSearch
evernote_openNote evernote_openNotebook
onenote_openPage onenote_openNotebook
todoist_openTask todoist_openProject
things3_openTask things3_openProject
asana_openTask asana_openProject
trello_openBoard trello_openCard
clickup_openTask clickup_openList
monday_openBoard monday_openItem
goodnotes_openNotebook goodnotes_openPage
5. NAVIGATION APPS
googleMaps_openSearch googleMaps_openDirections
6. RIDE-HAILING APPS
uber_callRide uber_openBooking
grab_callRide grab_openBooking
lyft_callRide lyft_openBooking
7. SOCIAL APPS
instagram_openProfile instagram_openPost instagram_openReel instagram_openSearch instagram_openCamera
facebook_openProfile facebook_openPage facebook_openFeed
tiktok_openVideo tiktok_openProfile tiktok_openSearch
twitterX_openTweet twitterX_openProfile twitterX_openSearch
snapchat_openCamera snapchat_openChat
reddit_openSubreddit reddit_openPost
pinterest_openPin pinterest_openBoard
linkedin_openProfile linkedin_openJob
threads_openThread threads_openProfile
tumblr_openBlog tumblr_openPost
8. MEDIA APPS
youtube_openVideo youtube_openChannel youtube_openSearch
youtubeMusic_playSong youtubeMusic_playAlbum youtubeMusic_playPlaylist
spotify_playTrack spotify_playAlbum spotify_playPlaylist spotify_openArtist
soundcloud_playTrack soundcloud_openArtist
netflix_openShow netflix_openMovie
disneyPlus_openShow disneyPlus_openMovie
primeVideo_openShow primeVideo_openMovie
hboMax_openShow hboMax_openMovie
twitch_openStream twitch_openChannel
pocketCasts_openPodcast pocketCasts_openEpisode
9. SHOPPING APPS
amazon_openProduct amazon_openSearch amazon_openCart
ebay_openProduct ebay_openSearch
taobao_openProduct taobao_openSearch
tmall_openProduct tmall_openSearch
jd_openProduct jd_openSearch
shopee_openProduct shopee_openSearch
lazada_openProduct lazada_openSearch
10. PAYMENT APPS
paypal_openPayment paypal_sendMoney
venmo_openPayment venmo_sendMoney
revolut_openPayment revolut_sendMoney
alipay_openPayment alipay_openScan
wechatPay_openPayment wechatPay_openScan
11. FILE APPS
dropbox_openFile dropbox_openFolder
googleDrive_openFile googleDrive_openFolder
onedrive_openFile onedrive_openFolder
icloudDrive_openFile icloudDrive_openFolder
onepassword_openVault onepassword_openItem
lastpass_openVault lastpass_openItem
2 Connector Training spec and mapping (connector_action) FOR TRAINING ONLY, NOT FOR RUNTIME 
CONNECTOR TRAINING SPEC (DINO OUTPUT)
1. EMAIL CONNECTOR
email_composeEmail email_replyEmail email_forwardEmail email_attachFiles email_saveDraft
2. MESSAGES CONNECTOR
messages_sendMessage messages_openConversation
3. PHONE CONNECTOR
phone_callNumber phone_openDialer
4. CALENDAR CONNECTOR
calendar_createEvent calendar_updateEvent calendar_deleteEvent calendar_listEvents
5. REMINDERS CONNECTOR
reminders_createReminder reminders_updateReminder reminders_deleteReminder reminders_listReminders
6. NOTES CONNECTOR
notes_createNote notes_appendToNote notes_searchNotes notes_openNote
7. CONTACTS CONNECTOR
contacts_createContact contacts_updateContact contacts_openContact contacts_searchContacts
8. NAVIGATION CONNECTOR
navigation_navigateTo navigation_showLocation navigation_searchPlaces
9. BROWSER CONNECTOR
browser_openURL browser_searchWeb
10. FILES CONNECTOR
files_openFile files_saveFile files_shareFile files_deleteFile
11. SHARE SHEET CONNECTOR
shareSheet_shareText shareSheet_shareURL shareSheet_shareFile
12. MEDIA CONNECTOR
media_playSong media_playArtist media_playAlbum media_openPlaylist
13. HOMEKIT CONNECTOR
homekit_runScene homekit_toggleDevice homekit_setDeviceState
14. SHORTCUTS CONNECTOR
15. PRODUCTIVITY APPS (Notion, Todoist, Things3, Asana, Trello, etc.)
productivity_createTask productivity_updateTask productivity_openProject productivity_openWorkspace productivity_searchWorkspace
16. FILE APPS (Dropbox, Google Drive, OneDrive, iCloud Drive)
fileApps_openFile fileApps_uploadFile fileApps_downloadFile fileApps_searchFiles
17. PAYMENT APPS (PayPal, Venmo, Revolut, Alipay, WeChat Pay)
paymentApps_openPayment paymentApps_sendMoney paymentApps_requestMoney
18. SHOPPING APPS (Amazon, eBay, Taobao, Shopee, Lazada)
shoppingApps_openProduct shoppingApps_searchProduct shoppingApps_openCart
3. Tool Training spec and mapping (connector_action) FOR TRAINING ONLY, NOT FOR RUNTIME 
1. Document export tool 
- docx_export
- xlsx_export
- pptx_export
- csv_export
- md_export
- pdf_export
- python_export
- swift_export
- json_export
2. ZIP
- zip_wrap
3. Internet search
- web_fetch
- image_preview
4. General Intent, Action Intent and Intent Subtype 
User Intention:
5. deeplink, connector, search, history_search (true/false only)
need_deeplink
need_connector
