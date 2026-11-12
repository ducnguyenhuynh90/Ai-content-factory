"""Canned replies for `--provider fake`: a dry run of the whole pipeline with no model and no network.

The content is a short demo of the pilot topic ("Tư duy từ gốc") in the sticker format. Its facts mirror the pilot's
research pack (Wired 2012, TED 2013, Vance 2015); it exists to exercise the pipeline, not to be published.
"""

from __future__ import annotations

import copy

from .config import SIGN_OFF

END = SIGN_OFF  # the cached series sign-off
SERIES = "Khung tư duy · Tập mới"

IDEA = {
    "framework": "Tư duy từ gốc", "framework_en": "First principles thinking",
    "storylines": [
        {"logline": "Linh muốn mở quán cà phê nhưng tin rằng mở quán là phải tốn rất nhiều tiền.",
         "protagonist": {"name": "Linh", "age": 27, "job": "kế toán, tối bán hàng online", "place": "Quận 7, TP.HCM",
                         "want": "mở một quán cà phê nhỏ", "flaw": "tin giá 'xưa nay vẫn thế'"},
         "dilemma": "so giá với các quán khác và cứ hoãn mãi", "real_story": "Musk hỏi tên lửa làm từ gì (2001–2002)",
         "why_it_fits": "cùng một câu hỏi: cái giá này làm từ gì?"},
        {"logline": "Anh Tùng chạy Grab tính mua xe mới vì ai cũng mua.",
         "protagonist": {"name": "Tùng", "age": 34, "job": "tài xế công nghệ", "place": "Hà Nội",
                         "want": "tăng thu nhập", "flaw": "làm theo số đông"},
         "dilemma": "vay mua xe mới", "real_story": "Malcom McLean và thùng container (1956)",
         "why_it_fits": "tách chi phí thật khỏi thói quen"},
        {"logline": "Cô Mai định đóng khóa học đắt nhất vì nghĩ đắt là tốt.",
         "protagonist": {"name": "Mai", "age": 31, "job": "chủ quán cà phê", "place": "Đà Lạt",
                         "want": "học pha chế bài bản", "flaw": "đắt là tốt"},
         "dilemma": "chọn khóa học", "real_story": "Musk và bảng tính vật liệu",
         "why_it_fits": "tách tới nguyên liệu"}],
    "chosen": 0, "why_chosen": "Misconception rõ nhất, câu chuyện thật có nguồn của chính người trong cuộc.",
    "metaphor": {"object": "nồi nước dùng ninh từ xương", "icon": "pot",
                 "shows": "biết trong nồi có gì, mỗi thứ góp gì và giá bao nhiêu",
                 "omits": "ninh xương chậm và tốn sức; có món phải theo đúng công thức"},
    "misconception": "Thứ gì đắt là vì nó vốn đắt; ai cũng trả thì giá ấy đúng.",
    "working_title": "Tư duy từ gốc: ly cà phê và quả tên lửa",
    "audience": "người trẻ Việt đi làm, hay quyết định mua gì, làm gì",
}

