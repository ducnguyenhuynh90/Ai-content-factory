"""JSON schemas for every model stage's output (checked by jsonutil.validate; closed ones are also sent to providers as
structured-output constraints). Constraint keywords such as maxLength are checked client-side only."""

from __future__ import annotations

from .patch import OPS_SCHEMA
from .rules import SPINE

S = {"type": "string"}
S1 = {"type": "string", "minLength": 1}
STRS = {"type": "array", "items": S}
CERTAINTY = {"type": "string", "enum": ["established", "attributed", "disputed", "estimate"]}


def obj(props: dict, required=None, closed=True) -> dict:
    return {"type": "object", "properties": props, "required": list(required if required is not None else props),
            "additionalProperties": not closed}


PERSON = obj({"name": S1, "age": {"type": "integer", "minimum": 12, "maximum": 90}, "job": S1, "place": S1,
              "want": S1, "flaw": S1})

IDEA = obj({
    "framework": S1,                       # the thinking framework / lesson, in Vietnamese
    "framework_en": S,
    "storylines": {"type": "array", "minItems": 3, "maxItems": 3, "items": obj({
        "logline": S1, "protagonist": PERSON, "dilemma": S1, "real_story": S1, "why_it_fits": S1})},
    "chosen": {"type": "integer", "minimum": 0, "maximum": 2},
    "why_chosen": S1,
    "metaphor": obj({"object": S1, "icon": S, "shows": S1, "omits": S1}),
    "misconception": S1,
    "working_title": {"type": "string", "minLength": 1, "maxLength": 65},
    "audience": S1,
})

SOURCE = obj({"id": {"type": "string", "pattern": r"^[a-z0-9_]+$"}, "cite": S1, "url": S,
              "kind": {"type": "string", "enum": ["primary", "secondary", "notes", "illustration"]},
              "from_notes": {"type": "boolean"}}, required=["id", "cite", "kind", "from_notes"])

RESEARCH = obj({
    "claims": {"type": "array", "minItems": 3, "items": obj({
        "id": {"type": "string", "pattern": r"^[A-Za-z0-9_]+$"},
        "claim": S1, "value": S, "sources": {"type": "array", "minItems": 1, "items": S1},
        "certainty": CERTAINTY,
        "verified": {"type": "boolean"},     # true only when a human note / provided document backs it
        "use": {"type": "string", "enum": ["voice", "screen", "hedge", "cut"]},
        "say": S,                             # how to say it in Vietnamese, hedged where needed
    }, required=["id", "claim", "sources", "certainty", "verified", "use"])},
    "sources": {"type": "array", "minItems": 1, "items": SOURCE},
    "myths": {"type": "array", "items": obj({"myth": S1, "truth": S1, "sources": STRS})},
    "open_items": STRS,                       # what a human must verify in a browser before the voice is locked
    "neutral_line": S,                        # one neutral sentence if the real person is controversial
})

SPINE_ACT = obj({"act": {"type": "string", "enum": list(SPINE)}, "summary": S1, "protagonist": S1,
                 "real_story": S, "claims": STRS, "seconds": {"type": "number", "minimum": 5, "maximum": 120}})
SPINE_SCHEMA = obj({
    "acts": {"type": "array", "minItems": 6, "maxItems": 6, "items": SPINE_ACT},
    "want": S1, "flaw": S1, "stakes": S1, "misconception": S1, "turning_point": S1,
    "moves": {"type": "array", "minItems": 3, "maxItems": 3, "items": obj({"name": S1, "line": S1})},
    "worked_example": S1, "metaphor_limit": S1, "viewer_question": S1,
    "pixar_checks": obj({"want_and_flaw": S1, "stakes_felt": S1, "coincidence_only_into_trouble": S1,
                         "ending_earned_by_choice": S1}),
})

