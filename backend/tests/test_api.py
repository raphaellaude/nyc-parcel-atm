from fastapi.testclient import TestClient

from main import app, pluto_years

client = TestClient(app)

LAT, LON = "40.7406", "-73.9897"
OFF_BLOCK = ("40.7128", "-74.0060")


def test_only_fixture_years_are_loaded():
    assert list(pluto_years) == ["25", "26"]


def test_point_lookup_returns_full_record():
    r = client.get(f"/single_year_point_lookup/26/{LAT}/{LON}")
    assert r.status_code == 200
    assert "159 5 AVENUE" in r.text
    assert "bctcb2020" in r.text
    assert "OGC_FID" not in r.text


def test_point_lookup_kiosk_returns_summary_columns():
    r = client.get(
        f"/single_year_point_lookup/25/{LAT}/{LON}", params={"kiosk": "true"}
    )
    assert r.status_code == 200
    assert "SHEFA LAND CORP" in r.text
    assert "bctcb2020" not in r.text


def test_point_lookup_off_block_finds_no_parcel():
    r = client.get(f"/single_year_point_lookup/26/{OFF_BLOCK[0]}/{OFF_BLOCK[1]}")
    assert r.status_code == 200
    assert "No parcel found" in r.text


def test_point_lookup_missing_year_is_404():
    r = client.get(f"/single_year_point_lookup/10/{LAT}/{LON}")
    assert r.status_code == 404


def test_point_lookup_rejects_bad_coordinates():
    r = client.get(f"/single_year_point_lookup/26/not-a-lat/{LON}")
    assert r.status_code == 400


def test_receipt_covers_each_year():
    r = client.get(f"/receipt/{LAT}/{LON}")
    assert r.status_code == 200
    assert r.text.count("<svg") == 2
    assert "<td>25</td>" in r.text
    assert "<td>26</td>" in r.text
    assert "SHEFA LAND CORP" in r.text


def test_receipt_kiosk_includes_address_and_barcode():
    r = client.get(f"/receipt/{LAT}/{LON}", params={"kiosk": "true"})
    assert r.status_code == 200
    assert "159 5 AVENUE" in r.text
    assert r.text.count("<svg") == 3


def test_receipt_off_block_is_404():
    r = client.get(f"/receipt/{OFF_BLOCK[0]}/{OFF_BLOCK[1]}")
    assert r.status_code == 404