RESEARCH = {
    "sources": [
        {"id": "wired2012", "cite": "Chris Anderson, 'Elon Musk's Mission to Mars', Wired, October 2012",
         "url": "https://www.wired.com/2012/10/ff-elon-musk-qa/", "kind": "primary", "from_notes": False},
        {"id": "ted2013", "cite": "Elon Musk with Chris Anderson, TED 2013", "kind": "primary", "from_notes": False},
        {"id": "vance2015", "cite": "Ashlee Vance, Elon Musk (2015)", "kind": "secondary", "from_notes": False},
        {"id": "minhhoa", "cite": "Số minh họa của kênh", "kind": "illustration", "from_notes": False}],
    "claims": [
        {"id": "A5", "claim": "Musk went to Russia three times in late 2001 and 2002 to buy rockets",
         "sources": ["wired2012", "vance2015"], "certainty": "attributed", "verified": False, "use": "hedge",
         "say": "theo lời Musk, ông sang Nga ba lần"},
        {"id": "A6", "claim": "Quoted price", "value": "$15–20 M each (Musk's own range)", "sources": ["wired2012"],
         "certainty": "disputed", "verified": False, "use": "hedge",
         "say": "theo lời ông, khoảng mười lăm đến hai mươi triệu đô mỗi quả"},
        {"id": "A9", "claim": "Materials ~2% of the typical rocket price (his estimate)", "sources": ["wired2012"],
         "certainty": "estimate", "verified": False, "use": "hedge",
         "say": "theo ước tính của ông, khoảng hai phần trăm giá một tên lửa thông thường"},
        {"id": "Q1", "claim": "First principles vs reasoning by analogy (definition)", "sources": ["ted2013"],
         "certainty": "established", "verified": False, "use": "voice", "say": "quy về sự thật nền tảng, rồi suy luận lên"},
        {"id": "X1", "claim": "Coffee cost breakdown", "value": "55k vs ~10k ingredients", "sources": ["minhhoa"],
         "certainty": "estimate", "verified": False, "use": "screen", "say": "số minh họa"}],
    "myths": [{"myth": "SpaceX bán tên lửa với giá bằng hai phần trăm", "truth": "2% là vật liệu so với giá thường thấy",
               "sources": ["wired2012"]}],
    "open_items": ["Mở Wired 2012 và kiểm lại câu 'around 2 percent of the typical price'"],
    "neutral_line": "Musk là người gây nhiều tranh cãi; ở đây mình chỉ kể một câu chuyện kỹ thuật.",
}

SPINE = {
    "acts": [
        {"act": "ngay_xua", "summary": "Linh làm kế toán, tối bán hàng online, mơ mở quán cà phê.",
         "protagonist": "háo hức nhưng ngại", "real_story": "", "claims": [], "seconds": 30},
        {"act": "cho_den_mot_ngay", "summary": "Một ly cà phê năm mươi lăm nghìn khiến Linh tính lại.",
         "protagonist": "tò mò", "real_story": "", "claims": ["X1"], "seconds": 20},
        {"act": "vi_vay", "summary": "Cô so giá với các quán khác, càng so càng nản, cứ hoãn mãi.",
         "protagonist": "nản", "real_story": "", "claims": [], "seconds": 40},
        {"act": "cho_den_khi", "summary": "Câu chuyện Musk hỏi tên lửa làm từ gì.", "protagonist": "ngạc nhiên",
         "real_story": "Nga 2001–2002, bảng tính vật liệu", "claims": ["A5", "A6", "A9", "Q1"], "seconds": 80},
        {"act": "tu_do", "summary": "Linh áp dụng ba việc, thử bán mang đi ở góc nhỏ.", "protagonist": "tự tin",
         "real_story": "", "claims": ["X1"], "seconds": 70},
        {"act": "va_gio", "summary": "Giới hạn của ẩn dụ, câu hỏi cho người xem, lời mời bình luận.",
         "protagonist": "bình thản", "real_story": "", "claims": [], "seconds": 50}],
    "want": "mở quán cà phê nhỏ", "flaw": "tin giá xưa nay vẫn thế", "stakes": "giấc mơ cứ hoãn mãi",
    "misconception": "đắt là vì vốn đắt", "turning_point": "câu hỏi tên lửa làm từ gì",
    "moves": [{"name": "Tách tới nguyên liệu", "line": "Thứ này làm từ gì, mỗi phần giá bao nhiêu?"},
              {"name": "Tách luật khỏi thói quen", "line": "Giới hạn thật hay chỉ là xưa nay vẫn thế?"},
              {"name": "Lắp lại, để thực tế chấm", "line": "Dựng phương án nhỏ rồi thử."}],
    "worked_example": "ly cà phê: nguyên liệu khoảng mười nghìn trên năm mươi lăm nghìn (minh họa)",
    "metaphor_limit": "ninh xương chậm, không ai làm vậy cho mọi bữa",
    "viewer_question": "khóa học báo giá rất cao: câu hỏi từ gốc đầu tiên là gì?",
    "pixar_checks": {"want_and_flaw": "muốn mở quán; tin giá vốn thế", "stakes_felt": "giấc mơ bị hoãn",
                     "coincidence_only_into_trouble": "ly cà phê đắt chỉ đẩy cô vào câu hỏi",
                     "ending_earned_by_choice": "cô tự thử bán mang đi"},
}

