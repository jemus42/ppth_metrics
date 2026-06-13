"""Unit tests for the ZFS / ARC parsers.

The fixtures are real captures from PPTH; column layout and the 2-line
arcstats preamble (kstat header + column names) are the easy things to
get wrong silently.
"""

from metrics import parse_zfs_list_output, parse_arcstats


ZFS_LIST_FIXTURE = (
    "Primary\t34888580606976\t46157419271744\t166656\n"
    "Primary/backups\t102113654784\t46157419271744\t102112583424\n"
    "Primary/media\t34782974187648\t46157419271744\t34740741396672\n"
    "SSD\t282011762688\t180695080960\t68311126016\n"
)


def test_parse_zfs_list_basic_shapes():
    rows = parse_zfs_list_output(ZFS_LIST_FIXTURE)
    assert len(rows) == 4
    primary = rows[0]
    assert primary["name"] == "Primary"
    assert primary["used"] == 34888580606976
    assert primary["avail"] == 46157419271744
    assert primary["referenced"] == 166656


def test_parse_zfs_list_skips_blank_lines():
    text = ZFS_LIST_FIXTURE + "\n\n"
    rows = parse_zfs_list_output(text)
    assert len(rows) == 4


def test_parse_zfs_list_handles_empty_input():
    assert parse_zfs_list_output("") == []


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
