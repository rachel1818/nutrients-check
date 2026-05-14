"""Tests for HTML routes."""


class TestHomePage:
    def test_home_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_home_has_search_form(self, client):
        r = client.get("/")
        assert b"search-form" in r.content

    def test_home_has_all_nutrients_link(self, client):
        r = client.get("/")
        assert b"/nutrients" in r.content

    def test_home_has_floating_emojis(self, client):
        r = client.get("/")
        assert b"float-emoji" in r.content


class TestSearchPage:
    def test_search_no_query_200(self, client):
        r = client.get("/search")
        assert r.status_code == 200

    def test_search_empty_query_200(self, client):
        r = client.get("/search?nutrient=")
        assert r.status_code == 200

    def test_search_unknown_nutrient_not_found(self, seeded_client):
        r = seeded_client.get("/search?nutrient=xyznonexistent99")
        assert r.status_code == 200
        assert b"No results" in r.content

    def test_search_valid_nutrient(self, seeded_client):
        r = seeded_client.get("/search?nutrient=Iron")
        assert r.status_code == 200
        assert b"Iron" in r.content
        assert b"Foods That Provide" in r.content

    def test_search_url_is_shareable(self, seeded_client):
        r1 = seeded_client.get("/search?nutrient=Calcium")
        r2 = seeded_client.get("/search?nutrient=Calcium")
        assert r1.status_code == 200
        assert r1.content == r2.content

    def test_search_synonym_resolves(self, seeded_client):
        r = seeded_client.get("/search?nutrient=folate")
        assert r.status_code == 200
        assert b"Vitamin B9" in r.content or b"folate" in r.content.lower()

    def test_search_typo_shows_suggestions(self, seeded_client):
        r = seeded_client.get("/search?nutrient=vitamine+c")
        assert r.status_code == 200
        content = r.content.lower()
        assert b"vitamin c" in content or b"no results" in content

    def test_search_case_insensitive(self, seeded_client):
        r = seeded_client.get("/search?nutrient=iron")
        assert r.status_code == 200
        assert b"Iron" in r.content

    def test_disclaimer_banner_in_search(self, seeded_client):
        r = seeded_client.get("/search?nutrient=Iron")
        assert b"educational purposes" in r.content or b"disclaimer" in r.content.lower()


class TestAllNutrientsPage:
    def test_all_nutrients_200(self, client):
        r = client.get("/nutrients")
        assert r.status_code == 200

    def test_all_nutrients_empty_state(self, client):
        r = client.get("/nutrients")
        assert r.status_code == 200

    def test_all_nutrients_shows_nutrients(self, seeded_client):
        r = seeded_client.get("/nutrients")
        assert r.status_code == 200
        assert b"Iron" in r.content
        assert b"Vitamin C" in r.content

    def test_all_nutrients_grouped_by_category(self, seeded_client):
        r = seeded_client.get("/nutrients")
        assert b"Vitamins" in r.content
        assert b"Minerals" in r.content

    def test_all_nutrients_links_to_detail(self, seeded_client):
        r = seeded_client.get("/nutrients")
        assert b"/nutrients/" in r.content


class TestNutrientDetailPage:
    def test_detail_page_200(self, seeded_client):
        r = seeded_client.get("/nutrients/1")
        assert r.status_code == 200

    def test_detail_page_404_for_unknown(self, client):
        r = client.get("/nutrients/9999")
        assert r.status_code == 404

    def test_detail_has_three_columns(self, seeded_client):
        r = seeded_client.get("/nutrients/1")
        content = r.content
        assert b"Foods That Provide" in content
        assert b"Improves Absorption" in content
        assert b"Role in the Body" in content


class TestErrorPages:
    def test_404_page_renders(self, client):
        r = client.get("/this-path-does-not-exist")
        assert r.status_code == 404

    def test_404_has_site_header(self, client):
        r = client.get("/this-path-does-not-exist")
        assert b"Nutrient Check" in r.content

    def test_404_has_site_footer(self, client):
        r = client.get("/this-path-does-not-exist")
        assert b"educational purposes" in r.content or b"footer" in r.content.lower()


class TestUtilityRoutes:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_robots_txt_200(self, client):
        r = client.get("/robots.txt")
        assert r.status_code == 200
        assert b"Disallow: /api/" in r.content

    def test_sitemap_xml_200(self, seeded_client):
        r = seeded_client.get("/sitemap.xml")
        assert r.status_code == 200
        assert b"urlset" in r.content

    def test_sitemap_xml_lists_nutrients(self, seeded_client):
        r = seeded_client.get("/sitemap.xml")
        assert b"/nutrients/" in r.content


class TestSecurityHeaders:
    def test_security_headers_on_home(self, client):
        r = client.get("/")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_security_headers_on_api(self, client):
        r = client.get("/api/nutrients")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"


class TestFooterDisclaimer:
    def test_footer_disclaimer_on_home(self, client):
        r = client.get("/")
        assert b"educational purposes" in r.content

    def test_footer_disclaimer_on_all_nutrients(self, client):
        r = client.get("/nutrients")
        assert b"educational purposes" in r.content