CAST = [{"id": "linh", "name": "Linh", "role": "protagonist",
         "look": {"skin": "#F1C9A5", "hair": "bob", "hair_color": "#2B2321", "shirt": "#E77A5F", "pants": "#3D4B63"}},
        {"id": "musk", "name": "Elon Musk", "role": "real person", "real": True, "tag": "Elon Musk",
         "look": {"shirt": "#5B6B7F"}}]


def stage(set_, x=0.35, expression="neutral", action="idle", cues=None, props=None, bubble=None, caption=None,
          transition="slide"):
    v = {"type": "stage", "set": set_,
         "characters": [{"id": "linh", "x": x, "expression": expression, "action": action, "cues": cues or []}],
         "transition": transition}
    if props:
        v["props"] = props
    if bubble:
        v["bubble"] = bubble
    if caption:
        v["caption"] = caption
    return v


BEATS = [
    {"id": "h1", "act": "hook", "spine": "cho_den_mot_ngay", "sources": ["minhhoa"], "certainty": "estimate",
     "narration": "Một ly cà phê năm mươi lăm nghìn. Nguyên liệu chỉ hơn mười nghìn. Phần còn lại là gì?",
     "visual": stage("cafe", expression="thinking", action="idle",
                     props=[{"icon": "glass", "x": 0.7, "y": 0.6, "cue": "một ly"}],
                     bubble={"who": "linh", "text": "Phần còn lại là gì?", "cue": "phần còn"}, transition="cut")},
    {"id": "h2", "act": "context", "spine": "cho_den_mot_ngay",
     "narration": "Nhân vật hư cấu, chuyện có thật: câu hỏi ấy từng làm đổi cả một ngành tên lửa. Và nó bắt đầu từ một cách nghĩ rất cũ.",
     "visual": {"type": "icon", "icon": "rocket", "kicker": "Nhân vật hư cấu · chuyện có thật",
                "line": "Một câu hỏi, cả ngành tên lửa", "line_cue": "câu hỏi", "action": "bay lên"}},
    {"id": "t0", "act": "context", "spine": "cho_den_mot_ngay", "narration": "",
     "visual": {"type": "title", "title": "Tư duy từ gốc", "kicker": SERIES, "hold": 3.0}},
    {"id": "b01", "act": "story", "spine": "ngay_xua",
     "narration": "Mỗi sáng, Linh làm kế toán ở quận Bảy. Tối về, cô chạy thêm đơn hàng online. Cô mơ một quán cà phê nhỏ của riêng mình.",
     "visual": stage("office", x=0.4, expression="happy", action="talk",
                     props=[{"icon": "coin", "x": 0.75, "y": 0.55, "cue": "đơn hàng"}], caption="Mơ một quán nhỏ")},
    {"id": "b02", "act": "misconception", "spine": "vi_vay",
     "narration": "Ai cũng bảo: mở quán là phải tốn rất nhiều tiền, giá xưa nay vẫn thế. Linh tin vậy, nên cô cứ hoãn mãi.",
     "visual": stage("cafe", expression="worried", action="shrug",
                     cues=[{"cue": "hoãn", "expression": "sad", "action": "sit"}],
                     bubble={"who": "linh", "text": "Phải tốn rất nhiều tiền", "cue": "linh tin"})},
    {"id": "b03", "act": "complication", "spine": "vi_vay",
     "narration": "Vì vậy cô so giá với các quán khác. Mỗi lần so, con số lại cao hơn. Làm giống người khác, chỉ sửa chút ít.",
     "visual": {"type": "icon", "icon": "packet", "concept": "loi_mon", "kicker": "Lối mòn",
                "line": "Làm giống người khác", "line_cue": "làm giống", "action": "lặp lại"}},
    {"id": "b04", "act": "story", "spine": "cho_den_khi", "sources": ["wired2012", "vance2015"], "certainty": "attributed",
     "narration": "Cho đến khi cô đọc lại một câu chuyện. Cuối năm hai nghìn lẻ một, theo lời Elon Musk, ông sang Nga hỏi mua tên lửa, được cho là ba lần.",
     "visual": {"type": "portrait", "name": "Elon Musk", "initials": "EM", "role": "Nga · 2001–2002"}},
    {"id": "b05", "act": "story", "spine": "cho_den_khi", "sources": ["wired2012"], "certainty": "disputed",
     "narration": "Giá ông kể lại là khoảng mười lăm đến hai mươi triệu đô mỗi quả. Nguồn khác ghi số khác.",
     "visual": {"type": "stat", "value": 20, "from": 15, "suffix": " triệu $", "label": "mỗi quả, theo lời Musk",
                "cue": "hai mươi"}},
    {"id": "b06", "act": "turn", "spine": "cho_den_khi", "sources": ["wired2012"], "certainty": "estimate",
     "narration": "Ông hỏi: tên lửa làm từ gì, vật liệu giá bao nhiêu? Theo ước tính của ông, chỉ khoảng hai phần trăm giá một tên lửa thông thường.",
     "visual": {"type": "icon", "icon": "pot", "concept": "tu_goc", "kicker": "Ước tính của Musk",
                "line": "Vật liệu khoảng 2%", "line_cue": "hai phần trăm", "action": "mở nắp"}},
    {"id": "b07", "act": "turn", "spine": "cho_den_khi", "sources": ["ted2013"],
     "narration": "Musk gọi đó là first principles. Mình gọi là tư duy từ gốc: như nồi nước dùng ninh từ xương, biết từng thứ trong nồi.",
     "visual": {"type": "icon", "icon": "pot", "concept": "tu_goc", "kicker": "Tư duy từ gốc",
                "line": "Biết từng thứ trong nồi", "line_cue": "biết từng", "action": "bốc hơi", "steam": True}},
    {"id": "b08", "act": "principle", "spine": "tu_do",
     "narration": "Từ đó, Linh làm ba việc. Thứ nhất, tách tới nguyên liệu: một ly cà phê làm từ gì, mỗi thứ giá bao nhiêu?",
     "visual": stage("cafe", expression="thinking", action="point",
                     props=[{"icon": "glass", "x": 0.7, "y": 0.6, "cue": "một ly"}], caption="Tách tới nguyên liệu")},
    {"id": "b09", "act": "principle", "spine": "tu_do",
     "narration": "Thứ hai, tách luật khỏi thói quen. Mặt bằng to là bắt buộc, hay chỉ là xưa nay vẫn thế?",
     "visual": stage("street", expression="thinking", action="idle",
                     cues=[{"cue": "hay chỉ", "expression": "surprised", "action": "jump"}],
                     caption="Tách luật khỏi thói quen", transition="whip")},
    {"id": "b10", "act": "principle", "spine": "tu_do", "sources": ["minhhoa"], "certainty": "estimate",
     "narration": "Thứ ba, lắp lại rồi để thực tế chấm. Cô thử bán cà phê mang đi ở một góc nhỏ, chi phí đầu chỉ bằng một phần nhỏ, số minh họa thôi.",
     "visual": stage("street", x=0.3, expression="happy", action="wave",
                     props=[{"icon": "store", "x": 0.7, "y": 0.55, "cue": "góc nhỏ"}], caption="Lắp lại, để thực tế chấm")},
    {"id": "b11", "act": "complication", "spine": "va_gio",
     "narration": "Nhưng nồi xương cũng có giới hạn: ninh cả đêm, không ai làm vậy cho mọi bữa. Có việc cứ theo công thức là đúng.",
     "visual": {"type": "icon", "icon": "pot", "concept": "tu_goc", "kicker": "Chỗ ẩn dụ dừng lại",
                "line": "Ninh chậm, tốn sức", "line_cue": "ninh cả", "action": "nguội dần"}},
    {"id": "b12", "act": "question", "spine": "va_gio",
     "narration": "Giờ thử nhé. Một khóa học báo giá rất cao. Câu hỏi từ gốc đầu tiên bạn nên hỏi là gì?",
     "visual": {"type": "question", "question": "Khóa học báo giá rất cao. Hỏi gì trước?",
                "choices": ["Ai cũng học, chắc đáng", "Khóa này gồm những gì?", "Có giảm giá không?"],
                "answer": "B", "think_seconds": 5}},
    {"id": "b13", "act": "recap", "spine": "va_gio",
     "narration": "Đáp án là B. Ba việc: tách tới nguyên liệu, tách luật khỏi thói quen, lắp lại rồi để thực tế chấm.",
     "visual": {"type": "list", "items": ["Tách tới nguyên liệu", "Tách luật khỏi thói quen", "Lắp lại, để thực tế chấm"],
                "check": True, "icon": "checklist"}},
    {"id": "b14", "act": "close", "spine": "va_gio",
     "narration": "Giờ Linh vẫn mua cà phê. Nhưng cô biết mình trả cho phần nào. Trước một cái giá hiển nhiên, hãy hỏi: trong nồi này có gì?",
     "visual": stage("cafe", expression="happy", action="idle",
                     bubble={"who": "linh", "text": "Trong nồi này có gì?", "cue": "trong nồi"})},
    {"id": "end", "act": "close", "spine": "va_gio", "narration": END,
     "visual": {"type": "end", "kicker": SERIES, "title": "Tư duy từ gốc", "ask": "Bạn muốn tập sau về khung tư duy nào?",
                "ask_hint": "Tư duy bậc hai · vòng tròn năng lực · chi phí cơ hội", "ask_cue": "còn bạn",
                "sources_line": "Nguồn: Wired (2012) · TED (2013) · Vance (2015) · xem mô tả", "sources_cue": "còn bạn",
                "disclaimer": "Nội dung giáo dục; nhân vật hư cấu, câu chuyện thật kể lại từ nguồn công khai."}},
]

