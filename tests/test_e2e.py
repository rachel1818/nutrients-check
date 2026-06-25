"""
End-to-end tests that chain multiple requests together the way a real
visitor would — home page -> autocomplete -> search results -> detail page,
crawling links and cross-checking the HTML against the JSON API, instead of
poking a single route in isolation.
"""
import re

HREF_RE = re.compile(rb'href="(/[^"]*)"')
DETAIL_LINK_RE = re.compile(r"/nutrients/\d+")


def _links(html: bytes) -> list[str]:
    return [href.decode() for href in HREF_RE.findall(html)]


class TestHomeToSearchJourney:
    """Home page -> autocomplete suggests a nutrient -> search lands on its detail."""

    def test_full_journey_for_a_known_nutrient(self, seeded_client):
        home = seeded_client.get("/")
        assert home.status_code == 200
        assert b'action="/search"' in home.content

        suggestions = seeded_client.get("/api/nutrients/suggest?q=iron").json()
        match = next(s for s in suggestions if s["name"] == "Iron")

        result = seeded_client.get(f"/search?nutrient={match['name']}")
        assert result.status_code == 200
        assert b"Iron" in result.content
        assert b"Foods That Provide" in result.content

        api_detail = seeded_client.get(f"/api/nutrients/{match['id']}")
        assert api_detail.status_code == 200
        assert api_detail.json()["name"] == "Iron"

    def test_autocomplete_suggestion_id_resolves_to_matching_detail_page(self, seeded_client):
        suggestions = seeded_client.get("/api/nutrients/suggest?q=calcium").json()
        match = next(s for s in suggestions if s["name"] == "Calcium")

        detail = seeded_client.get(f"/nutrients/{match['id']}")
        assert detail.status_code == 200
        assert b"Calcium" in detail.content

    def test_synonym_search_lands_on_the_correct_nutrient(self, seeded_client):
        result = seeded_client.get("/search?nutrient=folate")
        assert result.status_code == 200
        assert b"Vitamin B9" in result.content

        api = seeded_client.get("/api/nutrients/by-slug/vitamin-b9")
        synonyms = [s["synonym"].lower() for s in api.json()["synonyms"]]
        assert "folate" in synonyms

    def test_typo_search_suggestion_link_resolves_to_a_real_nutrient(self, seeded_client):
        typo_result = seeded_client.get("/search?nutrient=vitamine+c")
        assert typo_result.status_code == 200

        search_links = [l for l in _links(typo_result.content) if l.startswith("/search?nutrient=")]
        if search_links:
            follow_up = seeded_client.get(search_links[0])
            assert follow_up.status_code == 200
            assert b"No results" not in follow_up.content


class TestBrowseAllNutrientsJourney:
    """All Nutrients page -> follow every pill -> every detail page actually loads."""

    def test_every_nutrient_pill_links_to_a_working_detail_page(self, seeded_client):
        listing = seeded_client.get("/nutrients")
        assert listing.status_code == 200

        detail_links = sorted({l for l in _links(listing.content) if DETAIL_LINK_RE.fullmatch(l)})
        assert len(detail_links) >= 10

        for link in detail_links:
            detail = seeded_client.get(link)
            assert detail.status_code == 200, f"{link} broke the crawl"
            assert b"Foods That Provide" in detail.content

    def test_detail_page_links_back_to_all_nutrients(self, seeded_client):
        listing = seeded_client.get("/nutrients")
        detail_link = next(l for l in _links(listing.content) if DETAIL_LINK_RE.fullmatch(l))

        detail = seeded_client.get(detail_link)
        assert detail.status_code == 200
        assert b'href="/nutrients"' in detail.content


class TestApiHtmlConsistencyJourney:
    """Whatever a detail page renders must match what its own JSON API returns."""

    def test_food_sources_match_between_html_and_api(self, seeded_client):
        nutrient_id = seeded_client.get("/api/nutrients?limit=1").json()["items"][0]["id"]

        api_detail = seeded_client.get(f"/api/nutrients/{nutrient_id}").json()
        html = seeded_client.get(f"/nutrients/{nutrient_id}").content

        assert api_detail["food_sources"]
        for food in api_detail["food_sources"]:
            assert food["food_name"].encode() in html

    def test_rda_rows_match_between_html_and_api(self, seeded_client):
        nutrient_id = seeded_client.get("/api/nutrients?limit=1").json()["items"][0]["id"]

        api_detail = seeded_client.get(f"/api/nutrients/{nutrient_id}").json()
        html = seeded_client.get(f"/nutrients/{nutrient_id}").content

        assert len(api_detail["rda_values"]) >= 3
        for rda in api_detail["rda_values"]:
            assert rda["age_group"].encode() in html

    def test_paginated_foods_api_is_a_subset_of_the_full_detail(self, seeded_client):
        nutrient_id = seeded_client.get("/api/nutrients?limit=1").json()["items"][0]["id"]

        full = seeded_client.get(f"/api/nutrients/{nutrient_id}").json()
        page = seeded_client.get(f"/api/nutrients/{nutrient_id}/foods?offset=0&limit=3").json()

        full_names = {f["food_name"] for f in full["food_sources"]}
        page_names = {f["food_name"] for f in page["items"]}
        assert page_names <= full_names


class TestSitemapCrawlJourney:
    """The generated sitemap must only list URLs that actually resolve."""

    def test_every_sitemap_url_resolves_200(self, seeded_client):
        sitemap = seeded_client.get("/sitemap.xml")
        assert sitemap.status_code == 200

        locs = re.findall(rb"<loc>(.*?)</loc>", sitemap.content)
        assert locs

        for raw in locs:
            path = "/" + raw.decode().split("://", 1)[1].split("/", 1)[1]
            page = seeded_client.get(path)
            assert page.status_code == 200, f"{path} from sitemap is broken"


class TestErrorRecoveryJourney:
    """A user who hits a dead end should always have a way back into the app."""

    def test_404_page_has_a_way_back_home(self, client):
        broken = client.get("/this-page-does-not-exist")
        assert broken.status_code == 404
        assert b'href="/"' in broken.content

    def test_unknown_detail_id_404_then_recover_via_all_nutrients(self, seeded_client):
        missing = seeded_client.get("/nutrients/999999")
        assert missing.status_code == 404

        recovered = seeded_client.get("/nutrients")
        assert recovered.status_code == 200
        assert b"Iron" in recovered.content

    def test_nonsense_search_offers_a_path_back_into_the_app(self, seeded_client):
        dead_end = seeded_client.get("/search?nutrient=zzzznotanutrient")
        assert dead_end.status_code == 200
        assert "/nutrients" in _links(dead_end.content) or "/" in _links(dead_end.content)
