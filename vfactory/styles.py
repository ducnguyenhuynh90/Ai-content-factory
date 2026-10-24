"""Looks — the creative-director layer.

A Look bundles every taste decision that has to agree with every other one:
typography, palette, grade, texture, transitions, pacing, title motion, opening
and ending grammar, captions and sound. Mixing decisions across looks is how
edits start to feel "templated"; keeping them in one object keeps them coherent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace


@dataclass(frozen=True)
class Palette:
    bg: str = "#0B0B0C"          # card / end-card background
    fg: str = "#F4F1EA"          # primary type
    accent: str = "#E8B15A"      # one accent; never more than two
    muted: str = "#8A867E"       # secondary type, rules
    caption_hi: str = "#FFD84D"  # active caption word


@dataclass(frozen=True)
class Typography:
    display: str = "playfair"        # main title face
    display_weight: int | None = 500
    display_case: str = "upper"      # upper | title | as-is
    display_tracking: float = 0.12   # em; generous tracking on caps reads premium
    kicker: str = "montserrat"       # small overline above/below title
    kicker_weight: int | None = 500
    kicker_tracking: float = 0.42
    body: str = "inter"
    body_weight: int | None = 400
    caption: str = "inter"           # must be a static font (libass)
    caption_weight: int = 800


@dataclass(frozen=True)
class Look:
    name: str
    tagline: str
    palette: Palette = field(default_factory=Palette)
    type: Typography = field(default_factory=Typography)

    # --- picture ---------------------------------------------------------
    grade: str = ""                 # ffmpeg filter chain applied per segment
    halation: float = 0.0           # 0..1 highlight bloom
    vignette: float = 0.0           # 0..1
    grain: int = 0                  # luma grain strength (0..20)
    letterbox: float | None = None  # target aspect for bars, e.g. 2.39
    push_in: float = 0.0            # slow Ken Burns scale per shot (0.04 = 4%)

    # --- motion ----------------------------------------------------------
    title_anim: str = "tracking_reveal"
    lower_third_anim: str = "bar_wipe"
    endcard_layout: str = "center"
    transitions: tuple[str, ...] = ("cut", "cut", "dissolve")  # weighted vocabulary
    section_transition: str = "dip"  # between acts / into ending
    transition_dur: float = 0.6
    light_leaks: bool = False
    flash_on_hits: bool = False

    # --- pacing ----------------------------------------------------------
    min_shot: float = 2.0
    max_shot: float = 5.5
    beats_per_shot: tuple[int, ...] = (4, 4, 2)  # montage cutting on music
    cold_open: float = 3.0          # seconds of strongest moment before the title; 0 = none
    title_hold: float = 4.0
    endcard_hold: float = 5.0
    tail_fade: float = 1.2          # last shot fades to black/end card

    # --- captions --------------------------------------------------------
    caption_words: int = 3
    caption_case: str = "as-is"     # upper | as-is
    caption_size: float = 0.052     # fraction of frame height
    caption_karaoke: bool = True

    # --- sound -----------------------------------------------------------
    sfx: tuple[str, ...] = ("whoosh", "hit")  # which designed effects the look may use
    music_db: float = -16.0         # music bed level under nothing
    duck_db: float = 12.0           # how far music dips under speech

    def to_dict(self) -> dict:
        return asdict(self)

    def with_overrides(self, **kw) -> "Look":
        pal = kw.pop("palette", None)
        typ = kw.pop("type", None)
        look = replace(self, **kw)
        if pal:
            look = replace(look, palette=replace(look.palette, **pal))
        if typ:
            look = replace(look, type=replace(look.type, **typ))
        return look


LOOKS: dict[str, Look] = {}


def _add(look: Look) -> Look:
    LOOKS[look.name] = look
    return look


_add(Look(
    name="prestige",
    tagline="Prestige drama. Serif titles in open space, warm film stock, patience.",
    palette=Palette(bg="#0A0A0A", fg="#F2EDE4", accent="#D9A55B", muted="#8C857A", caption_hi="#F2D59B"),
    type=Typography(display="instrument-serif", display_weight=None, display_case="upper", display_tracking=0.16,
                    kicker="montserrat", kicker_weight=500, kicker_tracking=0.5, body="inter", caption="inter"),
    grade=("eq=contrast=1.04:saturation=0.86,"
           "colorbalance=rs=0.025:bs=-0.03:rm=0.02:bm=-0.015:rh=0.035:bh=-0.04,"
           "curves=all='0/0.035 0.25/0.225 0.75/0.775 1/0.955'"),
    halation=0.35, vignette=0.35, grain=7, letterbox=2.39, push_in=0.035,
    title_anim="tracking_reveal", lower_third_anim="hairline", endcard_layout="credits",
    transitions=("cut", "cut", "cut", "dissolve"), section_transition="dip", transition_dur=0.8,
    light_leaks=False, min_shot=3.0, max_shot=6.5, beats_per_shot=(8, 4, 4),
    cold_open=3.5, title_hold=4.5, endcard_hold=6.0, tail_fade=1.8,
    caption_words=5, caption_case="as-is", caption_karaoke=False,
    sfx=("hit",), music_db=-15.0, duck_db=13.0,
))

_add(Look(
    name="editorial",
    tagline="Swiss-clean product film. Bold grotesk, masked reveals, crisp neutral image.",
    palette=Palette(bg="#F5F5F2", fg="#111111", accent="#FF4D1F", muted="#6E6E6A", caption_hi="#FF4D1F"),
    type=Typography(display="inter-display", display_weight=800, display_case="as-is", display_tracking=-0.02,
                    kicker="inter", kicker_weight=600, kicker_tracking=0.18, body="inter", caption="inter"),
    grade="eq=contrast=1.06:saturation=1.04,curves=all='0/0 0.25/0.235 0.75/0.775 1/1'",
    halation=0.0, vignette=0.12, grain=0, letterbox=None, push_in=0.025,
    title_anim="mask_rise", lower_third_anim="bar_wipe", endcard_layout="center",
    transitions=("cut", "cut", "slide"), section_transition="wipe", transition_dur=0.45,
    min_shot=1.8, max_shot=4.0, beats_per_shot=(4, 2, 2), cold_open=2.5, title_hold=3.2, endcard_hold=4.5, tail_fade=0.8,
    caption_words=3, caption_case="as-is", caption_karaoke=True,
    sfx=("whoosh", "tick"), music_db=-16.0,
))

_add(Look(
    name="blockbuster",
    tagline="Trailer energy. Condensed caps that slam on the beat, teal-orange, flashes.",
    palette=Palette(bg="#050607", fg="#FFFFFF", accent="#FF9F1C", muted="#9AA3AB", caption_hi="#FF9F1C"),
    type=Typography(display="anton", display_weight=None, display_case="upper", display_tracking=0.04,
                    kicker="oswald", kicker_weight=500, kicker_tracking=0.45, body="oswald", caption="anton"),
    grade=("colorbalance=rs=-0.07:gs=-0.015:bs=0.09:rm=0.04:bm=-0.04:rh=0.09:gh=0.02:bh=-0.07,"
           "eq=contrast=1.14:saturation=1.08,curves=all='0/0 0.2/0.145 0.8/0.86 1/1'"),
    halation=0.25, vignette=0.45, grain=6, letterbox=2.39, push_in=0.05,
    title_anim="slam", lower_third_anim="bar_wipe", endcard_layout="center",
    transitions=("cut", "cut", "flash", "whip", "cut"), section_transition="flash", transition_dur=0.3,
    light_leaks=True, flash_on_hits=True,
    min_shot=1.0, max_shot=3.0, beats_per_shot=(4, 2, 2, 1), cold_open=2.5, title_hold=3.0, endcard_hold=4.5, tail_fade=0.6,
    caption_words=2, caption_case="upper", caption_size=0.06, caption_karaoke=True,
    sfx=("whoosh", "hit", "riser"), music_db=-13.0,
))

_add(Look(
    name="documentary",
    tagline="Observational doc. Typed mono titles, honest grade, informative lower thirds.",
    palette=Palette(bg="#101112", fg="#EDEDE8", accent="#7FD1B9", muted="#8D918F", caption_hi="#7FD1B9"),
    type=Typography(display="space-grotesk", display_weight=500, display_case="as-is", display_tracking=0.0,
                    kicker="jetbrains-mono", kicker_weight=500, kicker_tracking=0.2, body="jetbrains-mono", caption="inter"),
    grade="eq=saturation=0.82:contrast=1.03,colorbalance=bs=0.02:bm=0.01,curves=all='0/0.03 1/0.97'",
    halation=0.1, vignette=0.25, grain=5, letterbox=None, push_in=0.03,
    title_anim="type_on", lower_third_anim="hairline", endcard_layout="credits",
    transitions=("cut", "cut", "cut", "dissolve"), section_transition="dip", transition_dur=0.7,
    min_shot=2.5, max_shot=6.0, beats_per_shot=(8, 4), cold_open=3.0, title_hold=4.0, endcard_hold=5.5, tail_fade=1.4,
    caption_words=6, caption_case="as-is", caption_karaoke=False,
    sfx=("tick",), music_db=-18.0,
))

_add(Look(
    name="luxury",
    tagline="Fashion / luxury. Italic serif breathing in, creamy bloom, gold, slow dissolves.",
    palette=Palette(bg="#0E0C0A", fg="#F7F1E6", accent="#C9A86A", muted="#9C9283", caption_hi="#E9D3A1"),
    type=Typography(display="playfair-italic", display_weight=400, display_case="as-is", display_tracking=0.01,
                    kicker="montserrat", kicker_weight=400, kicker_tracking=0.6, body="montserrat", caption="dm-serif"),
    grade=("eq=saturation=0.9:brightness=0.015:contrast=0.98,"
           "colorbalance=rs=0.02:rh=0.05:gh=0.03:bh=-0.02,curves=all='0/0.05 0.5/0.53 1/0.98'"),
    halation=0.5, vignette=0.3, grain=4, letterbox=None, push_in=0.04,
    title_anim="serif_fade", lower_third_anim="hairline", endcard_layout="monogram",
    transitions=("dissolve", "cut", "dissolve"), section_transition="dip", transition_dur=1.0,
    light_leaks=True, min_shot=3.0, max_shot=6.0, beats_per_shot=(8, 4), cold_open=0.0,
    title_hold=4.5, endcard_hold=5.5, tail_fade=2.0,
    caption_words=5, caption_case="as-is", caption_karaoke=False,
    sfx=(), music_db=-14.0,
))

_add(Look(
    name="hype",
    tagline="Creator / social. Heavy grotesk, karaoke captions, punch zooms, saturated.",
    palette=Palette(bg="#0B0B0F", fg="#FFFFFF", accent="#C6FF3D", muted="#A1A1AA", caption_hi="#C6FF3D"),
    type=Typography(display="archivo-black", display_weight=None, display_case="upper", display_tracking=-0.01,
                    kicker="syne", kicker_weight=700, kicker_tracking=0.3, body="inter", caption="archivo-black"),
    grade="eq=contrast=1.1:saturation=1.25,curves=all='0/0 0.25/0.2 0.75/0.82 1/1',colorbalance=bs=0.03:rh=0.03",
    halation=0.15, vignette=0.2, grain=3, letterbox=None, push_in=0.06,
    title_anim="slam", lower_third_anim="bar_wipe", endcard_layout="center",
    transitions=("cut", "zoom", "cut", "whip"), section_transition="flash", transition_dur=0.3,
    flash_on_hits=True, min_shot=0.8, max_shot=2.5, beats_per_shot=(2, 2, 1), cold_open=2.0,
    title_hold=2.4, endcard_hold=3.5, tail_fade=0.5,
    caption_words=2, caption_case="upper", caption_size=0.065, caption_karaoke=True,
    sfx=("whoosh", "hit"), music_db=-13.0,
))


def get(name: str) -> Look:
    try:
        return LOOKS[name]
    except KeyError:
        raise KeyError(f"unknown look '{name}'. Available: {', '.join(LOOKS)}") from None


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