YOUTUBE = {"title": "Tư duy từ gốc: một ly cà phê và một quả tên lửa",
           "thumbnail_text": "55 nghìn một ly. Nguyên liệu bao nhiêu?",
           "description": "Nhân vật hư cấu, chuyện có thật. Nguồn: Wired 2012 (Chris Anderson) · TED 2013 · Vance 2015.",
           "chapters": ["Ly cà phê", "Lối mòn", "Tên lửa", "Ba việc", "Giới hạn"], "tags": ["tư duy từ gốc"]}

LESSON = {
    "meta": {"series": SERIES, "title": "Tư duy từ gốc", "subtitle": "First principles — ly cà phê và quả tên lửa",
             "topic": "books", "angle": "concept", "lang": "vi", "style": "sticker", "aspect": "16:9",
             "target_minutes": [2, 6], "voice": "omnivoice:male, middle-aged, very low pitch", "voice_seed": 99,
             "speed": 0.88, "music": "chill", "captions": True,
             "disclaimer": "Nội dung giáo dục; nhân vật hư cấu, câu chuyện thật kể lại từ nguồn công khai.",
             "learning_goals": ["Tách một cái giá thường ngày theo ba bước"],
             "cast": CAST,
             "concepts": [
                 {"id": "tu_goc", "visual": "pot", "color": "a", "shows": "biết trong nồi có gì và giá bao nhiêu",
                  "omits": "chậm, tốn sức; có món phải theo công thức"},
                 {"id": "loi_mon", "visual": "packet", "color": "b", "shows": "làm theo hướng dẫn có sẵn",
                  "omits": "đi theo lối mòn thường đúng và tiết kiệm sức"}],
             "brief": {"target_viewer": "người trẻ Việt đi làm", "format": "chuyện đời thường + chuyện thật, sticker",
                       "central_question": "cái giá ai cũng trả có hợp lý không?",
                       "transformation": "biết tách một cái giá thành nguyên liệu",
                       "discovery_goal": "tìm kiếm 'tư duy từ gốc'",
                       "primary_conversion": "comment answering the end-card question",
                       "share_recipient": "một người bạn sắp trả một khoản lớn vì ai cũng trả",
                       "evidence": "Wired 2012, TED 2013, Vance 2015", "constraints": "demo của FakeProvider"},
             "youtube": YOUTUBE},
    "sources": [{"id": s["id"], "cite": s["cite"], **({"url": s["url"]} if s.get("url") else {})}
                for s in RESEARCH["sources"]],
    "principles": [{"name": m["name"], "line": m["line"]} for m in SPINE["moves"]],
    "beats": BEATS,
    "pronounce": {},
}


