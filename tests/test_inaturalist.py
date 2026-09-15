from unittest.mock import patch, MagicMock

from src.qc_engine.inaturalist import fetch_observations, MAX_PAGE_SIZE


def _mock_response(results):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": results}
    return response


def test_fetch_observations_pages_until_total_records_reached():
    # total_records requires 2 pages given MAX_PAGE_SIZE-sized batches
    total_records = MAX_PAGE_SIZE + 50
    page_1 = [{"id": i} for i in range(MAX_PAGE_SIZE)]
    page_2 = [{"id": i} for i in range(MAX_PAGE_SIZE, MAX_PAGE_SIZE + 50)]

    with patch("src.qc_engine.inaturalist.requests.get") as mock_get:
        mock_get.side_effect = [_mock_response(page_1), _mock_response(page_2)]
        results = fetch_observations(taxon_id=1, total_records=total_records)

    assert len(results) == total_records
    assert mock_get.call_count == 2


def test_fetch_observations_stops_on_short_final_page():
    # API has fewer observations than total_records; loop should stop, not hang
    total_records = 100
    short_page = [{"id": i} for i in range(30)]

    with patch("src.qc_engine.inaturalist.requests.get") as mock_get:
        mock_get.side_effect = [_mock_response(short_page)]
        results = fetch_observations(taxon_id=1, total_records=total_records)

    assert len(results) == 30
    assert mock_get.call_count == 1


def test_fetch_observations_stops_on_empty_results():
    with patch("src.qc_engine.inaturalist.requests.get") as mock_get:
        mock_get.side_effect = [_mock_response([])]
        results = fetch_observations(taxon_id=1, total_records=100)

    assert results == []
    assert mock_get.call_count == 1


def test_fetch_observations_truncates_to_exact_total_records():
    # If the last page overshoots (shouldn't happen given per_page math, but
    # guards the [:total_records] slice), result length is still exact.
    total_records = 10
    page = [{"id": i} for i in range(10)]

    with patch("src.qc_engine.inaturalist.requests.get") as mock_get:
        mock_get.side_effect = [_mock_response(page)]
        results = fetch_observations(taxon_id=1, total_records=total_records)

    assert len(results) == total_records
