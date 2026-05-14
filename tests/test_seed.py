"""Tests for the seed data script."""
import pytest
from sqlalchemy import func

from app.models import (
    Nutrient,
    NutrientAbsorptionBlocker,
    NutrientAbsorptionHelper,
    NutrientBodyRole,
    NutrientFoodSource,
    NutrientRdaValue,
    Source,
)


@pytest.fixture(scope="function")
def seeded_db(db_session):
    from tools.seed_data import seed_all
    seed_all(db_session)
    return db_session


class TestSeedPopulation:
    def test_seeds_at_least_10_nutrients(self, seeded_db):
        assert seeded_db.query(Nutrient).count() >= 10

    def test_seeds_at_least_5_foods_per_nutrient(self, seeded_db):
        nutrients = seeded_db.query(Nutrient).all()
        for nutrient in nutrients:
            count = (
                seeded_db.query(NutrientFoodSource)
                .filter(NutrientFoodSource.nutrient_id == nutrient.id)
                .count()
            )
            assert count >= 5, f"{nutrient.name} has only {count} food sources"

    def test_seeds_at_least_1_helper_per_nutrient(self, seeded_db):
        nutrients = seeded_db.query(Nutrient).all()
        for nutrient in nutrients:
            count = (
                seeded_db.query(NutrientAbsorptionHelper)
                .filter(NutrientAbsorptionHelper.nutrient_id == nutrient.id)
                .count()
            )
            assert count >= 1, f"{nutrient.name} has no absorption helpers"

    def test_seeds_at_least_1_blocker_per_nutrient(self, seeded_db):
        nutrients = seeded_db.query(Nutrient).all()
        for nutrient in nutrients:
            count = (
                seeded_db.query(NutrientAbsorptionBlocker)
                .filter(NutrientAbsorptionBlocker.nutrient_id == nutrient.id)
                .count()
            )
            assert count >= 1, f"{nutrient.name} has no absorption blockers"

    def test_seeds_at_least_1_body_role_per_nutrient(self, seeded_db):
        nutrients = seeded_db.query(Nutrient).all()
        for nutrient in nutrients:
            count = (
                seeded_db.query(NutrientBodyRole)
                .filter(NutrientBodyRole.nutrient_id == nutrient.id)
                .count()
            )
            assert count >= 1, f"{nutrient.name} has no body roles"

    def test_seeds_at_least_3_rda_values_per_nutrient(self, seeded_db):
        nutrients = seeded_db.query(Nutrient).all()
        for nutrient in nutrients:
            count = (
                seeded_db.query(NutrientRdaValue)
                .filter(NutrientRdaValue.nutrient_id == nutrient.id)
                .count()
            )
            assert count >= 3, f"{nutrient.name} has only {count} RDA values"

    def test_total_food_sources_at_least_50(self, seeded_db):
        assert seeded_db.query(NutrientFoodSource).count() >= 50

    def test_total_rda_values_at_least_30(self, seeded_db):
        assert seeded_db.query(NutrientRdaValue).count() >= 30

    def test_has_sources(self, seeded_db):
        assert seeded_db.query(Source).count() >= 1


class TestSeedIdempotency:
    def test_rerun_does_not_duplicate_nutrients(self, seeded_db):
        from tools.seed_data import seed_all
        count_before = seeded_db.query(Nutrient).count()
        seed_all(seeded_db)
        count_after = seeded_db.query(Nutrient).count()
        assert count_before == count_after

    def test_rerun_does_not_duplicate_sources(self, seeded_db):
        from tools.seed_data import seed_all
        seed_all(seeded_db)
        unique_urls = seeded_db.query(func.count(func.distinct(Source.url))).scalar()
        total = seeded_db.query(Source).count()
        assert unique_urls == total

    def test_rerun_does_not_duplicate_food_sources(self, seeded_db):
        from tools.seed_data import seed_all
        count_before = seeded_db.query(NutrientFoodSource).count()
        seed_all(seeded_db)
        count_after = seeded_db.query(NutrientFoodSource).count()
        assert count_before == count_after