def beat_sheet() -> dict:
    out = []
    for b in BEATS:
        v = b["visual"]
        thread = "card" if v["type"] in ("title", "end") else ("fiction" if v["type"] == "stage" else "real")
        out.append({"id": b["id"], "spine": b["spine"], "act": b["act"], "thread": thread, "purpose": b["act"],
                    "narration_draft": b["narration"], "visual_idea": v["type"], "set": v.get("set", ""),
                    "characters": ["linh"] if v["type"] == "stage" else [],
                    "claims": [], "seconds": 3.0 if not b["narration"] else 14.0})
    out[-1]["seconds"] = 8.0
    sheet_total = sum(x["seconds"] for x in out)
    for x in out:  # spread to a ~4-minute plan
        x["seconds"] = round(x["seconds"] * 240 / sheet_total, 1)
    return {"beats": out, "cast": [{"id": c["id"], "name": c["name"], "role": c["role"], "real": bool(c.get("real"))}
                                   for c in CAST]}


CRITIQUE = {"verdict": "revise",
            "pixar_checks": SPINE["pixar_checks"],
            "issues": [{"beat": "b14", "rule": "screen", "problem": "the close has no caption for muted viewers",
                        "fix": "add the key question as a caption", "severity": "should"}],
            "ops": [{"op": "add", "path": "/beats/@b14/visual/caption", "value_json": "\"Trong nồi này có gì?\"",
                     "why": "muted viewers"}]}

