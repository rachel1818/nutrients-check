"""Tests for all API endpoints."""


class TestListNutrients:
    def test_list_empty(self, client):
        r = client.get("/api/nutrients")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    def test_list_paginated(self, seeded_client):
        r = seeded_client.get("/api/nutrients?offset=0&limit=5")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 5
        assert data["total"] >= 10

    def test_list_has_correct_fields(self, seeded_client):
        r = seeded_client.get("/api/nutrients?limit=1")
        assert r.status_code == 200
        item = r.json()["items"][0]
        assert "id" in item
        assert "name" in item
        assert "category" in item
        assert "slug" in item

    def test_list_offset(self, seeded_client):
        r1 = seeded_client.get("/api/nutrients?offset=0&limit=5")
        r2 = seeded_client.get("/api/nutrients?offset=5&limit=5")
        ids1 = {n["id"] for n in r1.json()["items"]}
        ids2 = {n["id"] for n in r2.json()["items"]}
        assert ids1.isdisjoint(ids2)


class TestSuggestEndpoint:
    def test_suggest_empty_q_returns_empty(self, client):
        r = client.get("/api/nutrients/suggest?q=")
        assert r.status_code == 200
        assert r.json() == []

    def test_suggest_short_q_returns_empty(self, client):
        r = client.get("/api/nutrients/suggest?q=v")
        assert r.status_code == 200
        assert r.json() == []

    def test_suggest_no_q_returns_empty(self, client):
        r = client.get("/api/nutrients/suggest")
        assert r.status_code == 200
        assert r.json() == []

    def test_suggest_returns_up_to_8(self, seeded_client):
        r = seeded_client.get("/api/nutrients/suggest?q=vit")
        assert r.status_code == 200
        results = r.json()
        assert len(results) <= 8

    def test_suggest_correct_shape(self, seeded_client):
        r = seeded_client.get("/api/nutrients/suggest?q=iron")
        assert r.status_code == 200
        results = r.json()
        assert isinstance(results, list)
        if results:
            item = results[0]
            assert "id" in item
            assert "name" in item
            assert "category" in item

    def test_suggest_not_swallowed_by_id_route(self, seeded_client):
        """Critical test: /api/nutrients/suggest must not match /{id} route."""
        r = seeded_client.get("/api/nutrients/suggest?q=iron")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_suggest_case_insensitive(self, seeded_client):
        r = seeded_client.get("/api/nutrients/suggest?q=IRON")
        assert r.status_code == 200
        names = [item["name"] for item in r.json()]
        assert any("iron" in n.lower() or "Iron" in n for n in names)


class TestGetNutrientById:
    def test_get_by_id_200(self, seeded_client):
        r = seeded_client.get("/api/nutrients/1")
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert "name" in data
        assert "food_sources" in data
        assert "rda_values" in data

    def test_get_by_id_404(self, client):
        r = client.get("/api/nutrients/9999")
        assert r.status_code == 404

    def test_get_by_id_has_full_detail(self, seeded_client):
        r = seeded_client.get("/api/nutrients/1")
        data = r.json()
        assert "synonyms" in data
        assert "absorption_helpers" in data
        assert "absorption_blockers" in data
        assert "body_roles" in data


class TestGetNutrientBySlug:
    def test_by_slug_returns_nutrient(self, seeded_client):
        r = seeded_client.get("/api/nutrients/by-slug/iron")
        assert r.status_code == 200
        assert r.json()["name"] == "Iron"

    def test_by_slug_not_found_404(self, client):
        r = client.get("/api/nutrients/by-slug/nonexistent-nutrient")
        assert r.status_code == 404

    def test_by_slug_not_swallowed_by_id_route(self, seeded_client):
        """Critical: /api/nutrients/by-slug/{slug} must not match /{id}."""
        r = seeded_client.get("/api/nutrients/by-slug/vitamin-c")
        # Should return 200 or 404, NOT 422 (which would mean /{id} captured it as non-int)
        assert r.status_code in (200, 404)


class TestPaginatedFoods:
    def test_foods_offset_0(self, seeded_client):
        r = seeded_client.get("/api/nutrients/1/foods?offset=0&limit=3")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert len(data["items"]) <= 3

    def test_foods_offset(self, seeded_client):
        r1 = seeded_client.get("/api/nutrients/1/foods?offset=0&limit=3")
        r2 = seeded_client.get("/api/nutrients/1/foods?offset=3&limit=3")
        ids1 = {f["id"] for f in r1.json()["items"]}
        ids2 = {f["id"] for f in r2.json()["items"]}
        assert ids1.isdisjoint(ids2)

    def test_foods_total_accurate(self, seeded_client):
        r = seeded_client.get("/api/nutrients/1/foods?offset=0&limit=100")
        data = r.json()
        assert data["total"] == len(data["items"])

    def test_foods_route_not_swallowed(self, seeded_client):
        """Critical: /api/nutrients/{id}/foods must not be captured by /{id}."""
        r = seeded_client.get("/api/nutrients/1/foods?offset=0&limit=10")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    def test_foods_not_found_nutrient(self, client):
        r = client.get("/api/nutrients/9999/foods")
        assert r.status_code == 404

    def test_foods_have_source_info(self, seeded_client):
        r = seeded_client.get("/api/nutrients/1/foods?limit=1")
        data = r.json()
        if data["items"]:
            food = data["items"][0]
            assert "source" in food
            assert "url" in food["source"]
            assert "name" in food["source"]
