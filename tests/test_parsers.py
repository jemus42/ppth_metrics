"""Unit tests for the ARC stats parser.

The fixture is a real capture from PPTH; the 2-line preamble (kstat header
+ column names) is the easy thing to get wrong silently.
"""

from metrics import parse_arcstats


ARCSTATS_FIXTURE = (
    "19 1 0x01 147 39984 7682526724 1464855638128092\n"
    "name                            type data\n"
    "hits                            4    23925343472\n"
    "misses                          4    16060758\n"
    "c                               4    4399659908\n"
    "c_max                           4    15665278976\n"
    "size                            4    4221206224\n"
    "data_size                       4    2787362816\n"
    "metadata_size                   4    844011008\n"
)


def test_parse_arcstats_extracts_named_counters():
    stats = parse_arcstats(ARCSTATS_FIXTURE)
    # The two-line preamble must not poison results
    assert "name" not in stats
    assert "19" not in stats
    assert stats["size"] == 4221206224
    assert stats["c_max"] == 15665278976
    assert stats["hits"] == 23925343472


def test_parse_arcstats_handles_missing_keys_gracefully():
    """Caller code expects .get() semantics; parser must not raise on partial input."""
    stats = parse_arcstats("19 1 0x01 0 0 0 0\nname type data\nsize 4 100\n")
    assert stats["size"] == 100
    assert "c_max" not in stats