REVIEW = {"verdict": "pass", "seen": "(dry run: no frames)", "issues": []}
FIX = {"summary": "nothing to fix", "ops": [], "needs_human": []}
PACKAGE = {"title": "Tư duy từ gốc: một ly cà phê và một quả tên lửa",
           "thumbnail_text": "55 nghìn một ly. Nguyên liệu bao nhiêu?",
           "description": ("Linh (nhân vật hư cấu) tính lại một ly cà phê, và một câu chuyện thật về tên lửa giúp cô nghĩ "
                           "từ gốc. Theo lời Musk, giá được báo khoảng 15–20 triệu đô mỗi quả; 2% là ước tính của ông về "
                           "vật liệu so với giá thường thấy. Số ly cà phê là số minh họa.\n\n"
                           "Nguồn: Chris Anderson, Wired (2012) https://www.wired.com/2012/10/ff-elon-musk-qa/ · "
                           "TED (2013) · Ashlee Vance, Elon Musk (2015) · Số minh họa của kênh.\n\n"
                           "Nội dung giáo dục; nhân vật hư cấu, câu chuyện thật kể lại từ nguồn công khai."),
           "chapters": ["Ly cà phê", "Lối mòn", "Tên lửa", "Ba việc", "Chỗ ẩn dụ dừng lại", "Câu hỏi cho bạn"],
           "tags": ["tư duy từ gốc", "first principles", "khung tư duy", "Elon Musk", "SpaceX", "tư duy", "kỹ năng tư duy",
                    "ra quyết định", "tiêu dùng thông minh", "mở quán cà phê", "first principles thinking",
                    "chuyện đời thường"],
           "pinned_comment": "Bạn muốn tập sau về khung tư duy nào?"}


def demo_script() -> dict:
    """{stage: [reply, ...]} for FakeProvider (deep copies, so a run can't mutate the fixture)."""
    return copy.deepcopy({"idea": [IDEA], "research": [RESEARCH], "spine": [SPINE], "beats": [beat_sheet()],
                          "lesson": [LESSON], "critique": [CRITIQUE], "gate": [REVIEW], "fix": [FIX],
                          "package": [PACKAGE]})