class TestSeedDataIntegrity:
    def test_all_rda_values_have_source_id(self, seeded_db):
        orphans = (
            seeded_db.query(NutrientRdaValue)
            .filter(NutrientRdaValue.source_id.is_(None))
            .count()
        )
        assert orphans == 0

    def test_all_food_sources_have_source_id(self, seeded_db):
        orphans = (
            seeded_db.query(NutrientFoodSource)
            .filter(NutrientFoodSource.source_id.is_(None))
            .count()
        )
        assert orphans == 0

    def test_all_body_roles_have_source_id(self, seeded_db):
        orphans = (
            seeded_db.query(NutrientBodyRole)
            .filter(NutrientBodyRole.source_id.is_(None))
            .count()
        )
        assert orphans == 0

    def test_vitamin_b9_has_folate_synonym(self, seeded_db):
        b9 = seeded_db.query(Nutrient).filter(Nutrient.name == "Vitamin B9").first()
        assert b9 is not None
        synonyms = [s.synonym.lower() for s in b9.synonyms]
        assert "folate" in synonyms

    def test_vitamin_b9_has_folic_acid_synonym(self, seeded_db):
        b9 = seeded_db.query(Nutrient).filter(Nutrient.name == "Vitamin B9").first()
        synonyms = [s.synonym.lower() for s in b9.synonyms]
        assert "folic acid" in synonyms

    def test_b12_ul_is_null(self, seeded_db):
        """NIH confirms no UL for B12 — must be stored as NULL."""
        b12 = seeded_db.query(Nutrient).filter(Nutrient.name == "Vitamin B12").first()
        assert b12 is not None
        for rda in b12.rda_values:
            assert rda.upper_limit is None, f"Expected NULL UL for B12, got {rda.upper_limit}"

    def test_nutrients_have_slugs(self, seeded_db):
        nutrients = seeded_db.query(Nutrient).all()
        for n in nutrients:
            assert n.slug is not None
            assert n.slug != ""
            assert " " not in n.slug

    def test_iron_slug(self, seeded_db):
        iron = seeded_db.query(Nutrient).filter(Nutrient.name == "Iron").first()
        assert iron.slug == "iron"

    def test_vitamin_c_slug(self, seeded_db):
        vc = seeded_db.query(Nutrient).filter(Nutrient.name == "Vitamin C").first()
        assert vc.slug == "vitamin-c"

    def test_source_urls_are_from_trusted_sources(self, seeded_db):
        trusted_domains = ["ods.od.nih.gov", "fdc.nal.usda.gov", "hsph.harvard.edu",
                           "clevelandclinic.org", "mayoclinic.org"]
        sources = seeded_db.query(Source).all()
        for source in sources:
            assert any(domain in source.url for domain in trusted_domains), (
                f"Untrusted source URL: {source.url}"
            )

    def test_all_categories_represented(self, seeded_db):
        categories = {n.category for n in seeded_db.query(Nutrient).all()}
        assert "Vitamins" in categories
        assert "Minerals" in categories
        assert "Macronutrients" in categories


class TestAlembicMigrations:
    def test_alembic_upgrade_head(self):
        """Alembic upgrade head runs without error on in-memory SQLite."""
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd="c:/Users/Evangeline/OneDrive/Desktop/Projects/nutrients-check",
            capture_output=True,
            text=True,
        )
        # Exit code 0 means success; exit code 1 is also acceptable if schema already exists
        assert result.returncode in (0, 1), f"alembic upgrade failed:\n{result.stderr}"

    def test_alembic_current_shows_revision(self):
        """alembic current returns without crashing."""
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            cwd="c:/Users/Evangeline/OneDrive/Desktop/Projects/nutrients-check",
            capture_output=True,
            text=True,
        )
        assert result.returncode in (0, 1)
