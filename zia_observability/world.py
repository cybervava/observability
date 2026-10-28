"""Zing Wireless — the world of our story (same in every notebook)."""

CATEGORIES = ["NO_SIGNAL", "BILL_HIGH", "DATA_PLAN", "SLOW_INTERNET", "SIM_ISSUE"]

TEAM_FOR = {"NO_SIGNAL": "NETWORK-OPS", "SLOW_INTERNET": "NETWORK-OPS",
            "BILL_HIGH": "BILLING-OPS", "DATA_PLAN": "PLANS-OPS", "SIM_ISSUE": "SIM-OPS"}

TOWER_FOR = {"Stadium": "TWR-017", "Midtown": "TWR-017", "Brooklyn": "TWR-031",
             "Queens": "TWR-044", "Jersey City": "TWR-052"}

# Real customers: short, emotional, sometimes in Spanish
SAMPLE_MESSAGES = [
    {"id": "M01", "customer": "C101", "place": "Stadium",     "lang": "en", "label": "NO_SIGNAL",     "text": "No signal at the stadium since 7pm!!"},
    {"id": "M02", "customer": "C102", "place": "Midtown",     "lang": "en", "label": "NO_SIGNAL",     "text": "Zero bars in Midtown for 2 hours, can't call anyone"},
    {"id": "M03", "customer": "C103", "place": "Queens",      "lang": "es", "label": "NO_SIGNAL",     "text": "No tengo señal en Queens desde las 9"},
    {"id": "M04", "customer": "C104", "place": "Brooklyn",    "lang": "en", "label": "BILL_HIGH",     "text": "Why is my bill $240? It's usually $65"},
    {"id": "M05", "customer": "C105", "place": "Queens",      "lang": "es", "label": "BILL_HIGH",     "text": "Mi factura es muy alta este mes, $180"},
    {"id": "M06", "customer": "C106", "place": "Jersey City", "lang": "en", "label": "DATA_PLAN",     "text": "Bought the 10GB add-on but it isn't showing"},
    {"id": "M07", "customer": "C107", "place": "Brooklyn",    "lang": "es", "label": "DATA_PLAN",     "text": "Pagué el plan de datos y no funciona"},
    {"id": "M08", "customer": "C108", "place": "Midtown",     "lang": "en", "label": "SLOW_INTERNET", "text": "Internet is super slow, videos keep buffering"},
    {"id": "M09", "customer": "C109", "place": "Queens",      "lang": "es", "label": "SLOW_INTERNET", "text": "El internet está muy lento en Queens"},
    {"id": "M10", "customer": "C110", "place": "Jersey City", "lang": "en", "label": "SIM_ISSUE",     "text": "My new eSIM won't activate"},
    {"id": "M11", "customer": "C111", "place": "Brooklyn",    "lang": "en", "label": "SIM_ISSUE",     "text": "Phone says No SIM card after the update"},
    {"id": "M12", "customer": "C112", "place": "Stadium",     "lang": "en", "label": "NO_SIGNAL",     "text": "Calls keep dropping at the game since 8pm, fix it!"},
]
