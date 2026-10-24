import time

from vfactory import trends

NOW = time.time()


def _reddit():
    return {"data": {"children": [
        {"data": {"title": "Sora 3 one-take video editing workflow", "permalink": "/r/editors/1", "created_utc": NOW - 2 * 86400,
                  "score": 5400, "num_comments": 800, "author": "a", "subreddit": "editors"}},
        {"data": {"title": "How do I export in Premiere?", "permalink": "/r/editors/2", "created_utc": NOW - 3 * 86400,
                  "score": 3, "num_comments": 2, "author": "b", "subreddit": "editors"}},
        {"data": {"title": "Old thread", "permalink": "/r/editors/3", "created_utc": NOW - 90 * 86400,
                  "score": 99999, "num_comments": 1, "author": "c", "subreddit": "editors"}},
    ]}}


def _hn():
    return {"hits": [{"title": "Sora 3 one-take editing is here", "url": "https://example.com/sora3", "created_at_i": int(NOW - 86400),
                      "points": 640, "num_comments": 300, "author": "d", "objectID": "42"},
                     {"title": "Show HN: a terminal spreadsheet", "url": "https://example.com/sheet", "created_at_i": int(NOW - 86400),
                      "points": 20, "num_comments": 4, "author": "e", "objectID": "43"}]}


def test_parsers_and_window():
    r = trends.parse_reddit(_reddit(), 30)
    assert len(r) == 2  # the 90-day-old post is outside the window
    h = trends.parse_hn(_hn())
    assert h[0].source == "hackernews" and h[0].engagement == 640


def test_cross_platform_story_ranks_first():
    items = trends.parse_reddit(_reddit(), 30) + trends.parse_hn(_hn())
    res = trends.research("video editing", 30, items_in=items)
    top = res["clusters"][0]
    assert set(top["sources"]) == {"reddit", "hackernews"}
    assert "sora" in top["terms"]
    md = trends.brief(res)
    assert "multi-platform" in md and "Trend brief" in md


def test_dead_sources_are_reported(monkeypatch):
    def boom(*a, **k):
        raise OSError("blocked")
    monkeypatch.setitem(trends.COLLECTORS, "reddit", boom)
    monkeypatch.setitem(trends.COLLECTORS, "hackernews", lambda q, d: trends.parse_hn(_hn()))
    res = trends.research("video", 30, sources=["reddit", "hackernews"])
    assert res["health"]["reddit"]["ok"] is False and res["health"]["hackernews"]["ok"] is True
    assert "unavailable: reddit" in trends.brief(res)
