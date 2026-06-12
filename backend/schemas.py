"""JSON Schemas for validating model outputs."""

CM_CLIPS_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "required": ["title", "category", "start_time", "end_time", "viral_score", "content"],
        "properties": {
            "title": {"type": "string"},
            "category": {"type": "string"},
            "start_time": {"type": "number"},
            "end_time": {"type": "number"},
            "viral_score": {"type": "number"},
            "content": {"type": "object"},
        },
    },
}

CM_BLOG_SCHEMA = {
    "type": "object",
    "required": ["title", "meta_description", "intro", "sections", "keywords"],
    "properties": {
        "title": {"type": "string"},
        "meta_description": {"type": "string"},
        "intro": {"type": "string"},
        "sections": {"type": "array"},
        "keywords": {"type": "array"},
    },
}

CM_SOCIAL_SCHEMA = {
    "type": "object",
    "required": ["linkedin", "twitter", "facebook"],
    "properties": {
        "linkedin": {"type": "object"},
        "twitter": {"type": "object"},
        "facebook": {"type": "object"},
    },
}

BGS_MARKET_RESEARCH_SCHEMA = {
    "type": "object",
    "required": ["audience", "existing_solutions", "your_product", "market_trends"],
}

BGS_PSYCHOANALYSIS_SCHEMA = {
    "type": "object",
    "required": ["recurring_themes", "prospect_commonalities", "individual_prospect_analysis"],
}

BGS_CREATIVE_BRIEF_SCHEMA = {
    "type": "object",
    "required": ["offer_name", "promise", "problem", "solution", "video_ideas"],
}

BGS_TITLES_SCHEMA = {
    "type": "object",
    "required": ["titles"],
    "properties": {"titles": {"type": "array", "minItems": 1}},
}

BGS_SIMILAR_TITLES_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": {"type": "object", "required": ["title"]},
}

BGS_CHAPTER_STRUCTURE_SCHEMA = {
    "type": "object",
    "required": ["chapters"],
    "properties": {"chapters": {"type": "array", "minItems": 1}},
}

BGS_SCRIPT_CHAPTER_SCHEMA = {
    "type": "object",
    "required": ["option_a", "option_b"],
    "properties": {
        "option_a": {"type": "object", "required": ["script"]},
        "option_b": {"type": "object", "required": ["script"]},
    },
}
