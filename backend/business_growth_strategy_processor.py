from google import genai
import json
import os
import re
import time
from database import get_all_projects, get_project_details
from jsonschema import ValidationError, validate
from schemas import (
    BGS_CHAPTER_STRUCTURE_SCHEMA,
    BGS_CREATIVE_BRIEF_SCHEMA,
    BGS_MARKET_RESEARCH_SCHEMA,
    BGS_PSYCHOANALYSIS_SCHEMA,
    BGS_SCRIPT_CHAPTER_SCHEMA,
    BGS_SIMILAR_TITLES_SCHEMA,
    BGS_TITLES_SCHEMA,
)

DEFAULT_GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3-flash-preview')
DEFAULT_THINKING_LEVEL = os.environ.get("GEMINI_THINKING_LEVEL", "low")

class BusinessGrowthStrategyProcessor:
    def __init__(self, api_key, model_name=None):
        if not api_key:
            raise ValueError("API Key is required for BusinessGrowthStrategyProcessor")
        self.model_name = model_name or DEFAULT_GEMINI_MODEL
        
        # Skip AI initialization for unit tests
        if api_key == "test_key":
            self.client = None
            self._runtime_stats = {"gemini_retries": 0, "gemini_calls": 0}
            return
            
        self.client = genai.Client(api_key=api_key)
        self._runtime_stats = {"gemini_retries": 0, "gemini_calls": 0}

    def _reset_runtime_stats(self):
        self._runtime_stats = {"gemini_retries": 0, "gemini_calls": 0}

    @staticmethod
    def _is_gemini_3_model(model_name):
        return str(model_name or "").startswith("gemini-3")

    @staticmethod
    def _build_generation_config(model_name):
        if not BusinessGrowthStrategyProcessor._is_gemini_3_model(model_name):
            return None
        return {
            "thinking_config": {
                "thinking_level": DEFAULT_THINKING_LEVEL,
            }
        }

    @staticmethod
    def _validate_with_schema(payload, schema):
        try:
            validate(instance=payload, schema=schema)
            return True, None
        except ValidationError as exc:
            return False, str(exc)

    def _generate_content_with_retry(self, prompt, max_attempts=3, base_backoff_seconds=0.7):
        if self.client is None:
            raise RuntimeError("Gemini client unavailable")

        last_error = None
        for attempt in range(1, max_attempts + 1):
            self._runtime_stats["gemini_calls"] += 1
            try:
                request_kwargs = {
                    "model": self.model_name,
                    "contents": prompt,
                }
                generation_config = self._build_generation_config(self.model_name)
                if generation_config is not None:
                    request_kwargs["config"] = generation_config
                return self.client.models.generate_content(**request_kwargs)
            except Exception as exc:
                last_error = exc
                if attempt >= max_attempts:
                    break
                self._runtime_stats["gemini_retries"] += 1
                time.sleep(base_backoff_seconds * (2 ** (attempt - 1)))
        raise last_error

    @staticmethod
    def _normalize_language(language):
        normalized = str(language or "pl").strip().lower()
        return normalized if normalized in ("pl", "en") else "pl"

    @classmethod
    def _language_label(cls, language):
        return "Polish" if cls._normalize_language(language) == "pl" else "English"

    @staticmethod
    def _ensure_object(value):
        return value if isinstance(value, dict) else {}

    def _normalize_market_research_payload(self, payload):
        """
        Normalize market research response so strict schema validation does not fail
        on occasional LLM omissions of required top-level sections.
        """
        alias_map = {
            "existingSolutions": "existing_solutions",
            "yourProduct": "your_product",
            "marketTrends": "market_trends",
        }
        required_sections = ("audience", "existing_solutions", "your_product", "market_trends")

        source = payload if isinstance(payload, dict) else {}
        normalized = dict(source)
        missing_sections = []

        for alias_key, canonical_key in alias_map.items():
            if canonical_key in normalized:
                continue
            alias_value = normalized.get(alias_key)
            if isinstance(alias_value, dict):
                normalized[canonical_key] = alias_value

        for key in required_sections:
            if key not in normalized:
                missing_sections.append(key)
            normalized[key] = self._ensure_object(normalized.get(key))

        audience = normalized["audience"]
        audience.setdefault("attitudes", {})
        audience.setdefault("desires", [])
        audience.setdefault("fears", [])

        existing_solutions = normalized["existing_solutions"]
        existing_solutions.setdefault("products_tried", [])
        existing_solutions.setdefault("successes", [])
        existing_solutions.setdefault("failures", [])
        existing_solutions.setdefault("horror_stories", "")
        existing_solutions.setdefault("market_belief", "")
        existing_solutions.setdefault("gap_analysis", "")

        your_product = normalized["your_product"]
        your_product.setdefault("unique_differentiators", [])
        your_product.setdefault("interesting_facts", [])
        your_product.setdefault("customer_testimonials_themes", "")
        your_product.setdefault("competitive_advantages", "")
        your_product.setdefault("positioning_statement", "")

        market_trends = normalized["market_trends"]
        market_trends.setdefault("current_trends", [])
        market_trends.setdefault("emerging_opportunities", [])
        market_trends.setdefault("threats", [])

        if missing_sections:
            print(f"[WARN] Market research response missing required sections, auto-filled: {missing_sections}")

        return normalized

    @staticmethod
    def _contains_recap_intro(text):
        snippet = str(text or "").strip().lower()
        if not snippet:
            return False

        patterns = [
            r"\bw poprzednim (rozdziale|odcinku)\b",
            r"\bw tym rozdziale\b",
            r"\bjak wcześniej mówiliśmy\b",
            r"\bin previous (chapter|episode)\b",
            r"\bin the previous (chapter|episode)\b",
            r"\blast (chapter|episode)\b",
            r"\bprevious chapter\b",
            r"\bprevious episode\b",
        ]
        return any(re.search(pattern, snippet, flags=re.IGNORECASE) for pattern in patterns)

    def _remove_recap_opening(self, script_text):
        text = str(script_text or "").strip()
        if not text:
            return text

        # Remove leading recap-style sentences if they appear at the start.
        sentences = re.split(r"(?<=[.!?])\s+", text)
        cleaned_sentences = []
        skipping_intro = True
        for sentence in sentences:
            stripped = sentence.strip()
            if skipping_intro and stripped and self._contains_recap_intro(stripped):
                continue
            skipping_intro = False
            cleaned_sentences.append(sentence)

        cleaned = " ".join(cleaned_sentences).strip()
        if cleaned:
            return cleaned

        # Fallback: if we couldn't split cleanly, remove a recap clause from the beginning.
        fallback = re.sub(
            r"^\s*[^.!?]*\b(?:w poprzednim (?:rozdziale|odcinku)|in previous (?:chapter|episode)|in the previous (?:chapter|episode)|last (?:chapter|episode)|previous chapter|previous episode)\b[^.!?]*[.!?]?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        return fallback or text

    def _sanitize_script_options(self, payload):
        if not isinstance(payload, dict):
            return payload

        for option_key in ("option_a", "option_b"):
            option = payload.get(option_key)
            if not isinstance(option, dict):
                continue
            script = option.get("script")
            if not isinstance(script, str):
                continue

            cleaned_script = self._remove_recap_opening(script)
            option["script"] = cleaned_script
            option["word_count"] = len(re.findall(r"\S+", cleaned_script))

        return payload

    @staticmethod
    def _count_unescaped_quotes(text):
        return len(re.findall(r'(?<!\\)"', str(text or "")))

    @staticmethod
    def _heal_list_string_items(text):
        """
        Repairs common malformed JSON list-item strings produced by LLMs:
        1) Unterminated item: "some text,
        2) Annotation outside quote: "some text" (note),
        """
        if not text:
            return text

        # Case 2: move trailing parenthetical annotation inside the string.
        # Example: "Title" (annotation), -> "Title (annotation)",
        text = re.sub(
            r'("(?:(?:\\.|[^"\\])*)")\s+\(([^)\n]+)\)(\s*,?)',
            lambda m: f'{m.group(1)[:-1]} ({m.group(2)})"{m.group(3)}',
            text,
        )

        # Case 1: close odd-quote list lines ending with comma.
        fixed_lines = []
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if re.match(r'^\s*"', line) and line.endswith(","):
                if BusinessGrowthStrategyProcessor._count_unescaped_quotes(line) % 2 == 1:
                    line = line[:-1] + '",'
            fixed_lines.append(line)
        return "\n".join(fixed_lines)

    def _repair_json_with_model(self, raw_text):
        """
        Last-resort JSON repair using the model.
        Returns raw repaired text (not parsed object).
        """
        if self.client is None:
            raise RuntimeError("Gemini client unavailable for model-based JSON repair")

        prompt = f"""You are a JSON repair assistant.
Return ONLY valid JSON. No markdown, no comments, no explanation.
Preserve all fields and values if possible.

TEXT TO REPAIR:
{str(raw_text or "")[:25000]}
"""
        response = self._generate_content_with_retry(prompt)
        return (response.text or "").strip()

    def _extract_json(self, text, allow_model_repair=True):
        """Robust JSON extraction from Gemini response."""
        text = text.strip()
        
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            text = json_match.group(1).strip()
        
        # Also try to find JSON starting with { or [
        if not (text.startswith('{') or text.startswith('[')):
            start_brace = text.find('{')
            start_bracket = text.find('[')
            if start_brace >= 0 and (start_bracket < 0 or start_brace < start_bracket):
                text = text[start_brace:]
            elif start_bracket >= 0:
                text = text[start_bracket:]
            
        # Basic cleanup: remove trailing commas before closing braces/brackets
        text = re.sub(r',\s*([\]}])', r'\1', text)
        
        # HEALING STEP 1: Surgical fix for positioning_statement Early Closure
        # Handle cases where AI might output multiple closing braces } } }
        text = re.sub(r'("positioning_statement":\s*".*?")\s*[\s\},]+\s*"(market_trends":)', r'\1, "\2', text, flags=re.DOTALL)
        
        # HEALING STEP 2: Schema-aware heal for top-level keys
        expected_keys = ["market_trends", "swot_analysis", "strategic_recommendations"]
        for key in expected_keys:
            text = re.sub(r'\}\s*,?\s*"' + key + '":', r', "' + key + '":', text)
            
        # HEALING STEP 3: Fix missing commas between closing brace/bracket and next quote/brace
        # e.g. "manifestations": [ ... ] "next_key": ...  OR  }, { "title": ... }
        text = re.sub(r'([\]\}])\s*(?=["\{])', r'\1, ', text)

        # HEALING STEP 3b: Repair malformed list string items and trailing parenthetical notes.
        text = self._heal_list_string_items(text)
        
        # HEALING STEP 3: Escape ALL control characters (0-31) that might be inside strings
        # This replaces characters like \x03 with \u0003 so json.loads doesn't crash
        def escape_control_chars(match):
            s = match.group(0)
            return "".join(f"\\u{ord(c):04x}" if ord(c) < 32 else c for c in s)
        
        # HEALING STEP: Fix unescaped quotes in specific contexts (common in AI text)
        # Pattern: ("' -> (\"'
        text = re.sub(r'\("\'', r'(\"\'', text)
        # Pattern: '") -> '\")
        text = re.sub(r'\'"\)', r'\'\")', text)

        # We target content between quotes. This is an approximation but very effective.
        text = re.sub(r'"(.*?[^\\])"', escape_control_chars, text, flags=re.DOTALL)

        # HEALING STEP 4: Balance braces/brackets using a stack
        # This handles nested structures correctly (e.g. {"a": [1, 2 -> ]})
        stack = []
        for char in text:
            if char == '{':
                stack.append('}')
            elif char == '[':
                stack.append(']')
            elif char == '}' or char == ']':
                if stack and stack[-1] == char:
                    stack.pop()
        
        # Append missing closing characters in reverse order
        if stack:
            text += "".join(reversed(stack))

        try:
            # Try raw_decode to ignore trailing garbage
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text)
            return obj
        except json.JSONDecodeError as e:
            # Check for specific "Orphan Object" error (Expecting property name)
            if "Expecting property name" in str(e):
                print(f"[JSON ERROR] Detected orphan object. Attempting to wrap video ideas...")
                if re.search(r'([\]\}])\s*,?\s*\{\s*"title":', text):
                    text = re.sub(r'([\]\}])\s*,?\s*(\{\s*"title":)', r'\1, "video_ideas": [\2', text, count=1)
                    if text.strip().endswith('}'):
                        text = text.strip()[:-1] + ']}'
                    else:
                        text += ']}'
                    try:
                        return json.loads(text)
                    except Exception as e3:
                        print(f"[JSON ERROR] Orphan wrap failed: {e3}")

            # NEW: Iterative Surgical Healer for "Expecting , delimiter" (Unescaped Quotes)
            # This loops up to 3 times to fix multiple unescaped quotes
            if "Expecting ',' delimiter" in str(e):
                current_text = text
                for attempt in range(3):
                    try:
                        print(f"[JSON ERROR] Expecting delimiter at {e.pos}. Attempting surgical quote fix (Attempt {attempt+1})...")
                        # Find the last quote before e.pos
                        # e.pos usually points to the character *after* the string apparently closed.
                        # We want to escape the quote that caused the closure.
                        error_pos = e.pos
                        # Search backwards from error_pos for a quote
                        pre_error_text = current_text[:error_pos]
                        last_quote_idx = pre_error_text.rfind('"')
                        
                        if last_quote_idx != -1:
                           # Escape it
                           fixed_text = current_text[:last_quote_idx] + '\\"' + current_text[last_quote_idx+1:]
                           # Try to parse immediately to see if it works or moves the error
                           try:
                               return json.loads(fixed_text)
                           except json.JSONDecodeError as new_e:
                               if "Expecting ',' delimiter" in str(new_e) and new_e.pos > error_pos:
                                   # We made progress! The error moved forward. Update current_text and continue loop.
                                   current_text = fixed_text
                                   e = new_e # Update e for next iteration log
                                   continue
                               elif attempt == 2:
                                   # Last attempt, if it failed, maybe try the fallback below
                                   current_text = fixed_text # Keep the fix anyway
                               else:
                                   current_text = fixed_text
                                   e = new_e
                                   continue
                        else:
                            break # No quote found to fix
                    except Exception:
                         break
                # Only if the loop finishes without returning, we use the modified text for the final fallback
                text = current_text
            
            print(f"[JSON ERROR] Initial parse failed: {e}. Attempting final fallback heal...")
            try:
                # FINAL FALLBACK: Fix unescaped newlines within strings specifically
                healed = re.sub(r'(?<=[:\[,])\s*"(.*?)"(?=\s*[,\]}])', 
                                lambda m: '"' + m.group(1).replace('\n', '\\n').replace('\r', '') + '"', 
                                text, flags=re.DOTALL)
                return json.loads(healed)
            except Exception as e2:
                if allow_model_repair and self.client is not None:
                    try:
                        print("[JSON ERROR] Attempting model-based JSON repair...")
                        repaired = self._repair_json_with_model(text)
                        return self._extract_json(repaired, allow_model_repair=False)
                    except Exception as model_err:
                        print(f"[JSON ERROR] Model repair failed: {model_err}")
                # Save failure to file
                try:
                    with open("debug_json_failure.txt", "w", encoding="utf-8") as f:
                        f.write(f"ERROR: {e}\nHEAL_ERROR: {e2}\n" + "-"*50 + "\n" + text)
                    print(f"[JSON ERROR] Saved to debug_json_failure.txt")
                except: pass
                raise e

    def _get_cm_transcripts(self):
        """Get all Content Maximizer project transcripts from database."""
        try:
            projects = get_all_projects()
            transcripts = []
            for p in projects:
                if p.get('type') == 'content-maximizer':
                    details = get_project_details(p.get('id'))
                    if details and details.get('transcriptData'):
                        transcript = details['transcriptData'].get('transcript', '')
                        if transcript:
                            title = details.get('title', 'Untitled')
                            transcripts.append(f"[{title}]\n{transcript[:3000]}")
            return "\n\n---\n\n".join(transcripts) if transcripts else ""
        except Exception as e:
            print(f"[ERROR] Failed to load CM transcripts: {e}")
            return ""

    # =========================================================================
    # SECTION 1: MARKET RESEARCH
    # Based on 1MarketResearchTemplate.txt
    # Uses: Website + Sales Transcripts + CM Transcripts + Google Search
    # =========================================================================
    def generate_market_research(self, website_content, sales_transcripts, cm_transcripts, manual_context, language="pl"):
        """
        Generates comprehensive Market Research based on all data sources.
        Following the structure from 1MarketResearchTemplate.txt
        """
        self._reset_runtime_stats()
        language = self._normalize_language(language)
        language_label = self._language_label(language)
        prompt = f"""
You are a world-class Market Research Analyst. Create an EXTENSIVE and DETAILED Market Research document.
ALL narrative fields in the JSON output must be written in {language_label}.
Keep JSON keys exactly as provided in English.

=== DATA SOURCES ===

WEBSITE CONTENT:
{website_content[:8000] if website_content else 'Not provided'}

SALES CALL TRANSCRIPTS:
{sales_transcripts[:10000] if sales_transcripts else 'Not provided'}

EXISTING CONTENT TRANSCRIPTS (from previous videos):
{cm_transcripts[:5000] if cm_transcripts else 'Not provided'}

ADDITIONAL CONTEXT:
{manual_context if manual_context else 'Not provided'}

=== OUTPUT STRUCTURE (JSON) ===
Generate a comprehensive research document with the following sections. Each section should be DETAILED and EXTENSIVE (multiple paragraphs where appropriate):

{{
    "audience": {{
        "gender_mix": "Detailed description of target gender demographics...",
        "ideal_client_description": "Comprehensive description of the ideal client profile with specific details...",
        "age_range": "Age range with context on why this matters...",
        "attitudes": {{
            "religious": "Religious attitudes and how they affect buying behavior...",
            "political": "Political leanings and their business implications...",
            "social": "Social attitudes, values, and community involvement...",
            "economic": "Economic mindset, spending habits, investment attitudes..."
        }},
        "desires": ["List of 10+ deep desires with explanations..."],
        "fears": ["List of 10+ fears and anxieties with context..."],
        "current_identity": "Who they see themselves as RIGHT NOW - detailed psychological profile...",
        "desired_identity": "Who they WANT TO BECOME - the transformation they seek...",
        "perceived_obstacles": "External forces THEY BELIEVE have prevented their success...",
        "life_beliefs": "Core beliefs about life, success, business, relationships..."
    }},
    "existing_solutions": {{
        "products_tried": ["List of 10+ products/solutions they've likely tried..."],
        "successes": ["What has worked for them in the past..."],
        "failures": ["What has failed them and why..."],
        "horror_stories": "Common horror stories about existing solutions in this market...",
        "market_belief": "Does the market believe existing solutions work? Why or why not?",
        "gap_analysis": "The critical gaps that current solutions fail to address..."
    }},
    "your_product": {{
        "unique_differentiators": ["10+ things that make this offer unique..."],
        "interesting_facts": ["Interesting stories, facts, or angles about the product..."],
        "customer_testimonials_themes": "Common themes from what customers say...",
        "competitive_advantages": "Clear advantages over competitors...",
        "positioning_statement": "One powerful positioning statement..."
    }},
    "market_trends": {{
        "current_trends": ["5+ current market trends relevant to this business..."],
        "emerging_opportunities": ["5+ emerging opportunities to capitalize on..."],
        "threats": ["Potential threats or challenges in the market..."]
    }}
}}

Be extremely thorough. The user needs this for strategic content creation.
"""
        try:
            response = self._generate_content_with_retry(prompt)
            print(f"[DEBUG] generate_market_research response length: {len(response.text)}")
            extracted = self._extract_json(response.text)
            extracted = self._normalize_market_research_payload(extracted)
            ok, error = self._validate_with_schema(extracted, BGS_MARKET_RESEARCH_SCHEMA)
            if not ok:
                return {"error": f"Schema validation failed: {error}"}
            return extracted
        except Exception as e:
            print(f"[ERROR] generate_market_research: {e}")
            return {"error": str(e)}

    # =========================================================================
    # SECTION 2: PSYCHOANALYSIS
    # Based on 2PsychoAnalysisTemplate.txt
    # Uses: ONLY Sales Call Transcripts (primary focus)
    # =========================================================================
    def generate_psychoanalysis(self, sales_transcripts, language="pl"):
        """
        Generates deep Psychoanalysis of prospects from sales call transcripts.
        Following the structure from 2PsychoAnalysisTemplate.txt
        """
        self._reset_runtime_stats()
        language = self._normalize_language(language)
        language_label = self._language_label(language)
        if not sales_transcripts or len(sales_transcripts.strip()) < 100:
            return {
                "error": "Insufficient sales transcript data for psychoanalysis. Please upload sales call transcripts."
            }

        prompt = f"""
You are a world-class Sales Psychologist and Behavioral Analyst. Perform a DEEP PSYCHOANALYSIS of the prospects from these sales call transcripts.
ALL narrative fields in the JSON output must be written in {language_label}.
Keep JSON keys exactly as provided in English.

=== SALES CALL TRANSCRIPTS ===
{sales_transcripts[:20000]}

=== OUTPUT STRUCTURE (JSON) ===
Generate an extensive psychological analysis with the following sections:

{{
    "recurring_themes": [
        "Theme 1: Detailed explanation of this recurring pattern...",
        "Theme 2: Another recurring pattern with context...",
        "(list 10+ themes)"
    ],
    "prospect_commonalities": [
        "Commonality 1: What's similar between prospects with explanation...",
        "(list 8+ commonalities)"
    ],
    "problems_they_relate_to": [
        "Problem 1: Specific problem they'd relate to...",
        "Problem 2: Another relatable problem...",
        "(list 30 problems)"
    ],
    "individual_prospect_analysis": [
        {{
            "name": "Prospect Name (or Prospect 1 if unnamed)",
            "core_identity": "Who they are, their posture, their self-image...",
            "dominant_archetype": "Bull, Eagle, Monkey, or mix - with explanation...",
            "primary_motivations": "What drives them - Aspiration, Authority, Speed, Safety, Belonging...",
            "frictions_from_history": "Past experiences that create resistance...",
            "decision_style": "How they make decisions - fast, slow, logical, emotional...",
            "buying_triggers": "What specifically triggers them to buy...",
            "fears_and_objections": "Implied fears and likely objections...",
            "messaging_that_lands": "Exact messaging style that works for them...",
            "proof_required": "What proof do they need to convert...",
            "risks_to_manage": "Risks in working with this type of client..."
        }}
    ],
    "cognitive_biases": {{
        "common_biases": [
            "Bias 1: Explanation of how this bias manifests...",
            "(list 10+ biases with explanations)"
        ],
        "bias_by_prospect_type": "How different prospect types show different biases..."
    }},
    "common_phrases": {{
        "financial_language": ["Phrases related to money, ROI, deals..."],
        "program_experience_language": ["Phrases about past experiences..."],
        "execution_tools_language": ["Phrases about systems, tools, processes..."],
        "tone_markers": ["Emotional tone words they use..."],
        "theme_summary": "Overall theme of how prospects communicate..."
    }},
    "correlating_quotes": {{
        "desire_for_expert_access": ["Direct quotes showing this desire..."],
        "roi_focus": ["Quotes about money and returns..."],
        "past_burns": ["Quotes about negative past experiences..."],
        "urgency_readiness": ["Quotes showing readiness to act..."],
        "excitement_commitment": ["Quotes showing enthusiasm..."]
    }},
    "cross_persona_insights": {{
        "why_they_buy": "Unified understanding of purchase psychology...",
        "universal_triggers": ["Triggers that work across all prospect types..."],
        "universal_objections": ["Objections common to all prospects..."]
    }}
}}

Be extremely thorough. Extract actual quotes when possible. This analysis will drive all content creation.
"""
        try:
            response = self._generate_content_with_retry(prompt)
            print(f"[DEBUG] generate_psychoanalysis response length: {len(response.text)}")
            extracted = self._extract_json(response.text)
            ok, error = self._validate_with_schema(extracted, BGS_PSYCHOANALYSIS_SCHEMA)
            if not ok:
                return {"error": f"Schema validation failed: {error}"}
            return extracted
        except Exception as e:
            print(f"[ERROR] generate_psychoanalysis: {e}")
            return {"error": str(e)}

    # =========================================================================
    # SECTION 3: CREATIVE BRIEF
    # Based on 3CreativeBriefTemplate.txt
    # Uses: Market Research + Psychoanalysis + All Data
    # =========================================================================
    def generate_creative_brief(self, market_research, psychoanalysis, website_content, manual_context, language="pl"):
        """
        Generates comprehensive Creative Brief combining all insights.
        Following the structure from 3CreativeBriefTemplate.txt
        """
        self._reset_runtime_stats()
        language = self._normalize_language(language)
        language_label = self._language_label(language)
        prompt = f"""
You are a world-class Creative Director at a top content agency. Create a COMPREHENSIVE Creative Brief for video content marketing.
ALL narrative fields in the JSON output must be written in {language_label}.
Keep JSON keys exactly as provided in English.

=== INPUT DATA ===

MARKET RESEARCH:
{json.dumps(market_research, indent=2)[:8000]}

PSYCHOANALYSIS:
{json.dumps(psychoanalysis, indent=2)[:8000]}

WEBSITE/OFFER CONTEXT:
{website_content[:3000] if website_content else 'Not provided'}

ADDITIONAL CONTEXT:
{manual_context if manual_context else 'Not provided'}

=== OUTPUT STRUCTURE (JSON) ===
Generate a complete Creative Brief with these sections:

{{
    "offer_name": "Name of the offer/product/service...",
    "promise": {{
        "main_promise": "The core promise - what are we guaranteeing?",
        "supporting_promises": ["Additional promises that support the main one..."]
    }},
    "problem": {{
        "core_problem": "The main problem we're solving...",
        "manifestations": ["How this problem shows up in their daily life..."],
        "cost_of_inaction": "What happens if they don't solve this..."
    }},
    "solution": {{
        "core_solution": "How we solve the problem...",
        "mechanism": "The unique mechanism/method we use...",
        "why_it_works": "Why this solution works when others failed..."
    }},
    "sales_argument": {{
        "main_argument": "The primary sales argument...",
        "supporting_points": ["Points that strengthen the argument..."],
        "objection_handlers": ["Pre-emptive objection handling..."]
    }},
    "reasons_to_believe": [
        "Reason 1: Credibility element...",
        "Reason 2: Proof point...",
        "(list 5+ reasons)"
    ],
    "primary_avatar": {{
        "description": "Detailed description of the primary customer avatar...",
        "dream_outcome": "Their ultimate dream outcome - in vivid detail...",
        "obstacles": ["What's standing in their way..."],
        "key_bullets": ["Key benefit bullets that matter to them..."],
        "solutions_they_need": ["Specific solutions they're looking for..."],
        "offer_positioning": "How to position the offer for this avatar...",
        "mechanisms_that_resonate": ["Mechanisms/methods that appeal to them..."],
        "deliverables_they_want": [
            {{"feature": "Feature 1", "benefit": "Benefit 1"}},
            {{"feature": "Feature 2", "benefit": "Benefit 2"}}
        ]
    }},
    "client_journey": {{
        "week_1": "What happens in week 1...",
        "week_2": "Week 2 focus...",
        "week_3": "Week 3 focus...",
        "week_4": "Week 4+ and ongoing...",
        "transformation_arc": "The emotional/practical transformation arc..."
    }},
    "guarantee": {{
        "guarantee_statement": "The guarantee we offer...",
        "risk_reversal": "How we reverse the risk..."
    }},
    "final_sales_argument": "The closing argument - why they should act NOW...",
    "tone_and_style": {{
        "voice": "How we should sound...",
        "energy": "High/medium/low energy...",
        "key_phrases_to_use": ["Phrases that resonate with this audience..."],
        "phrases_to_avoid": ["What NOT to say..."]
    }},
    "content_pillars": [
        {{
            "pillar": "Content Pillar 1",
            "description": "What this pillar covers...",
            "example_topics": ["Topic ideas for this pillar..."]
        }}
    ],
    "video_ideas": [
        {{
            "title": "Hooky Video Title 1",
            "concept": "What this video covers...",
            "format": "Talking Head / Tutorial / Case Study / etc.",
            "pillar": "Which content pillar this belongs to"
        }}
    ]
}}

Generate 30 video ideas at the end. Make each section thorough and actionable.
"""
        try:
            response = self._generate_content_with_retry(prompt)
            print(f"[DEBUG] generate_creative_brief response length: {len(response.text)}")
            extracted = self._extract_json(response.text)
            ok, error = self._validate_with_schema(extracted, BGS_CREATIVE_BRIEF_SCHEMA)
            if not ok:
                return {"error": f"Schema validation failed: {error}"}
            return extracted
        except Exception as e:
            print(f"[ERROR] generate_creative_brief: {e}")
            return {"error": str(e)}

    def process_file_content(self, file_storage):
        """Reads text from uploaded file (assuming txt/utf-8 for now)."""
        try:
            return file_storage.read().decode('utf-8')
        except Exception:
            return ""

    def run_full_pipeline(self, manual_context, website_content, sales_transcripts, language="pl"):
        """
        Runs the complete Business Growth Strategy generation pipeline (Blocking).
        """
        language = self._normalize_language(language)
        # ... (Existing implementation kept for backward compatibility if needed, 
        # but we can also making it use the stream or just leave it)
        # For now, I'll essentially copy the logic but with yields for the new method.
        # To avoid code duplication, I could refactor, but for safety I will add the new method explicitly.
        print("[PIPELINE] Starting Business Growth Strategy generation...")
        
        # Get CM transcripts from database
        cm_transcripts = self._get_cm_transcripts()
        print(f"[PIPELINE] Loaded {len(cm_transcripts)} chars from CM transcripts")
        
        # Step 1: Market Research
        print("[PIPELINE] Step 1: Generating Market Research...")
        market_research = self.generate_market_research(
            website_content, 
            sales_transcripts, 
            cm_transcripts,
            manual_context,
            language=language,
        )
        
        # Step 2: Psychoanalysis
        print("[PIPELINE] Step 2: Generating Psychoanalysis...")
        psychoanalysis = self.generate_psychoanalysis(sales_transcripts, language=language)
        
        # Step 3: Creative Brief
        print("[PIPELINE] Step 3: Generating Creative Brief...")
        creative_brief = self.generate_creative_brief(
            market_research,
            psychoanalysis,
            website_content,
            manual_context,
            language=language,
        )
        
        print("[PIPELINE] Business Growth Strategy generation complete!")
        
        return {
            "market_research": market_research,
            "psychoanalysis": psychoanalysis,
            "creative_brief": creative_brief
        }

    def run_full_pipeline_stream(self, manual_context, website_content, sales_transcripts, language="pl"):
        """
        Generator that runs the pipeline and fields progress events.
        Yields JSON strings: {"type": "progress", "stage": "...", "percent": X, "message": "...", "time_remaining": "..."}
        Final yield is {"type": "complete", "business_growth_strategy": {...}} or {"type": "error", "message": "..."}
        """
        language = self._normalize_language(language)
        def yield_event(data):
            try:
                return json.dumps(data) + "\n"
            except Exception as e:
                return json.dumps({"type": "error", "message": f"Serialization Error: {str(e)}"}) + "\n"

        try:
            total_retries = 0
            total_calls = 0
            yield yield_event({"type": "progress", "stage": "init", "percent": 5, "message": "Initializing...", "time_remaining": "~2-3 mins left"})
            
            # Get CM transcripts
            cm_transcripts = self._get_cm_transcripts()
            yield yield_event({"type": "progress", "stage": "init", "percent": 10, "message": f"Loaded {len(cm_transcripts)} chars of context", "time_remaining": "~2-3 mins left"})
            
            # Step 1: Market Research
            yield yield_event({"type": "progress", "stage": "market_research", "percent": 20, "message": "Analyzing Market & Competition...", "time_remaining": "~2 mins left"})
            
            market_research = self.generate_market_research(
                website_content, 
                sales_transcripts, 
                cm_transcripts,
                manual_context,
                language=language,
            )
            total_retries += int(self._runtime_stats.get("gemini_retries", 0))
            total_calls += int(self._runtime_stats.get("gemini_calls", 0))
            
            if 'error' in market_research:
                 yield yield_event({"type": "error", "message": f"Market Research Failed: {market_research['error']}"})
                 return

            yield yield_event({"type": "progress", "stage": "market_research_done", "percent": 45, "message": "Market Research Complete", "time_remaining": "~1.5 mins left"})
            
            # Step 2: Psychoanalysis
            yield yield_event({"type": "progress", "stage": "psychoanalysis", "percent": 50, "message": "Performing Psychoanalysis...", "time_remaining": "~1 min left"})
            
            psychoanalysis = self.generate_psychoanalysis(sales_transcripts, language=language)
            total_retries += int(self._runtime_stats.get("gemini_retries", 0))
            total_calls += int(self._runtime_stats.get("gemini_calls", 0))
            
            # Psychoanalysis soft fail warning
            if 'error' in psychoanalysis:
                 yield yield_event({"type": "progress", "stage": "psychoanalysis_warn", "percent": 65, "message": f"Psychoanalysis Warning: {psychoanalysis['error']}", "time_remaining": "~1 min left"})
            
            yield yield_event({"type": "progress", "stage": "psychoanalysis_done", "percent": 75, "message": "Psychoanalysis Complete", "time_remaining": "~30 secs left"})
            
            # Step 3: Creative Brief
            yield yield_event({"type": "progress", "stage": "creative_brief", "percent": 80, "message": "Drafting Creative Brief...", "time_remaining": "~30 secs left"})
            
            creative_brief = self.generate_creative_brief(
                market_research,
                psychoanalysis,
                website_content,
                manual_context,
                language=language,
            )
            total_retries += int(self._runtime_stats.get("gemini_retries", 0))
            total_calls += int(self._runtime_stats.get("gemini_calls", 0))
            
            if 'error' in creative_brief:
                yield yield_event({"type": "error", "message": f"Creative Brief Failed: {creative_brief['error']}"})
                return

            yield yield_event({"type": "progress", "stage": "creative_brief_done", "percent": 95, "message": "Finalizing Business Growth Strategy...", "time_remaining": "Almost done..."})
            
            # Assembly
            business_growth_strategy = {
                "market_research": market_research,
                "psychoanalysis": psychoanalysis,
                "creative_brief": creative_brief
            }
            
            yield yield_event({
                "type": "complete",
                "percent": 100,
                "business_growth_strategy": business_growth_strategy,
                "game_plan": business_growth_strategy,  # Legacy alias for older frontend clients.
                "time_remaining": "Complete!",
                "metrics": {
                    "gemini_retries": total_retries,
                    "gemini_calls": total_calls,
                },
            })
            
        except Exception as e:
            print(f"[STREAM ERROR] {e}")
            yield yield_event({"type": "error", "message": str(e)})

    # =========================================================================
    # CONTENT IDEAS - TAB 4: Interactive Video Content Creation
    # =========================================================================
    
    def generate_video_titles(self, context_data, language="pl"):
        """
        Generates 5 video titles with concepts.
        Uses Market Research, Psychoanalysis, and Creative Brief context.
        """
        self._reset_runtime_stats()
        language = self._normalize_language(language)
        language_label = self._language_label(language)
        print(f"[CONTENT IDEAS] Generating 5 video titles in {language}...")
        
        prompt = f"""You are a world-class YouTube Content Strategist specializing in B2B content.

=== CONTEXT FROM BUSINESS GROWTH STRATEGY ===
{json.dumps(context_data, indent=2, default=str)[:15000]}

=== YOUR TASK ===
Generate 5 compelling long-form YouTube video titles for this B2B business.

IMPORTANT RULES:
1. ALL titles MUST be in {language_label}
2. Titles should be optimized for YouTube search and click-through rate
3. Each title should address a different angle/topic from the Business Growth Strategy insights
4. Target length: 8-15 words per title
5. Use patterns that work: How to..., X Steps to..., Why..., The Secret to..., etc.

=== OUTPUT FORMAT (JSON) ===
{{
    "titles": [
        {{
            "title": "Full video title in {language_label}",
            "concept": "2-3 sentence description of what this video covers",
            "target_audience": "Who specifically this video is for",
            "hook": "The emotional/curiosity hook that makes people click",
            "content_pillar": "Which content pillar this serves"
        }},
        // ... 4 more titles
    ]
}}

Generate exactly 5 unique, compelling titles now:"""

        try:
            response = self._generate_content_with_retry(prompt)
            extracted = self._extract_json(response.text)
            ok, error = self._validate_with_schema(extracted, BGS_TITLES_SCHEMA)
            if not ok:
                return {"error": f"Schema validation failed: {error}", "titles": []}
            return extracted
        except Exception as e:
            print(f"[ERROR] Failed to generate video titles: {e}")
            return {"error": str(e), "titles": []}

    def generate_similar_title(self, original_title, context_data, language="pl", count=4):
        """
        Generates multiple variations of an existing title.
        Returns an array of title objects.
        """
        self._reset_runtime_stats()
        language = self._normalize_language(language)
        language_label = self._language_label(language)
        print(f"[CONTENT IDEAS] Generating {count} similar titles to: {original_title[:50]}...")
        
        prompt = f"""You are a YouTube Title Optimization Expert.

=== ORIGINAL TITLE ===
{original_title}

=== CONTEXT ===
{json.dumps(context_data, indent=2, default=str)[:8000]}

=== YOUR TASK ===
Create {count} NEW variations of this title. Each should:
1. Cover the same topic but from a different angle
2. Use a different emotional hook or structure
3. Be in {language_label}
4. Be equally or more compelling

=== OUTPUT FORMAT (JSON ARRAY) ===
[
    {{
        "title": "Title variation 1 in {language_label}",
        "concept": "2-3 sentence description",
        "content_pillar": "Category name",
        "target_audience": "Who this targets",
        "hook": "The emotional/curiosity hook"
    }},
    ...
]

IMPORTANT: Return EXACTLY {count} title objects in a JSON array."""

        try:
            response = self._generate_content_with_retry(prompt)
            result = self._extract_json(response.text)
            # Ensure we always return a list
            if isinstance(result, list):
                ok, error = self._validate_with_schema(result, BGS_SIMILAR_TITLES_SCHEMA)
                return result if ok else []
            elif isinstance(result, dict):
                wrapped = [result]
                ok, error = self._validate_with_schema(wrapped, BGS_SIMILAR_TITLES_SCHEMA)
                return wrapped if ok else []
            return []
        except Exception as e:
            print(f"[ERROR] Failed to generate similar titles: {e}")
            return []

    def generate_chapter_structure(self, title, context_data, language="pl"):
        """
        Generates a detailed chapter structure for a video title.
        """
        self._reset_runtime_stats()
        language = self._normalize_language(language)
        language_label = self._language_label(language)
        print(f"[CONTENT IDEAS] Generating chapter structure for: {title[:50]}...")
        
        prompt = f"""You are a world-class Video Script Architect.

=== VIDEO TITLE ===
{title}

=== CONTEXT FROM BUSINESS GROWTH STRATEGY ===
{json.dumps(context_data, indent=2, default=str)[:12000]}

=== YOUR TASK ===
Create a detailed chapter structure for this long-form YouTube video (15-30 min).

RULES:
1. Create 5-8 chapters
2. Each chapter should have a clear purpose and flow into the next
3. Include timing estimates
4. Chapter titles in {language_label}
5. Make the structure engaging - strong hook, build tension, provide value, CTA

=== OUTPUT FORMAT (JSON) ===
{{
    "total_duration_minutes": 20,
    "chapters": [
        {{
            "number": 1,
            "title": "Chapter title in {language_label}",
            "duration_minutes": 3,
            "purpose": "What this chapter achieves",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "transition": "How to transition to next chapter"
        }},
        // ... more chapters
    ],
    "hook_strategy": "Overall strategy for the video opening",
    "cta_strategy": "What action viewers should take after watching"
}}"""

        try:
            response = self._generate_content_with_retry(prompt)
            extracted = self._extract_json(response.text)
            ok, error = self._validate_with_schema(extracted, BGS_CHAPTER_STRUCTURE_SCHEMA)
            if not ok:
                return {"error": f"Schema validation failed: {error}", "chapters": []}
            return extracted
        except Exception as e:
            print(f"[ERROR] Failed to generate chapter structure: {e}")
            return {"error": str(e), "chapters": []}

    def generate_script_chapter(self, title, chapter, context_data, language="pl", previous_chapter_script=None):
        """
        Generates script for a single chapter with 2 options (A and B).
        Optionally receives previous chapter's selected script for continuity.
        """
        self._reset_runtime_stats()
        language = self._normalize_language(language)
        language_label = self._language_label(language)
        print(f"[CONTENT IDEAS] Generating script for chapter: {chapter.get('title', 'Unknown')[:40]}...")
        
        # Build continuity context if previous chapter script provided
        continuity_section = ""
        if previous_chapter_script:
            continuity_section = f"""
=== PREVIOUS CHAPTER (for continuity) ===
The user selected this script style for the previous chapter. 
Match the tone, energy, and stylistic approach only.
Do NOT recap or explicitly reference previous chapter/episode/part.
---
{previous_chapter_script[:2000]}
---
"""
        
        prompt = f"""You are a world-class Video Scriptwriter specializing in B2B content.

=== VIDEO TITLE ===
{title}

=== CHAPTER TO SCRIPT ===
Chapter {chapter.get('number', '?')}: {chapter.get('title', 'Untitled')}
Duration: {chapter.get('duration_minutes', 3)} minutes
Purpose: {chapter.get('purpose', 'N/A')}
Key Points: {json.dumps(chapter.get('key_points', []))}
{continuity_section}
=== CONTEXT ===
{json.dumps(context_data, indent=2, default=str)[:8000]}

=== YOUR TASK ===
Write TWO different script versions for this chapter:
- Option A: More direct and educational
- Option B: More storytelling and emotional

CRITICAL RULES:
1. Write ONLY the spoken text (what the founder/presenter says out loud)
2. Do NOT include ANY visual directions, B-ROLL suggestions, camera cues, or production notes
3. This is a PURE SPOKEN SCRIPT - no brackets, no visual descriptions
4. Write in {language_label}
5. Aim for ~{chapter.get('duration_minutes', 3) * 150} words per option
6. Treat this as one cohesive long YouTube script (single continuous video), not separate episodes
7. Never open with recap/meta phrases like "w poprzednim rozdziale", "w poprzednim odcinku", "in previous chapter/episode", "last chapter", "jak wcześniej mówiliśmy"
8. Do NOT mention chapter numbers, chapter names, episode labels, or "this chapter"
9. Continue naturally from prior context by advancing the argument immediately

=== OUTPUT FORMAT (JSON) ===
{{
    "chapter_number": {chapter.get('number', 1)},
    "chapter_title": "{chapter.get('title', 'Untitled')}",
    "option_a": {{
        "style": "Direct/Educational",
        "script": "Full spoken script text only - NO visual cues...",
        "word_count": 450
    }},
    "option_b": {{
        "style": "Storytelling/Emotional", 
        "script": "Full spoken script text only - NO visual cues...",
        "word_count": 450
    }}
}}"""

        try:
            response = self._generate_content_with_retry(prompt)
            extracted = self._extract_json(response.text)
            ok, error = self._validate_with_schema(extracted, BGS_SCRIPT_CHAPTER_SCHEMA)
            if not ok:
                return {"error": f"Schema validation failed: {error}"}
            return self._sanitize_script_options(extracted)
        except Exception as e:
            print(f"[ERROR] Failed to generate script chapter: {e}")
            return {"error": str(e)}

# Legacy alias for backward compatibility.
GamePlanProcessor = BusinessGrowthStrategyProcessor