BEAT = obj({
    "id": {"type": "string", "pattern": r"^[a-z0-9_]+$"},
    "spine": {"type": "string", "enum": list(SPINE)},
    "act": {"type": "string", "enum": ["hook", "context", "story", "misconception", "complication", "turn", "principle",
                                       "example", "question", "recap", "close"]},
    "thread": {"type": "string", "enum": ["fiction", "real", "both", "card"]},
    "purpose": S1, "narration_draft": S, "visual_idea": S1,
    "set": S, "characters": STRS, "claims": STRS, "seconds": {"type": "number", "minimum": 0, "maximum": 40},
}, required=["id", "spine", "act", "thread", "purpose", "narration_draft", "visual_idea", "claims", "seconds"])
BEATS = obj({"beats": {"type": "array", "minItems": 12, "maxItems": 40, "items": BEAT},
             "cast": {"type": "array", "minItems": 1, "items": obj({"id": S1, "name": S1, "role": S1,
                                                                    "real": {"type": "boolean"}}, required=["id", "name", "role"])}})

# lesson.json: open (visuals carry many optional fields), so prompt-instructed JSON + validation, never constrained
LESSON = {
    "type": "object",
    "required": ["meta", "sources", "principles", "beats"],
    "properties": {
        "meta": {"type": "object", "required": ["series", "title", "lang", "style", "cast", "aspect", "target_minutes",
                                                "concepts", "brief", "youtube"],
                 "properties": {
                     "style": {"const": "sticker"}, "lang": {"const": "vi"},
                     "cast": {"type": "array", "minItems": 1, "items": {
                         "type": "object", "required": ["id", "name", "look", "role"],
                         "properties": {"id": S1, "name": S1, "role": S1, "look": {"type": "object"},
                                        "real": {"type": "boolean"}, "name_tag": S}}},
                     "concepts": {"type": "array", "items": {"type": "object", "required": ["id", "visual"]}},
                     "youtube": {"type": "object"}, "brief": {"type": "object"},
                 }},
        "sources": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["id", "cite"]}},
        "principles": {"type": "array", "minItems": 2, "maxItems": 4,
                       "items": {"type": "object", "required": ["name", "line"]}},
        "beats": {"type": "array", "minItems": 12, "items": {
            "type": "object", "required": ["id", "act", "spine", "narration", "visual"],
            "properties": {"id": S1, "narration": S, "visual": {"type": "object", "required": ["type"]},
                           "sources": STRS, "certainty": CERTAINTY}}},
        "pronounce": {"type": "object"},
    },
}

ISSUE = obj({"beat": S, "rule": S, "problem": S1, "fix": S1, "severity": {"type": "string", "enum": ["must", "should"]}},
            required=["beat", "problem", "fix", "severity"])
CRITIQUE = obj({
    "verdict": {"type": "string", "enum": ["pass", "revise"]},
    "pixar_checks": obj({"want_and_flaw": S1, "stakes_felt": S1, "coincidence_only_into_trouble": S1,
                         "ending_earned_by_choice": S1}),
    "issues": {"type": "array", "items": ISSUE},
    "ops": OPS_SCHEMA,
})

REVIEW = obj({
    "verdict": {"type": "string", "enum": ["pass", "revise", "block"]},
    "seen": S1,                              # what the reviewer actually saw in the frames (forces looking)
    "scores": obj({k: {"type": "integer", "minimum": 0, "maximum": 5} for k in "ABCDEFGHIJKL"}),
    "issues": {"type": "array", "items": ISSUE},
}, required=["verdict", "seen", "issues"])

FIX = obj({"summary": S1, "ops": OPS_SCHEMA, "needs_human": STRS})

PACKAGE = obj({
    "title": {"type": "string", "minLength": 10, "maxLength": 65},
    "thumbnail_text": S1,
    "description": S1,
    "chapters": STRS,
    "tags": {"type": "array", "minItems": 12, "maxItems": 15, "items": S1},
    "pinned_comment": S,
})

BY_STAGE = {"idea": IDEA, "research": RESEARCH, "spine": SPINE_SCHEMA, "beats": BEATS, "lesson": LESSON,
            "critique": CRITIQUE, "gate": REVIEW, "fix": FIX, "package": PACKAGE}
