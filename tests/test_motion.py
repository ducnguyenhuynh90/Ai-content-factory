import numpy as np
import pytest

from vfactory import fonts, styles
from vfactory.motion.cards import EndCard, LightLeak, LowerThird
from vfactory.motion.core import Glyphs, TextStyle, fit_text
from vfactory.motion.titles import TITLE_ANIMS, make_title


def test_bundled_fonts_exist_and_load():
    for name, path in fonts.available().items():
        f = fonts.get(name, 40, 700)
        assert f.getlength("Hello") > 0, name


def test_fit_text_respects_width():
    st = TextStyle("anton", 300)
    lines, st2 = fit_text("an extremely long title that cannot possibly fit", st, 800, max_lines=2)
    assert len(lines) <= 2
    assert all(Glyphs(l, st2).width <= 800 for l in lines)


@pytest.mark.parametrize("anim", list(TITLE_ANIMS))
@pytest.mark.parametrize("look", ["prestige", "hype"])
def test_titles_appear_and_leave(anim, look):
    a = make_title(styles.get(look), 640, 360, 30, 4.0, "The Long Road Home", kicker="Kicker", subtitle="Sub", anim=anim)
    mid = np.asarray(a.frame(a.intro + 0.3))[..., 3]
    end = np.asarray(a.frame(a.duration - 1 / 30))[..., 3]
    assert mid.max() == 255 or mid.mean() > 2, "title should be visible after its intro"
    assert end.mean() < mid.mean(), "title should be leaving at the end"
    assert a.hits and all(0 <= h < a.duration for h in a.hits)


def test_overlay_ink_flips_on_footage():
    a = make_title(styles.get("editorial"), 640, 360, 30, 4.0, "Title")
    assert a.pal.fg == "#FFFFFF"
    b = make_title(styles.get("editorial"), 640, 360, 30, 4.0, "Title", card=True)
    assert b.pal.fg == styles.get("editorial").palette.fg


def test_cards_render():
    look = styles.get("luxury")
    lt = LowerThird(look, 640, 360, 30, 3.0, "Mai Tran", "Director")
    assert np.asarray(lt.frame(1.5))[..., 3].max() > 0
    ec = EndCard(look, 640, 360, 30, 5.0, "Title", tagline="t", cta="Subscribe", credits=[["Directed by", "X"]])
    assert ec.frame(4.0).size == (640, 360)
    leak = LightLeak(640, 360, 30, 1.0)
    assert np.asarray(leak.frame(0.5))[..., 3].max() > 0
    assert np.asarray(leak.frame(0.0))[..., 3].max() == 0
