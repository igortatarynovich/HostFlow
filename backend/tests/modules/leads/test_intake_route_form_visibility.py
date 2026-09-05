from backend.app.modules.leads.intake_route_form_visibility import (
    drop_empty_page_duplicates,
    keep_intake_route_form,
)

CONNECTED = {"484113398123847"}
CLAIMED = {"1352242509195886", "2911549885844549"}
GRAPH = {"1352242509195886", "1695737891802328"}


def test_keep_claimed_form_on_connected_page() -> None:
    assert keep_intake_route_form(
        form_id="1352242509195886",
        page_id="484113398123847",
        claimed_form_ids=CLAIMED,
        connected_page_ids=CONNECTED,
        graph_form_ids=GRAPH,
    )


def test_drop_unclaimed_graph_form_on_connected_page() -> None:
    assert not keep_intake_route_form(
        form_id="1695737891802328",
        page_id="484113398123847",
        claimed_form_ids=CLAIMED,
        connected_page_ids=CONNECTED,
        graph_form_ids=GRAPH,
    )


def test_drop_leftover_claimed_form_from_disconnected_page() -> None:
    """Work Host leftover on Focus after the Page moved to another tenant."""
    assert not keep_intake_route_form(
        form_id="2911549885844549",
        page_id="259905353877064",
        claimed_form_ids=CLAIMED,
        connected_page_ids=CONNECTED,
        graph_form_ids=GRAPH,
    )


def test_keep_claimed_graph_form_when_page_id_missing() -> None:
    assert keep_intake_route_form(
        form_id="1352242509195886",
        page_id=None,
        claimed_form_ids=CLAIMED,
        connected_page_ids=CONNECTED,
        graph_form_ids=GRAPH,
    )


def test_keep_claimed_form_on_connected_page_without_graph() -> None:
    assert keep_intake_route_form(
        form_id="1352242509195886",
        page_id="484113398123847",
        claimed_form_ids=CLAIMED,
        connected_page_ids=CONNECTED,
        graph_form_ids=set(),
    )


def test_drop_empty_form_id() -> None:
    assert not keep_intake_route_form(
        form_id="  ",
        page_id="484113398123847",
        claimed_form_ids=CLAIMED,
        connected_page_ids=CONNECTED,
        graph_form_ids=GRAPH,
    )


def test_drop_empty_page_duplicate_when_paged_row_exists() -> None:
    assert drop_empty_page_duplicates("1352242509195886", None, {"1352242509195886"})
    assert not drop_empty_page_duplicates("1352242509195886", "484113398123847", {"1352242509195886"})
    assert not drop_empty_page_duplicates("1352242509195886", None, set())
