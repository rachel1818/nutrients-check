"""
Seed script for Nutrient Check.
All data from NIH ODS, USDA FoodData Central, Harvard T.H. Chan, Cleveland Clinic, Mayo Clinic.
Re-run safe: upserts nutrients, deletes-and-reinserts child records.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Nutrient,
    NutrientAbsorptionBlocker,
    NutrientAbsorptionHelper,
    NutrientBodyRole,
    NutrientFoodSource,
    NutrientRdaValue,
    NutrientSynonym,
    Source,
)


def _make_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def get_or_create_source(db: Session, name: str, url: str) -> Source:
    source = db.query(Source).filter(Source.url == url).first()
    if not source:
        source = Source(name=name, url=url)
        db.add(source)
        db.flush()
    return source


def upsert_nutrient(db: Session, name: str, category: str, solubility: str | None) -> Nutrient:
    nutrient = db.query(Nutrient).filter(Nutrient.name == name).first()
    if not nutrient:
        slug = _make_slug(name)
        nutrient = Nutrient(name=name, category=category, solubility=solubility, slug=slug)
        db.add(nutrient)
        db.flush()
    return nutrient


def seed_nutrient(db: Session, name: str, category: str, solubility: str | None,
                  synonyms: list[str],
                  food_sources: list[dict],
                  helpers: list[dict],
                  blockers: list[dict],
                  body_roles: list[dict],
                  rda_values: list[dict]) -> None:
    nutrient = upsert_nutrient(db, name, category, solubility)
    nid = nutrient.id

    # Idempotent: delete children then re-insert
    db.query(NutrientSynonym).filter(NutrientSynonym.nutrient_id == nid).delete()
    db.query(NutrientFoodSource).filter(NutrientFoodSource.nutrient_id == nid).delete()
    db.query(NutrientAbsorptionHelper).filter(NutrientAbsorptionHelper.nutrient_id == nid).delete()
    db.query(NutrientAbsorptionBlocker).filter(NutrientAbsorptionBlocker.nutrient_id == nid).delete()
    db.query(NutrientBodyRole).filter(NutrientBodyRole.nutrient_id == nid).delete()
    db.query(NutrientRdaValue).filter(NutrientRdaValue.nutrient_id == nid).delete()
    db.flush()

    for syn in synonyms:
        db.add(NutrientSynonym(nutrient_id=nid, synonym=syn))

    for fs in food_sources:
        src = get_or_create_source(db, fs["source_name"], fs["source_url"])
        db.add(NutrientFoodSource(
            nutrient_id=nid,
            food_name=fs["food_name"],
            serving_size=fs["serving_size"],
            amount=fs["amount"],
            unit=fs["unit"],
            bioavailability_note=fs.get("bioavailability_note"),
            preparation_note=fs.get("preparation_note"),
            source_id=src.id,
        ))

    for h in helpers:
        src = get_or_create_source(db, h["source_name"], h["source_url"])
        db.add(NutrientAbsorptionHelper(
            nutrient_id=nid,
            helper_name=h["helper_name"],
            helper_type=h["helper_type"],
            description=h["description"],
            source_id=src.id,
        ))

    for b in blockers:
        src = get_or_create_source(db, b["source_name"], b["source_url"])
        db.add(NutrientAbsorptionBlocker(
            nutrient_id=nid,
            blocker_name=b["blocker_name"],
            blocker_type=b["blocker_type"],
            description=b["description"],
            source_id=src.id,
        ))

    for role in body_roles:
        src = get_or_create_source(db, role["source_name"], role["source_url"])
        db.add(NutrientBodyRole(
            nutrient_id=nid,
            body_system=role["body_system"],
            explanation=role["explanation"],
            deficiency_signs=role.get("deficiency_signs"),
            source_id=src.id,
        ))

    for rda in rda_values:
        src = get_or_create_source(db, rda["source_name"], rda["source_url"])
        db.add(NutrientRdaValue(
            nutrient_id=nid,
            age_group=rda["age_group"],
            sex=rda["sex"],
            value=rda["value"],
            unit=rda["unit"],
            intake_type=rda["intake_type"],
            upper_limit=rda.get("upper_limit"),  # None = no UL established (NIH confirmed)
            source_id=src.id,
        ))


NIH = "NIH Office of Dietary Supplements"
USDA = "USDA FoodData Central"
HARVARD = "Harvard T.H. Chan School of Public Health"
CLEVELAND = "Cleveland Clinic"
MAYO = "Mayo Clinic"

NIH_VIT_A = "https://ods.od.nih.gov/factsheets/VitaminA-HealthProfessional/"
NIH_VIT_D = "https://ods.od.nih.gov/factsheets/VitaminD-HealthProfessional/"
NIH_VIT_E = "https://ods.od.nih.gov/factsheets/VitaminE-HealthProfessional/"
NIH_VIT_C = "https://ods.od.nih.gov/factsheets/VitaminC-HealthProfessional/"
NIH_VIT_B12 = "https://ods.od.nih.gov/factsheets/VitaminB12-HealthProfessional/"
NIH_VIT_B9 = "https://ods.od.nih.gov/factsheets/Folate-HealthProfessional/"
NIH_IRON = "https://ods.od.nih.gov/factsheets/Iron-HealthProfessional/"
NIH_CALCIUM = "https://ods.od.nih.gov/factsheets/Calcium-HealthProfessional/"
NIH_ZINC = "https://ods.od.nih.gov/factsheets/Zinc-HealthProfessional/"
NIH_MAG = "https://ods.od.nih.gov/factsheets/Magnesium-HealthProfessional/"
USDA_URL = "https://fdc.nal.usda.gov/"
HARVARD_URL = "https://www.hsph.harvard.edu/nutritionsource/"


def seed_all(db: Session) -> None:

    # ── 1. Vitamin A ─────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin A", category="Vitamins", solubility="fat-soluble",
        synonyms=["retinol", "beta-carotene", "retinyl palmitate", "retinyl acetate"],
        food_sources=[
            {"food_name": "Beef Liver", "serving_size": "3 oz (85g)", "amount": 6582, "unit": "mcg",
             "bioavailability_note": "Retinol (preformed vitamin A) from animal sources is highly bioavailable.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sweet Potato (baked)", "serving_size": "1 medium (130g)", "amount": 1403, "unit": "mcg",
             "bioavailability_note": "Beta-carotene is converted to vitamin A; absorption improves with dietary fat.",
             "source_name": NIH, "source_url": NIH_VIT_A},
            {"food_name": "Carrot (raw)", "serving_size": "1 medium (61g)", "amount": 601, "unit": "mcg",
             "preparation_note": "Cooking or pureeing carrots slightly increases beta-carotene bioavailability.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Spinach (cooked)", "serving_size": "1/2 cup (90g)", "amount": 573, "unit": "mcg",
             "bioavailability_note": "Non-heme beta-carotene; absorption enhanced by fat.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Cantaloupe", "serving_size": "1/2 cup cubed (80g)", "amount": 467, "unit": "mcg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Egg (scrambled)", "serving_size": "1 large egg (61g)", "amount": 75, "unit": "mcg",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Dietary Fat", "helper_type": "food",
             "description": "Vitamin A is fat-soluble; consuming it with healthy fats (olive oil, avocado) significantly improves intestinal absorption.",
             "source_name": NIH, "source_url": NIH_VIT_A},
            {"helper_name": "Zinc", "helper_type": "nutrient",
             "description": "Zinc is required for the synthesis of retinol-binding protein, which transports vitamin A in the blood.",
             "source_name": NIH, "source_url": NIH_VIT_A},
        ],
        blockers=[
            {"blocker_name": "Alcohol", "blocker_type": "food",
             "description": "Chronic alcohol consumption depletes vitamin A stores in the liver and impairs its metabolism.",
             "source_name": NIH, "source_url": NIH_VIT_A},
            {"blocker_name": "Mineral Oil", "blocker_type": "food",
             "description": "Mineral oil (used as a laxative) dissolves fat-soluble vitamins in the gut, impairing their absorption.",
             "source_name": MAYO, "source_url": "https://www.mayoclinic.org/drugs-supplements-vitamin-a/art-20365945"},
        ],
        body_roles=[
            {"body_system": "Vision", "explanation": "Vitamin A is a component of rhodopsin, a protein in the eye that absorbs light. It is essential for vision in dim light.",
             "deficiency_signs": "Night blindness; xerophthalmia (dry eye); in severe cases, blindness.",
             "source_name": NIH, "source_url": NIH_VIT_A},
            {"body_system": "Immune System", "explanation": "Vitamin A supports the growth and differentiation of immune cells, including T-lymphocytes, and maintains mucosal barriers.",
             "deficiency_signs": "Increased susceptibility to infections, particularly respiratory and diarrheal diseases.",
             "source_name": NIH, "source_url": NIH_VIT_A},
        ],
        rda_values=[
            # Adults
            {"age_group": "19–50 years", "sex": "male", "value": 900, "unit": "mcg RAE", "intake_type": "RDA",
             "upper_limit": 3000, "source_name": NIH, "source_url": NIH_VIT_A},
            {"age_group": "19–50 years", "sex": "female", "value": 700, "unit": "mcg RAE", "intake_type": "RDA",
             "upper_limit": 3000, "source_name": NIH, "source_url": NIH_VIT_A},
            {"age_group": "4–8 years", "sex": "all", "value": 400, "unit": "mcg RAE", "intake_type": "RDA",
             "upper_limit": 900, "source_name": NIH, "source_url": NIH_VIT_A},
            {"age_group": "Pregnancy (19–50 years)", "sex": "pregnant", "value": 770, "unit": "mcg RAE", "intake_type": "RDA",
             "upper_limit": 3000, "source_name": NIH, "source_url": NIH_VIT_A},
            {"age_group": "Lactation (19–50 years)", "sex": "lactating", "value": 1300, "unit": "mcg RAE", "intake_type": "RDA",
             "upper_limit": 3000, "source_name": NIH, "source_url": NIH_VIT_A},
        ],
    )

    # ── 2. Vitamin D ─────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin D", category="Vitamins", solubility="fat-soluble",
        synonyms=["calciferol", "cholecalciferol", "vitamin D3", "ergocalciferol", "vitamin D2"],
        food_sources=[
            {"food_name": "Salmon (sockeye, cooked)", "serving_size": "3 oz (85g)", "amount": 570, "unit": "IU",
             "bioavailability_note": "Vitamin D3 from fatty fish is the most bioavailable dietary form.",
             "source_name": NIH, "source_url": NIH_VIT_D},
            {"food_name": "Swordfish (cooked)", "serving_size": "3 oz (85g)", "amount": 566, "unit": "IU",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Tuna (canned in water)", "serving_size": "3 oz (85g)", "amount": 154, "unit": "IU",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Fortified Milk (2% fat)", "serving_size": "1 cup (237ml)", "amount": 120, "unit": "IU",
             "bioavailability_note": "Most milk in the US is fortified with D3.",
             "source_name": NIH, "source_url": NIH_VIT_D},
            {"food_name": "Fortified Orange Juice", "serving_size": "1 cup (237ml)", "amount": 137, "unit": "IU",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Egg Yolk (raw)", "serving_size": "1 large (17g)", "amount": 44, "unit": "IU",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Magnesium", "helper_type": "nutrient",
             "description": "Magnesium is required to activate the enzymes that convert vitamin D to its active form (calcitriol). Magnesium deficiency can render vitamin D supplementation ineffective.",
             "source_name": NIH, "source_url": NIH_VIT_D},
            {"helper_name": "Dietary Fat", "helper_type": "food",
             "description": "As a fat-soluble vitamin, vitamin D requires fat in the meal for intestinal absorption.",
             "source_name": HARVARD, "source_url": HARVARD_URL},
        ],
        blockers=[
            {"blocker_name": "Cholestyramine", "blocker_type": "nutrient",
             "description": "This bile acid sequestrant (used to lower cholesterol) can impair the absorption of fat-soluble vitamins including vitamin D.",
             "source_name": NIH, "source_url": NIH_VIT_D},
            {"blocker_name": "Olestra", "blocker_type": "food",
             "description": "Olestra, a fat substitute in some snack foods, inhibits absorption of fat-soluble vitamins including vitamin D.",
             "source_name": NIH, "source_url": NIH_VIT_D},
        ],
        body_roles=[
            {"body_system": "Skeletal System", "explanation": "Vitamin D is essential for calcium absorption in the gut. Without adequate vitamin D, the body cannot absorb enough calcium to maintain bone density.",
             "deficiency_signs": "Rickets in children; osteomalacia (soft bones) and osteoporosis in adults.",
             "source_name": NIH, "source_url": NIH_VIT_D},
            {"body_system": "Immune System", "explanation": "Vitamin D modulates innate and adaptive immune responses and helps reduce excessive inflammation.",
             "source_name": NIH, "source_url": NIH_VIT_D},
        ],
        rda_values=[
            # 600 IU for adults 19-70; 800 for 71+; UL 4000 IU
            {"age_group": "1–70 years", "sex": "all", "value": 600, "unit": "IU", "intake_type": "RDA",
             "upper_limit": 4000, "source_name": NIH, "source_url": NIH_VIT_D},
            {"age_group": "71+ years", "sex": "all", "value": 800, "unit": "IU", "intake_type": "RDA",
             "upper_limit": 4000, "source_name": NIH, "source_url": NIH_VIT_D},
            # Infants: AI (no RDA established)
            {"age_group": "0–12 months", "sex": "all", "value": 400, "unit": "IU", "intake_type": "AI",
             "upper_limit": 1000, "source_name": NIH, "source_url": NIH_VIT_D},
            {"age_group": "Pregnancy / Lactation", "sex": "pregnant", "value": 600, "unit": "IU", "intake_type": "RDA",
             "upper_limit": 4000, "source_name": NIH, "source_url": NIH_VIT_D},
        ],
    )

    # ── 3. Vitamin E ─────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin E", category="Vitamins", solubility="fat-soluble",
        synonyms=["alpha-tocopherol", "tocopherol", "d-alpha-tocopherol"],
        food_sources=[
            {"food_name": "Wheat Germ Oil", "serving_size": "1 tbsp (13.6g)", "amount": 20.3, "unit": "mg",
             "source_name": NIH, "source_url": NIH_VIT_E},
            {"food_name": "Sunflower Seeds (dry roasted)", "serving_size": "1 oz (28g)", "amount": 7.4, "unit": "mg",
             "source_name": NIH, "source_url": NIH_VIT_E},
            {"food_name": "Almonds (dry roasted)", "serving_size": "1 oz (28g)", "amount": 6.8, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sunflower Oil", "serving_size": "1 tbsp (13.6g)", "amount": 5.6, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Hazelnuts (dry roasted)", "serving_size": "1 oz (28g)", "amount": 4.3, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Peanut Butter (smooth)", "serving_size": "2 tbsp (32g)", "amount": 2.9, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Vitamin C", "helper_type": "nutrient",
             "description": "Vitamin C regenerates oxidized vitamin E back to its active antioxidant form, extending its effectiveness.",
             "source_name": NIH, "source_url": NIH_VIT_E},
            {"helper_name": "Dietary Fat", "helper_type": "food",
             "description": "Vitamin E is fat-soluble. Consuming vitamin E-rich foods with a source of fat (e.g., olive oil) improves intestinal absorption.",
             "source_name": HARVARD, "source_url": HARVARD_URL},
        ],
        blockers=[
            {"blocker_name": "High-Dose Iron Supplements", "blocker_type": "nutrient",
             "description": "Large doses of supplemental iron can reduce vitamin E absorption; separate their timing when both are needed.",
             "source_name": MAYO, "source_url": "https://www.mayoclinic.org/drugs-supplements-vitamin-e/art-20364144"},
            {"blocker_name": "Cholestyramine", "blocker_type": "nutrient",
             "description": "This bile acid binder impairs fat-soluble vitamin absorption, including vitamin E.",
             "source_name": NIH, "source_url": NIH_VIT_E},
        ],
        body_roles=[
            {"body_system": "Antioxidant Defense", "explanation": "Vitamin E is a potent fat-soluble antioxidant that protects cell membranes from oxidative damage caused by free radicals.",
             "deficiency_signs": "Peripheral neuropathy, ataxia (loss of muscle coordination), skeletal myopathy, retinopathy.",
             "source_name": NIH, "source_url": NIH_VIT_E},
            {"body_system": "Immune System", "explanation": "Vitamin E enhances immune cell function, particularly T-lymphocyte activity, helping the body fight infections.",
             "source_name": NIH, "source_url": NIH_VIT_E},
        ],
        rda_values=[
            {"age_group": "14+ years", "sex": "all", "value": 15, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 1000, "source_name": NIH, "source_url": NIH_VIT_E},
            {"age_group": "9–13 years", "sex": "all", "value": 11, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 600, "source_name": NIH, "source_url": NIH_VIT_E},
            {"age_group": "4–8 years", "sex": "all", "value": 7, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 300, "source_name": NIH, "source_url": NIH_VIT_E},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 15, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 1000, "source_name": NIH, "source_url": NIH_VIT_E},
        ],
    )

    # ── 4. Vitamin C ─────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin C", category="Vitamins", solubility="water-soluble",
        synonyms=["ascorbic acid", "ascorbate", "L-ascorbic acid", "ascorbyl"],
        food_sources=[
            {"food_name": "Red Bell Pepper (raw)", "serving_size": "1/2 cup chopped (75g)", "amount": 95, "unit": "mg",
             "preparation_note": "Raw peppers retain more vitamin C than cooked ones.",
             "source_name": NIH, "source_url": NIH_VIT_C},
            {"food_name": "Orange", "serving_size": "1 medium (131g)", "amount": 70, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Kiwifruit", "serving_size": "1 medium (76g)", "amount": 64, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Broccoli (cooked)", "serving_size": "1/2 cup (78g)", "amount": 51, "unit": "mg",
             "preparation_note": "Steaming preserves more vitamin C than boiling.",
             "source_name": NIH, "source_url": NIH_VIT_C},
            {"food_name": "Strawberries (raw)", "serving_size": "1/2 cup (76g)", "amount": 49, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Tomato Juice", "serving_size": "6 fl oz (182g)", "amount": 33, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Raw Preparation", "helper_type": "food",
             "description": "Vitamin C is water-soluble and heat-sensitive. Eating fruits and vegetables raw or lightly steamed maximizes vitamin C content.",
             "source_name": HARVARD, "source_url": HARVARD_URL},
        ],
        blockers=[
            {"blocker_name": "Heat / Cooking", "blocker_type": "food",
             "description": "Vitamin C is destroyed by heat. Prolonged boiling at high temperatures can reduce vitamin C content by 50% or more. Prefer steaming or eating raw.",
             "source_name": NIH, "source_url": NIH_VIT_C},
            {"blocker_name": "Excess Supplemental Vitamin C", "blocker_type": "nutrient",
             "description": "At doses above 1000 mg/day, intestinal absorption becomes saturated and excess is excreted in urine. Absorption efficiency decreases as dose increases.",
             "source_name": NIH, "source_url": NIH_VIT_C},
        ],
        body_roles=[
            {"body_system": "Connective Tissue / Collagen", "explanation": "Vitamin C is essential for hydroxylation of proline and lysine, steps required to synthesize collagen — the structural protein in skin, blood vessels, bones, and cartilage.",
             "deficiency_signs": "Scurvy: fatigue, gum disease, bleeding, poor wound healing, joint pain.",
             "source_name": NIH, "source_url": NIH_VIT_C},
            {"body_system": "Immune System", "explanation": "Vitamin C stimulates the production and function of white blood cells (especially neutrophils and lymphocytes) and acts as an antioxidant to protect them from oxidative stress during infection.",
             "source_name": NIH, "source_url": NIH_VIT_C},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "male", "value": 90, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 2000, "source_name": NIH, "source_url": NIH_VIT_C},
            {"age_group": "19+ years", "sex": "female", "value": 75, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 2000, "source_name": NIH, "source_url": NIH_VIT_C},
            {"age_group": "9–13 years", "sex": "all", "value": 45, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 1200, "source_name": NIH, "source_url": NIH_VIT_C},
            {"age_group": "Pregnancy (19–50 years)", "sex": "pregnant", "value": 85, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 2000, "source_name": NIH, "source_url": NIH_VIT_C},
            {"age_group": "Lactation (19–50 years)", "sex": "lactating", "value": 120, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 2000, "source_name": NIH, "source_url": NIH_VIT_C},
        ],
    )

    # ── 5. Vitamin B12 ───────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin B12", category="Vitamins", solubility="water-soluble",
        synonyms=["cobalamin", "cyanocobalamin", "methylcobalamin", "adenosylcobalamin", "hydroxocobalamin"],
        food_sources=[
            {"food_name": "Beef Liver (pan-fried)", "serving_size": "3 oz (85g)", "amount": 70.7, "unit": "mcg",
             "bioavailability_note": "Liver is exceptionally rich in B12; one serving provides nearly 30x the daily requirement.",
             "source_name": NIH, "source_url": NIH_VIT_B12},
            {"food_name": "Clams (cooked)", "serving_size": "3 oz (85g)", "amount": 17.0, "unit": "mcg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Salmon (sockeye, cooked)", "serving_size": "3 oz (85g)", "amount": 4.9, "unit": "mcg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Ground Beef (85% lean, pan-broiled)", "serving_size": "3 oz (85g)", "amount": 2.4, "unit": "mcg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Fortified Breakfast Cereal", "serving_size": "3/4 cup (28g)", "amount": 6.0, "unit": "mcg",
             "bioavailability_note": "Synthetic B12 in fortified foods is well absorbed, even without intrinsic factor.",
             "source_name": NIH, "source_url": NIH_VIT_B12},
            {"food_name": "Milk (whole)", "serving_size": "1 cup (244ml)", "amount": 1.2, "unit": "mcg",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Intrinsic Factor", "helper_type": "nutrient",
             "description": "Intrinsic factor, a protein secreted by the stomach, is required for vitamin B12 absorption in the terminal ileum. Without it, absorption is less than 1%.",
             "source_name": NIH, "source_url": NIH_VIT_B12},
            {"helper_name": "Calcium", "helper_type": "nutrient",
             "description": "Calcium is required for the intrinsic factor–B12 complex to bind to receptors in the terminal ileum and be absorbed.",
             "source_name": NIH, "source_url": NIH_VIT_B12},
        ],
        blockers=[
            {"blocker_name": "Proton Pump Inhibitors (PPIs)", "blocker_type": "nutrient",
             "description": "PPIs (e.g., omeprazole, lansoprazole) reduce stomach acid, which is needed to cleave B12 from food proteins. Long-term use is associated with B12 deficiency.",
             "source_name": NIH, "source_url": NIH_VIT_B12},
            {"blocker_name": "Metformin", "blocker_type": "nutrient",
             "description": "Long-term metformin use reduces vitamin B12 absorption; up to 30% of patients develop reduced B12 levels.",
             "source_name": NIH, "source_url": NIH_VIT_B12},
        ],
        body_roles=[
            {"body_system": "Nervous System", "explanation": "Vitamin B12 is required for the synthesis of myelin, the protective sheath around nerve fibers. It is also involved in the production of neurotransmitters.",
             "deficiency_signs": "Subacute combined degeneration of the spinal cord; numbness/tingling in hands and feet; memory loss; depression.",
             "source_name": NIH, "source_url": NIH_VIT_B12},
            {"body_system": "Blood Cell Formation", "explanation": "B12 works with folate to produce healthy red blood cells. Deficiency prevents proper cell division, leading to abnormally large, immature red blood cells.",
             "deficiency_signs": "Megaloblastic anemia: fatigue, weakness, pale skin, shortness of breath.",
             "source_name": NIH, "source_url": NIH_VIT_B12},
        ],
        rda_values=[
            # No UL established by NIH for B12 — insert None explicitly
            {"age_group": "14+ years", "sex": "all", "value": 2.4, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_VIT_B12},
            {"age_group": "9–13 years", "sex": "all", "value": 1.8, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_VIT_B12},
            {"age_group": "4–8 years", "sex": "all", "value": 1.2, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_VIT_B12},
            {"age_group": "Pregnancy (19–50 years)", "sex": "pregnant", "value": 2.6, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_VIT_B12},
        ],
    )

    # ── 6. Vitamin B9 (Folate) ───────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin B9", category="Vitamins", solubility="water-soluble",
        synonyms=["folate", "folic acid", "vitamin B9", "pteroylglutamic acid", "5-methyltetrahydrofolate", "5-MTHF"],
        food_sources=[
            {"food_name": "Beef Liver (braised)", "serving_size": "3 oz (85g)", "amount": 215, "unit": "mcg DFE",
             "source_name": NIH, "source_url": NIH_VIT_B9},
            {"food_name": "Spinach (cooked)", "serving_size": "1/2 cup (90g)", "amount": 131, "unit": "mcg DFE",
             "preparation_note": "Cooking reduces volume but concentrates folate. Steam briefly to minimize loss.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Black-Eyed Peas (cooked)", "serving_size": "1/2 cup (86g)", "amount": 105, "unit": "mcg DFE",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Fortified Breakfast Cereal", "serving_size": "3/4 cup (28g)", "amount": 400, "unit": "mcg DFE",
             "bioavailability_note": "Synthetic folic acid in fortified foods has nearly 100% bioavailability when consumed without food.",
             "source_name": NIH, "source_url": NIH_VIT_B9},
            {"food_name": "Asparagus (boiled)", "serving_size": "4 spears (60g)", "amount": 89, "unit": "mcg DFE",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Brussels Sprouts (boiled)", "serving_size": "1/2 cup (78g)", "amount": 78, "unit": "mcg DFE",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Vitamin B12", "helper_type": "nutrient",
             "description": "Vitamin B12 and folate work together in the methylation cycle. B12 is required to convert 5-MTHF (the active form of folate) back to a usable form for DNA synthesis.",
             "source_name": NIH, "source_url": NIH_VIT_B9},
            {"helper_name": "Vitamin C", "helper_type": "nutrient",
             "description": "Vitamin C helps protect folate from oxidative degradation in food and may assist its intestinal absorption.",
             "source_name": HARVARD, "source_url": HARVARD_URL},
        ],
        blockers=[
            {"blocker_name": "Alcohol", "blocker_type": "food",
             "description": "Alcohol impairs folate absorption in the small intestine, increases renal excretion, and disrupts folate metabolism in the liver.",
             "source_name": NIH, "source_url": NIH_VIT_B9},
            {"blocker_name": "Methotrexate", "blocker_type": "nutrient",
             "description": "Methotrexate is a folate antagonist used in chemotherapy and rheumatoid arthritis treatment. It blocks dihydrofolate reductase, preventing folate from being used.",
             "source_name": NIH, "source_url": NIH_VIT_B9},
        ],
        body_roles=[
            {"body_system": "Cell Division / DNA Synthesis", "explanation": "Folate is required for the synthesis of purines and thymidylate, essential components of DNA. It is critical during periods of rapid cell division such as pregnancy.",
             "deficiency_signs": "Neural tube defects (spina bifida, anencephaly) in the fetus; megaloblastic anemia in adults.",
             "source_name": NIH, "source_url": NIH_VIT_B9},
            {"body_system": "Cardiovascular", "explanation": "Folate, with B6 and B12, helps break down homocysteine, an amino acid that at elevated levels is associated with increased cardiovascular disease risk.",
             "source_name": NIH, "source_url": NIH_VIT_B9},
        ],
        rda_values=[
            # UL applies to synthetic folic acid only, not naturally occurring folate from food
            {"age_group": "19+ years", "sex": "all", "value": 400, "unit": "mcg DFE", "intake_type": "RDA",
             "upper_limit": 1000, "source_name": NIH, "source_url": NIH_VIT_B9},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 600, "unit": "mcg DFE", "intake_type": "RDA",
             "upper_limit": 1000, "source_name": NIH, "source_url": NIH_VIT_B9},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 500, "unit": "mcg DFE", "intake_type": "RDA",
             "upper_limit": 1000, "source_name": NIH, "source_url": NIH_VIT_B9},
            {"age_group": "9–13 years", "sex": "all", "value": 300, "unit": "mcg DFE", "intake_type": "RDA",
             "upper_limit": 600, "source_name": NIH, "source_url": NIH_VIT_B9},
        ],
    )

    # ── 7. Iron ──────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Iron", category="Minerals", solubility=None,
        synonyms=["ferrous sulfate", "ferric iron", "heme iron", "non-heme iron", "Fe", "ferrous fumarate"],
        food_sources=[
            {"food_name": "Oysters (eastern, cooked)", "serving_size": "3 oz (85g)", "amount": 8.0, "unit": "mg",
             "bioavailability_note": "Oysters contain heme iron, which is absorbed 2–3x more efficiently than non-heme iron from plant sources.",
             "source_name": NIH, "source_url": NIH_IRON},
            {"food_name": "Beef Liver (pan-fried)", "serving_size": "3 oz (85g)", "amount": 5.2, "unit": "mg",
             "bioavailability_note": "Liver provides heme iron with high bioavailability.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "White Beans (canned)", "serving_size": "1/2 cup (131g)", "amount": 3.9, "unit": "mg",
             "bioavailability_note": "Non-heme iron; pair with vitamin C-rich foods to enhance absorption.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Dark Chocolate (70–85% cacao)", "serving_size": "1 oz (28g)", "amount": 3.4, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Lentils (cooked)", "serving_size": "1/2 cup (99g)", "amount": 3.3, "unit": "mg",
             "bioavailability_note": "Non-heme iron; soaking lentils before cooking can reduce phytate content and improve absorption.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Spinach (cooked)", "serving_size": "1/2 cup (90g)", "amount": 3.2, "unit": "mg",
             "preparation_note": "Cooking spinach reduces oxalate content, slightly improving non-heme iron absorption.",
             "bioavailability_note": "Non-heme iron; oxalates in raw spinach inhibit absorption. Add lemon juice (vitamin C) to improve uptake.",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Vitamin C", "helper_type": "nutrient",
             "description": "Vitamin C converts ferric iron (Fe3+) to ferrous iron (Fe2+), which is more soluble and better absorbed in the small intestine. Even 25–100 mg of vitamin C can increase non-heme iron absorption by 2–4x.",
             "source_name": NIH, "source_url": NIH_IRON},
            {"helper_name": "Meat / Fish / Poultry (MFP factor)", "helper_type": "food",
             "description": "A substance in meat, fish, and poultry enhances non-heme iron absorption when both are consumed in the same meal.",
             "source_name": NIH, "source_url": NIH_IRON},
        ],
        blockers=[
            {"blocker_name": "Calcium", "blocker_type": "nutrient",
             "description": "Calcium inhibits absorption of both heme and non-heme iron when consumed simultaneously. Avoid taking calcium supplements with iron-rich meals.",
             "source_name": NIH, "source_url": NIH_IRON},
            {"blocker_name": "Phytic Acid (Phytates)", "blocker_type": "food",
             "description": "Phytates in whole grains, legumes, and nuts bind iron and reduce its absorption. Soaking, fermenting, or sprouting reduces phytate content.",
             "source_name": NIH, "source_url": NIH_IRON},
            {"blocker_name": "Tannins (in Tea and Coffee)", "blocker_type": "food",
             "description": "Polyphenols, especially tannins in black tea and coffee, bind non-heme iron and can reduce absorption by 50–60%. Avoid drinking tea/coffee with iron-rich meals.",
             "source_name": HARVARD, "source_url": HARVARD_URL},
        ],
        body_roles=[
            {"body_system": "Oxygen Transport", "explanation": "Iron is the central atom of hemoglobin in red blood cells. It binds and transports oxygen from the lungs to tissues, and returns carbon dioxide to the lungs.",
             "deficiency_signs": "Iron-deficiency anemia: fatigue, weakness, pale skin, shortness of breath, cold hands/feet, brittle nails.",
             "source_name": NIH, "source_url": NIH_IRON},
            {"body_system": "Energy Metabolism", "explanation": "Iron is a component of myoglobin in muscles and is essential for enzymes involved in cellular energy production (electron transport chain).",
             "source_name": NIH, "source_url": NIH_IRON},
        ],
        rda_values=[
            {"age_group": "19–50 years", "sex": "male", "value": 8, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 45, "source_name": NIH, "source_url": NIH_IRON},
            {"age_group": "19–50 years", "sex": "female", "value": 18, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 45, "source_name": NIH, "source_url": NIH_IRON},
            {"age_group": "51+ years", "sex": "all", "value": 8, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 45, "source_name": NIH, "source_url": NIH_IRON},
            {"age_group": "9–13 years", "sex": "all", "value": 8, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 40, "source_name": NIH, "source_url": NIH_IRON},
            {"age_group": "Pregnancy (19–50 years)", "sex": "pregnant", "value": 27, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 45, "source_name": NIH, "source_url": NIH_IRON},
        ],
    )

    # ── 8. Calcium ───────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Calcium", category="Minerals", solubility=None,
        synonyms=["Ca", "calcium carbonate", "calcium citrate", "calcium phosphate", "calcium gluconate"],
        food_sources=[
            {"food_name": "Plain Yogurt (low-fat)", "serving_size": "8 oz (245g)", "amount": 415, "unit": "mg",
             "bioavailability_note": "Dairy calcium is among the most bioavailable forms; absorption rate ~30–35%.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
            {"food_name": "Mozzarella Cheese", "serving_size": "1.5 oz (42g)", "amount": 333, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sardines (canned in oil, with bones)", "serving_size": "3 oz (85g)", "amount": 325, "unit": "mg",
             "bioavailability_note": "The soft, edible bones are an excellent source of bioavailable calcium.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
            {"food_name": "Cheddar Cheese", "serving_size": "1.5 oz (42g)", "amount": 307, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Milk (whole)", "serving_size": "1 cup (244ml)", "amount": 306, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Fortified Soy Milk", "serving_size": "1 cup (244ml)", "amount": 300, "unit": "mg",
             "bioavailability_note": "Absorption of calcium from fortified soy milk is similar to cow's milk.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
            {"food_name": "Kale (cooked)", "serving_size": "1 cup (130g)", "amount": 94, "unit": "mg",
             "bioavailability_note": "Kale has low oxalate content, so its calcium (non-dairy) is well absorbed (~50% bioavailability).",
             "source_name": NIH, "source_url": NIH_CALCIUM},
        ],
        helpers=[
            {"helper_name": "Vitamin D", "helper_type": "nutrient",
             "description": "Vitamin D increases the production of calcium-binding proteins in the intestinal lining, enabling active calcium absorption. Without vitamin D, only 10–15% of dietary calcium is absorbed passively.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
            {"helper_name": "Magnesium", "helper_type": "nutrient",
             "description": "Magnesium regulates calcium transport across cell membranes and bone metabolism. An adequate magnesium intake supports calcium's role in bone health.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
        ],
        blockers=[
            {"blocker_name": "Oxalates", "blocker_type": "food",
             "description": "Oxalic acid in spinach, beet greens, and rhubarb binds calcium in the gut, forming insoluble calcium oxalate and dramatically reducing absorption. Calcium in spinach has only ~5% bioavailability.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
            {"blocker_name": "High Sodium Diet", "blocker_type": "food",
             "description": "High sodium intake increases urinary calcium excretion. For every 2,300 mg of sodium consumed, about 40 mg of calcium is lost in urine.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
            {"blocker_name": "Phytic Acid (Phytates)", "blocker_type": "food",
             "description": "Phytates in grains and legumes bind calcium, reducing its absorption. Soaking or fermenting grains reduces phytate levels.",
             "source_name": HARVARD, "source_url": HARVARD_URL},
        ],
        body_roles=[
            {"body_system": "Skeletal System", "explanation": "About 99% of the body's calcium is stored in bones and teeth, where it provides structural strength and serves as a calcium reservoir. Adequate intake throughout life reduces osteoporosis risk.",
             "deficiency_signs": "Hypocalcemia: muscle cramps, tetany, numbness; long-term: osteopenia, osteoporosis.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
            {"body_system": "Neuromuscular Function", "explanation": "Calcium ions are essential for nerve impulse transmission, muscle contraction (including the heartbeat), and blood clotting.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
        ],
        rda_values=[
            {"age_group": "19–50 years", "sex": "all", "value": 1000, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 2500, "source_name": NIH, "source_url": NIH_CALCIUM},
            {"age_group": "51–70 years", "sex": "male", "value": 1000, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 2000, "source_name": NIH, "source_url": NIH_CALCIUM},
            {"age_group": "51–70 years", "sex": "female", "value": 1200, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 2000, "source_name": NIH, "source_url": NIH_CALCIUM},
            {"age_group": "71+ years", "sex": "all", "value": 1200, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 2000, "source_name": NIH, "source_url": NIH_CALCIUM},
            {"age_group": "9–18 years", "sex": "all", "value": 1300, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 3000, "source_name": NIH, "source_url": NIH_CALCIUM},
        ],
    )

    # ── 9. Zinc ──────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Zinc", category="Minerals", solubility=None,
        synonyms=["Zn", "zinc sulfate", "zinc gluconate", "zinc acetate", "zinc picolinate"],
        food_sources=[
            {"food_name": "Oysters (eastern, cooked)", "serving_size": "3 oz (85g)", "amount": 74.0, "unit": "mg",
             "bioavailability_note": "Oysters contain more zinc per serving than any other food.",
             "source_name": NIH, "source_url": NIH_ZINC},
            {"food_name": "Beef Chuck Roast (braised)", "serving_size": "3 oz (85g)", "amount": 7.0, "unit": "mg",
             "bioavailability_note": "Zinc from animal sources (heme proteins) is better absorbed than from plant sources.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Alaska King Crab (cooked)", "serving_size": "3 oz (85g)", "amount": 6.5, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Lobster (cooked)", "serving_size": "3 oz (85g)", "amount": 3.4, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Pork Chop (bone-in, cooked)", "serving_size": "3 oz (85g)", "amount": 2.9, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Baked Beans (canned, plain)", "serving_size": "1/2 cup (127g)", "amount": 2.9, "unit": "mg",
             "bioavailability_note": "Plant-based zinc has lower bioavailability due to phytate content.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Pumpkin Seeds (dry roasted)", "serving_size": "1 oz (28g)", "amount": 2.2, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Animal Protein", "helper_type": "food",
             "description": "Amino acids in meat, fish, and poultry (especially cysteine and histidine) enhance zinc solubility in the gut and improve its absorption.",
             "source_name": NIH, "source_url": NIH_ZINC},
        ],
        blockers=[
            {"blocker_name": "Phytic Acid (Phytates)", "blocker_type": "food",
             "description": "Phytates in legumes, whole grains, and seeds are the main dietary inhibitor of zinc absorption. They bind zinc in the gut to form insoluble complexes. Soaking, sprouting, or fermenting reduces phytate content.",
             "source_name": NIH, "source_url": NIH_ZINC},
            {"blocker_name": "High-Dose Calcium Supplements", "blocker_type": "nutrient",
             "description": "Calcium supplements at doses above 600 mg can interfere with zinc absorption when taken together.",
             "source_name": NIH, "source_url": NIH_ZINC},
            {"blocker_name": "High-Dose Iron Supplements", "blocker_type": "nutrient",
             "description": "Supplemental iron at doses of 25 mg or more can inhibit zinc absorption by competing for the same transporters.",
             "source_name": NIH, "source_url": NIH_ZINC},
        ],
        body_roles=[
            {"body_system": "Immune System", "explanation": "Zinc is essential for the normal development and function of immune cells (neutrophils, T-lymphocytes, B-lymphocytes). It acts as a signal molecule in immune responses.",
             "deficiency_signs": "Impaired immune function, increased infections, poor wound healing, growth retardation in children.",
             "source_name": NIH, "source_url": NIH_ZINC},
            {"body_system": "Wound Healing", "explanation": "Zinc is required for cell proliferation, protein synthesis, and collagen formation during wound healing. It also acts as a cofactor for over 300 enzymes.",
             "source_name": NIH, "source_url": NIH_ZINC},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "male", "value": 11, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 40, "source_name": NIH, "source_url": NIH_ZINC},
            {"age_group": "19+ years", "sex": "female", "value": 8, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 40, "source_name": NIH, "source_url": NIH_ZINC},
            {"age_group": "9–13 years", "sex": "all", "value": 8, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 23, "source_name": NIH, "source_url": NIH_ZINC},
            {"age_group": "Pregnancy (19–50 years)", "sex": "pregnant", "value": 11, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 40, "source_name": NIH, "source_url": NIH_ZINC},
            {"age_group": "Lactation (19–50 years)", "sex": "lactating", "value": 12, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 40, "source_name": NIH, "source_url": NIH_ZINC},
        ],
    )

    # ── 10. Magnesium ────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Magnesium", category="Macronutrients", solubility=None,
        synonyms=["Mg", "magnesium citrate", "magnesium glycinate", "magnesium oxide", "magnesium malate"],
        food_sources=[
            {"food_name": "Pumpkin Seeds (roasted)", "serving_size": "1 oz (28g)", "amount": 156, "unit": "mg",
             "source_name": NIH, "source_url": NIH_MAG},
            {"food_name": "Chia Seeds", "serving_size": "1 oz (28g)", "amount": 111, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Almonds (dry roasted)", "serving_size": "1 oz (28g)", "amount": 80, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Spinach (boiled)", "serving_size": "1/2 cup (90g)", "amount": 78, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Cashews (dry roasted)", "serving_size": "1 oz (28g)", "amount": 74, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Black Beans (cooked)", "serving_size": "1/2 cup (86g)", "amount": 60, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Edamame (shelled, cooked)", "serving_size": "1/2 cup (78g)", "amount": 50, "unit": "mg",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Vitamin D", "helper_type": "nutrient",
             "description": "Magnesium is required to activate enzymes that convert vitamin D to its active form (calcitriol). The two nutrients are mutually dependent.",
             "source_name": NIH, "source_url": NIH_MAG},
            {"helper_name": "Vitamin B6", "helper_type": "nutrient",
             "description": "Vitamin B6 increases intracellular magnesium retention and may enhance its cellular uptake.",
             "source_name": CLEVELAND, "source_url": "https://my.clevelandclinic.org/health/articles/17606-magnesium-rich-food"},
        ],
        blockers=[
            {"blocker_name": "Excessive Alcohol", "blocker_type": "food",
             "description": "Alcohol increases urinary magnesium excretion and is a major cause of magnesium deficiency in heavy drinkers.",
             "source_name": NIH, "source_url": NIH_MAG},
            {"blocker_name": "High-Dose Zinc Supplements", "blocker_type": "nutrient",
             "description": "Supplemental zinc at doses above 142 mg/day can interfere with magnesium absorption.",
             "source_name": NIH, "source_url": NIH_MAG},
        ],
        body_roles=[
            {"body_system": "Energy Metabolism", "explanation": "Magnesium is a cofactor in more than 300 enzymatic reactions, including those involved in ATP synthesis, protein synthesis, and DNA replication. Every reaction that uses ATP requires magnesium as a cofactor.",
             "deficiency_signs": "Muscle cramps, fatigue, weakness, irregular heartbeat; severe deficiency: tetany, seizures.",
             "source_name": NIH, "source_url": NIH_MAG},
            {"body_system": "Nervous System", "explanation": "Magnesium regulates NMDA receptor activity, playing a key role in nerve signal transmission and neuroprotection. It also regulates calcium channels in neurons.",
             "source_name": NIH, "source_url": NIH_MAG},
        ],
        rda_values=[
            # UL is 350 mg/day for supplemental magnesium only (not food sources)
            {"age_group": "19–30 years", "sex": "male", "value": 400, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 350, "source_name": NIH, "source_url": NIH_MAG},
            {"age_group": "31+ years", "sex": "male", "value": 420, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 350, "source_name": NIH, "source_url": NIH_MAG},
            {"age_group": "19–30 years", "sex": "female", "value": 310, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 350, "source_name": NIH, "source_url": NIH_MAG},
            {"age_group": "31+ years", "sex": "female", "value": 320, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 350, "source_name": NIH, "source_url": NIH_MAG},
            {"age_group": "9–13 years", "sex": "all", "value": 240, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 350, "source_name": NIH, "source_url": NIH_MAG},
        ],
    )

    # ── Extra food sources for existing nutrients ───────────────────────────
    _expand_food_sources(db)

    # ── New Fatty Acid nutrients ─────────────────────────────────────────────
    _seed_fatty_acids(db)

    # ── All remaining vitamins, minerals, and macronutrients ─────────────────
    _seed_extended_nutrients(db)

    db.commit()
    print(f"Seeded {db.query(Nutrient).count()} nutrients successfully.")


NIH_OMEGA3 = "https://ods.od.nih.gov/factsheets/Omega3FattyAcids-HealthProfessional/"
NIH_OMEGA6 = "https://ods.od.nih.gov/factsheets/omega6fattyacids-healthprofessional/"
HARVARD_FATS = "https://www.hsph.harvard.edu/nutritionsource/what-should-you-eat/fats-and-cholesterol/"
CLEVELAND_FATS = "https://my.clevelandclinic.org/health/articles/11208-fat-what-you-need-to-know"


def _expand_food_sources(db: Session) -> None:
    """Add more food source rows to existing nutrients."""
    extra: dict[str, list[dict]] = {
        "Vitamin A": [
            {"food_name": "Butternut Squash (cooked)", "serving_size": "1/2 cup cubed (102g)",
             "amount": 572, "unit": "mcg",
             "bioavailability_note": "Beta-carotene; absorption enhanced with fat.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Kale (raw)", "serving_size": "1 cup chopped (67g)",
             "amount": 206, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Apricot (dried)", "serving_size": "5 halves (19g)",
             "amount": 63, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Fortified Cereal (Total®)", "serving_size": "3/4 cup (30g)",
             "amount": 150, "unit": "mcg",
             "bioavailability_note": "Synthetic retinol; highly bioavailable.",
             "source_name": NIH, "source_url": NIH_VIT_A},
            {"food_name": "Pumpkin (canned)", "serving_size": "1/2 cup (122g)",
             "amount": 953, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
        ],
        "Vitamin D": [
            {"food_name": "Herring (pickled)", "serving_size": "3 oz (85g)",
             "amount": 182, "unit": "IU", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Beef Liver (braised)", "serving_size": "3 oz (85g)",
             "amount": 42, "unit": "IU", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Fortified Yogurt", "serving_size": "6 oz (170g)",
             "amount": 80, "unit": "IU",
             "bioavailability_note": "Fortification levels vary by brand; check label.",
             "source_name": NIH, "source_url": NIH_VIT_D},
            {"food_name": "Rainbow Trout (farmed, cooked)", "serving_size": "3 oz (85g)",
             "amount": 645, "unit": "IU",
             "bioavailability_note": "One of the richest dietary sources of vitamin D3.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Mushrooms (UV-exposed, raw)", "serving_size": "1/2 cup (48g)",
             "amount": 366, "unit": "IU",
             "bioavailability_note": "Mushrooms exposed to UV light generate vitamin D2 (ergocalciferol).",
             "preparation_note": "Place gill-side up in direct sunlight for 15–30 min to boost vitamin D content.",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        "Vitamin E": [
            {"food_name": "Avocado (raw)", "serving_size": "1/2 medium (68g)",
             "amount": 2.1, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Olive Oil (extra virgin)", "serving_size": "1 tbsp (13.5g)",
             "amount": 1.9, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Spinach (raw)", "serving_size": "1 cup (30g)",
             "amount": 0.6, "unit": "mg",
             "preparation_note": "Lightly cook to reduce oxalates; still provides modest vitamin E.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Mango (raw)", "serving_size": "1 cup sliced (165g)",
             "amount": 1.5, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Pine Nuts (dried)", "serving_size": "1 oz (28g)",
             "amount": 2.6, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
        "Vitamin C": [
            {"food_name": "Guava (raw)", "serving_size": "1 medium (55g)",
             "amount": 126, "unit": "mg",
             "bioavailability_note": "One of the richest food sources of vitamin C per gram.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Papaya (raw)", "serving_size": "1 cup cubed (145g)",
             "amount": 87, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Brussels Sprouts (cooked)", "serving_size": "1/2 cup (78g)",
             "amount": 48, "unit": "mg",
             "preparation_note": "Brief steaming preserves more vitamin C than boiling.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Blackcurrants (raw)", "serving_size": "1/2 cup (56g)",
             "amount": 101, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Pineapple (raw)", "serving_size": "1 cup chunks (165g)",
             "amount": 79, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Lemon Juice (fresh)", "serving_size": "1/4 cup (61ml)",
             "amount": 23, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Cauliflower (raw)", "serving_size": "1/2 cup (50g)",
             "amount": 26, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
        "Vitamin B12": [
            {"food_name": "Nutritional Yeast (fortified)", "serving_size": "2 tbsp (16g)",
             "amount": 4.8, "unit": "mcg",
             "bioavailability_note": "Ideal plant-based source; cyanocobalamin is well absorbed.",
             "source_name": NIH, "source_url": NIH_VIT_B12},
            {"food_name": "Mackerel (Atlantic, cooked)", "serving_size": "3 oz (85g)",
             "amount": 16.1, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Trout (rainbow, cooked)", "serving_size": "3 oz (85g)",
             "amount": 3.5, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Ham (cured, roasted)", "serving_size": "3 oz (85g)",
             "amount": 0.6, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Swiss Cheese", "serving_size": "1.5 oz (42g)",
             "amount": 0.8, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
        ],
        "Vitamin B9": [
            {"food_name": "Edamame (shelled, boiled)", "serving_size": "1/2 cup (78g)",
             "amount": 241, "unit": "mcg DFE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Romaine Lettuce (raw)", "serving_size": "1 cup shredded (47g)",
             "amount": 64, "unit": "mcg DFE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Avocado (raw)", "serving_size": "1/2 medium (68g)",
             "amount": 59, "unit": "mcg DFE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Beets (boiled)", "serving_size": "1/2 cup sliced (85g)",
             "amount": 68, "unit": "mcg DFE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Kidney Beans (canned)", "serving_size": "1/2 cup (128g)",
             "amount": 46, "unit": "mcg DFE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Orange (raw)", "serving_size": "1 medium (131g)",
             "amount": 40, "unit": "mcg DFE", "source_name": USDA, "source_url": USDA_URL},
        ],
        "Iron": [
            {"food_name": "Pumpkin Seeds (roasted)", "serving_size": "1 oz (28g)",
             "amount": 2.5, "unit": "mg",
             "bioavailability_note": "Non-heme iron; pair with vitamin C to boost absorption.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Fortified Breakfast Cereal", "serving_size": "3/4 cup (30g)",
             "amount": 18.0, "unit": "mg",
             "bioavailability_note": "Synthetic iron (often ferrous sulfate); highly bioavailable.",
             "source_name": NIH, "source_url": NIH_IRON},
            {"food_name": "Chickpeas (canned)", "serving_size": "1/2 cup (120g)",
             "amount": 2.4, "unit": "mg",
             "bioavailability_note": "Non-heme iron; combine with bell pepper or orange juice for better absorption.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Tofu (firm)", "serving_size": "1/2 cup (126g)",
             "amount": 3.4, "unit": "mg",
             "bioavailability_note": "Non-heme iron; best absorbed when consumed with vitamin C.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Quinoa (cooked)", "serving_size": "1 cup (185g)",
             "amount": 2.8, "unit": "mg",
             "bioavailability_note": "Contains all essential amino acids and non-heme iron.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Chicken Breast (roasted)", "serving_size": "3 oz (85g)",
             "amount": 0.9, "unit": "mg",
             "bioavailability_note": "Heme iron; directly absorbed without vitamin C needed.",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        "Calcium": [
            {"food_name": "Collard Greens (cooked)", "serving_size": "1 cup (190g)",
             "amount": 268, "unit": "mg",
             "bioavailability_note": "Low oxalate; calcium bioavailability (~40%) rivals milk.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
            {"food_name": "Bok Choy (cooked)", "serving_size": "1 cup (170g)",
             "amount": 158, "unit": "mg",
             "bioavailability_note": "Low oxalate; well-absorbed plant calcium source.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "White Beans (canned)", "serving_size": "1/2 cup (131g)",
             "amount": 96, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Almonds (dry roasted)", "serving_size": "1 oz (28g)",
             "amount": 76, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Calcium-set Tofu (firm)", "serving_size": "1/2 cup (126g)",
             "amount": 434, "unit": "mg",
             "bioavailability_note": "Calcium sulfate-set tofu is an excellent plant-based calcium source.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
            {"food_name": "Ricotta Cheese (part-skim)", "serving_size": "1/2 cup (124g)",
             "amount": 337, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
        "Zinc": [
            {"food_name": "Hemp Seeds (hulled)", "serving_size": "3 tbsp (30g)",
             "amount": 3.0, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Cashews (dry roasted)", "serving_size": "1 oz (28g)",
             "amount": 1.6, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Chicken Leg (roasted)", "serving_size": "3 oz (85g)",
             "amount": 2.7, "unit": "mg",
             "bioavailability_note": "Heme zinc from poultry has higher bioavailability than plant sources.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Fortified Breakfast Cereal", "serving_size": "3/4 cup (30g)",
             "amount": 3.8, "unit": "mg",
             "bioavailability_note": "Synthetic zinc; well absorbed without phytate interference.",
             "source_name": NIH, "source_url": NIH_ZINC},
            {"food_name": "Swiss Cheese", "serving_size": "1.5 oz (42g)",
             "amount": 1.2, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Lentils (cooked)", "serving_size": "1/2 cup (99g)",
             "amount": 1.3, "unit": "mg",
             "bioavailability_note": "Non-heme zinc; soak or sprout to reduce phytates.",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        "Magnesium": [
            {"food_name": "Dark Chocolate (70–85% cacao)", "serving_size": "1 oz (28g)",
             "amount": 64, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Avocado (raw)", "serving_size": "1/2 medium (68g)",
             "amount": 22, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Banana (raw)", "serving_size": "1 medium (118g)",
             "amount": 32, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Salmon (Atlantic, cooked)", "serving_size": "3 oz (85g)",
             "amount": 26, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Brown Rice (cooked)", "serving_size": "1 cup (195g)",
             "amount": 84, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Tofu (firm)", "serving_size": "1/2 cup (126g)",
             "amount": 37, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Whole Wheat Bread", "serving_size": "2 slices (56g)",
             "amount": 46, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
    }

    for nutrient_name, foods in extra.items():
        nutrient = db.query(Nutrient).filter(Nutrient.name == nutrient_name).first()
        if not nutrient:
            continue
        for fs in foods:
            # Avoid duplicates (check by food_name + nutrient_id)
            exists = (
                db.query(NutrientFoodSource)
                .filter(
                    NutrientFoodSource.nutrient_id == nutrient.id,
                    NutrientFoodSource.food_name == fs["food_name"],
                )
                .first()
            )
            if exists:
                continue
            src = get_or_create_source(db, fs["source_name"], fs["source_url"])
            db.add(NutrientFoodSource(
                nutrient_id=nutrient.id,
                food_name=fs["food_name"],
                serving_size=fs["serving_size"],
                amount=fs["amount"],
                unit=fs["unit"],
                bioavailability_note=fs.get("bioavailability_note"),
                preparation_note=fs.get("preparation_note"),
                source_id=src.id,
            ))
    db.flush()


def _seed_fatty_acids(db: Session) -> None:
    """Seed three Fatty Acids nutrients: Omega-3, Omega-6, and Omega-9."""

    # ── Omega-3 Fatty Acids ──────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Omega-3 Fatty Acids", category="Fatty Acids", solubility="fat-soluble",
        synonyms=[
            "ALA", "alpha-linolenic acid", "EPA", "eicosapentaenoic acid",
            "DHA", "docosahexaenoic acid", "fish oil", "omega 3",
        ],
        food_sources=[
            {"food_name": "Salmon (Atlantic, farmed, cooked)", "serving_size": "3 oz (85g)",
             "amount": 1.8, "unit": "g",
             "bioavailability_note": "Rich in EPA and DHA — the most bioavailable forms of omega-3.",
             "source_name": NIH, "source_url": NIH_OMEGA3},
            {"food_name": "Mackerel (Atlantic, cooked)", "serving_size": "3 oz (85g)",
             "amount": 1.0, "unit": "g",
             "bioavailability_note": "High EPA+DHA content; well absorbed.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sardines (canned in oil)", "serving_size": "3 oz (85g)",
             "amount": 1.4, "unit": "g",
             "bioavailability_note": "Good source of EPA and DHA; the oil in the can retains omega-3s.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Flaxseed (ground)", "serving_size": "1 tbsp (10g)",
             "amount": 2.4, "unit": "g",
             "bioavailability_note": "Provides ALA; the body converts only 5–10% of ALA to EPA/DHA. Ground flaxseed is better absorbed than whole seeds.",
             "preparation_note": "Grind before consuming — whole seeds pass through undigested.",
             "source_name": NIH, "source_url": NIH_OMEGA3},
            {"food_name": "Chia Seeds", "serving_size": "1 oz (28g)",
             "amount": 5.1, "unit": "g",
             "bioavailability_note": "Plant-based ALA; richest single-food source of omega-3 by weight.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Walnuts (English)", "serving_size": "1 oz (28g)",
             "amount": 2.6, "unit": "g",
             "bioavailability_note": "Rich in ALA; the only tree nut with significant omega-3 content.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Herring (Atlantic, cooked)", "serving_size": "3 oz (85g)",
             "amount": 1.7, "unit": "g",
             "bioavailability_note": "Excellent EPA+DHA source; similar to salmon.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Anchovies (canned in oil)", "serving_size": "2 oz (57g)",
             "amount": 1.2, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Algae Oil (DHA supplement)", "serving_size": "1 tsp (5ml)",
             "amount": 0.9, "unit": "g",
             "bioavailability_note": "Vegan DHA directly from microalgae — the original source fish get their DHA from. Bioavailability equivalent to fish-derived DHA.",
             "source_name": NIH, "source_url": NIH_OMEGA3},
            {"food_name": "Fortified Eggs (DHA-enriched)", "serving_size": "1 large egg (50g)",
             "amount": 0.17, "unit": "g",
             "bioavailability_note": "Hens fed flaxseed or algae produce eggs with higher DHA.",
             "source_name": NIH, "source_url": NIH_OMEGA3},
            {"food_name": "Hemp Seeds (hulled)", "serving_size": "3 tbsp (30g)",
             "amount": 2.6, "unit": "g",
             "bioavailability_note": "ALA source; also provides a favourable omega-6:omega-3 ratio (~3:1).",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Vitamin E", "helper_type": "nutrient",
             "description": "Vitamin E protects EPA and DHA from oxidative damage in the body and in food storage. Consuming omega-3s with vitamin E-rich foods helps preserve their biological activity.",
             "source_name": NIH, "source_url": NIH_OMEGA3},
            {"helper_name": "Astaxanthin", "helper_type": "nutrient",
             "description": "This carotenoid antioxidant (found in salmon and shrimp) protects omega-3 fatty acids from lipid peroxidation, enhancing their stability and effectiveness.",
             "source_name": HARVARD, "source_url": HARVARD_FATS},
        ],
        blockers=[
            {"blocker_name": "Excessive Omega-6 Fatty Acids", "blocker_type": "nutrient",
             "description": "Omega-6 and omega-3 fatty acids compete for the same desaturase enzymes. A diet very high in omega-6s (vegetable oils, processed foods) reduces conversion of ALA to EPA/DHA.",
             "source_name": NIH, "source_url": NIH_OMEGA3},
            {"blocker_name": "Trans Fats", "blocker_type": "food",
             "description": "Partially hydrogenated oils (trans fats) interfere with the enzymes that metabolize omega-3 fatty acids, reducing their incorporation into cell membranes.",
             "source_name": HARVARD, "source_url": HARVARD_FATS},
        ],
        body_roles=[
            {"body_system": "Cardiovascular", "explanation": "EPA and DHA reduce triglyceride levels, decrease inflammation in blood vessels, modestly lower blood pressure, and reduce the risk of arrhythmia. Observational data links regular oily fish consumption to lower cardiovascular mortality.",
             "deficiency_signs": "Rough, scaly skin; poor wound healing; increased inflammatory markers; in infants: impaired visual and cognitive development.",
             "source_name": NIH, "source_url": NIH_OMEGA3},
            {"body_system": "Brain and Nervous System", "explanation": "DHA is the predominant structural fatty acid in the brain's grey matter and retina. It is essential for synaptic membrane fluidity, neurotransmitter signalling, and visual acuity. Adequate DHA during pregnancy supports fetal brain development.",
             "source_name": NIH, "source_url": NIH_OMEGA3},
            {"body_system": "Immune / Anti-inflammatory", "explanation": "EPA and DHA are precursors to resolvins and protectins — signalling molecules that actively resolve inflammation, supporting immune balance and reducing chronic low-grade inflammation.",
             "source_name": HARVARD, "source_url": HARVARD_FATS},
        ],
        rda_values=[
            # No established RDA; only AI values
            {"age_group": "19+ years", "sex": "male", "value": 1.6, "unit": "g ALA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA3},
            {"age_group": "19+ years", "sex": "female", "value": 1.1, "unit": "g ALA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA3},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 1.4, "unit": "g ALA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA3},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 1.3, "unit": "g ALA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA3},
            {"age_group": "9–13 years", "sex": "male", "value": 1.2, "unit": "g ALA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA3},
            {"age_group": "9–13 years", "sex": "female", "value": 1.0, "unit": "g ALA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA3},
        ],
    )

    # ── Omega-6 Fatty Acids ──────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Omega-6 Fatty Acids", category="Fatty Acids", solubility="fat-soluble",
        synonyms=[
            "linoleic acid", "LA", "arachidonic acid", "AA", "GLA",
            "gamma-linolenic acid", "omega 6",
        ],
        food_sources=[
            {"food_name": "Safflower Oil (high-linoleic)", "serving_size": "1 tbsp (13.6g)",
             "amount": 10.1, "unit": "g",
             "bioavailability_note": "Highest omega-6 content of common cooking oils.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sunflower Oil", "serving_size": "1 tbsp (13.6g)",
             "amount": 8.9, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Corn Oil", "serving_size": "1 tbsp (13.6g)",
             "amount": 7.3, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Soybeans (cooked)", "serving_size": "1/2 cup (90g)",
             "amount": 5.9, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Walnuts (English)", "serving_size": "1 oz (28g)",
             "amount": 10.8, "unit": "g",
             "bioavailability_note": "Walnuts provide both omega-6 (LA) and omega-3 (ALA), but omega-6 predominates at roughly 4:1.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Pumpkin Seeds (roasted)", "serving_size": "1 oz (28g)",
             "amount": 5.8, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sesame Oil", "serving_size": "1 tbsp (13.6g)",
             "amount": 5.6, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Evening Primrose Oil", "serving_size": "1 g capsule",
             "amount": 0.09, "unit": "g",
             "bioavailability_note": "Rich in GLA (gamma-linolenic acid), a precursor to anti-inflammatory eicosanoids.",
             "source_name": NIH, "source_url": NIH_OMEGA6},
            {"food_name": "Pine Nuts", "serving_size": "1 oz (28g)",
             "amount": 9.7, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Tofu (firm)", "serving_size": "1/2 cup (126g)",
             "amount": 2.9, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Chicken Breast (roasted)", "serving_size": "3 oz (85g)",
             "amount": 1.0, "unit": "g",
             "bioavailability_note": "Arachidonic acid (AA) from animal foods is directly usable by the body.",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Dietary Fat (meal context)", "helper_type": "food",
             "description": "Omega-6 fatty acids are fat-soluble. Consuming them as part of a fat-containing meal improves their absorption in the small intestine.",
             "source_name": HARVARD, "source_url": HARVARD_FATS},
        ],
        blockers=[
            {"blocker_name": "Trans Fats", "blocker_type": "food",
             "description": "Trans fatty acids compete with linoleic acid for desaturase enzymes, impairing the conversion of omega-6 fatty acids to their active forms.",
             "source_name": HARVARD, "source_url": HARVARD_FATS},
            {"blocker_name": "Excessive Omega-3 Intake", "blocker_type": "nutrient",
             "description": "Very high omega-3 intake can suppress arachidonic acid synthesis from linoleic acid by competing for the same elongase and desaturase enzymes.",
             "source_name": NIH, "source_url": NIH_OMEGA6},
        ],
        body_roles=[
            {"body_system": "Cell Membrane Structure", "explanation": "Linoleic acid (LA) and arachidonic acid (AA) are critical structural components of every cell membrane. They maintain fluidity, permeability, and the function of membrane-bound proteins and receptors.",
             "deficiency_signs": "Dry scaly dermatitis; poor wound healing; hair loss; impaired immune function. Deficiency is rare in adults eating a mixed diet.",
             "source_name": NIH, "source_url": NIH_OMEGA6},
            {"body_system": "Immune and Inflammatory Signalling", "explanation": "Arachidonic acid is a precursor to prostaglandins, leukotrienes, and thromboxanes — eicosanoids that regulate inflammation, blood clotting, and immune responses. These are pro-inflammatory in excess but essential for normal immune function.",
             "source_name": HARVARD, "source_url": HARVARD_FATS},
        ],
        rda_values=[
            {"age_group": "19–50 years", "sex": "male", "value": 17, "unit": "g LA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA6},
            {"age_group": "19–50 years", "sex": "female", "value": 12, "unit": "g LA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA6},
            {"age_group": "51+ years", "sex": "male", "value": 14, "unit": "g LA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA6},
            {"age_group": "51+ years", "sex": "female", "value": 11, "unit": "g LA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA6},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 13, "unit": "g LA", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_OMEGA6},
        ],
    )

    # ── Omega-9 Fatty Acids (Monounsaturated) ───────────────────────────────
    seed_nutrient(
        db=db, name="Omega-9 Fatty Acids", category="Fatty Acids", solubility="fat-soluble",
        synonyms=[
            "oleic acid", "monounsaturated fat", "MUFA",
            "erucic acid", "omega 9",
        ],
        food_sources=[
            {"food_name": "Olive Oil (extra virgin)", "serving_size": "1 tbsp (13.5g)",
             "amount": 9.9, "unit": "g",
             "bioavailability_note": "Richest common dietary source of oleic acid. Cold-pressed extra virgin oil retains antioxidant polyphenols.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Avocado (raw)", "serving_size": "1/2 medium (68g)",
             "amount": 6.7, "unit": "g",
             "bioavailability_note": "Whole-food source of oleic acid with fat-soluble vitamins and fibre.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Almonds (dry roasted)", "serving_size": "1 oz (28g)",
             "amount": 9.1, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Canola Oil", "serving_size": "1 tbsp (14g)",
             "amount": 8.9, "unit": "g",
             "bioavailability_note": "High MUFA content; also contains some ALA (omega-3).",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Peanut Butter (smooth)", "serving_size": "2 tbsp (32g)",
             "amount": 7.6, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Macadamia Nuts", "serving_size": "1 oz (28g)",
             "amount": 16.5, "unit": "g",
             "bioavailability_note": "Highest MUFA content of all tree nuts.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Hazelnuts (dry roasted)", "serving_size": "1 oz (28g)",
             "amount": 12.9, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sunflower Oil (high-oleic)", "serving_size": "1 tbsp (13.6g)",
             "amount": 11.7, "unit": "g",
             "bioavailability_note": "High-oleic variety has been selectively bred for MUFA content, unlike regular sunflower oil.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sesame Seeds (whole, dried)", "serving_size": "1 tbsp (9g)",
             "amount": 2.3, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Salmon (Atlantic, farmed, cooked)", "serving_size": "3 oz (85g)",
             "amount": 3.7, "unit": "g",
             "bioavailability_note": "Animal sources provide oleic acid alongside EPA/DHA omega-3s.",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Polyphenols (in olive oil)", "helper_type": "food",
             "description": "The polyphenols naturally present in extra-virgin olive oil (oleocanthal, oleuropein) enhance the anti-inflammatory effects of oleic acid and protect it from oxidation.",
             "source_name": HARVARD, "source_url": HARVARD_FATS},
        ],
        blockers=[
            {"blocker_name": "High Cooking Heat", "blocker_type": "food",
             "description": "While MUFAs are more stable than PUFAs, excessive heat (deep frying at very high temperatures) can degrade oleic acid and generate harmful oxidation products. Use moderate heat.",
             "source_name": CLEVELAND, "source_url": CLEVELAND_FATS},
            {"blocker_name": "Excessive Saturated Fat", "blocker_type": "nutrient",
             "description": "Diets very high in saturated fat can partially offset the cardiovascular benefits of omega-9 MUFAs by raising LDL cholesterol independently.",
             "source_name": HARVARD, "source_url": HARVARD_FATS},
        ],
        body_roles=[
            {"body_system": "Cardiovascular", "explanation": "Oleic acid raises HDL ('good') cholesterol while lowering LDL ('bad') cholesterol when it replaces saturated fat in the diet. It reduces oxidative modification of LDL, a key step in atherosclerosis. The Mediterranean diet, rich in olive oil, is associated with significantly lower cardiovascular disease rates.",
             "source_name": HARVARD, "source_url": HARVARD_FATS},
            {"body_system": "Insulin Sensitivity", "explanation": "MUFA-rich diets improve insulin receptor sensitivity compared to high-saturated-fat diets, helping regulate blood glucose levels. This is a key mechanism behind olive-oil-rich dietary patterns reducing type 2 diabetes risk.",
             "source_name": CLEVELAND, "source_url": CLEVELAND_FATS},
        ],
        rda_values=[
            # No formal RDA or AI — general recommendation is 15–20% of calories
            {"age_group": "19+ years", "sex": "all", "value": 15, "unit": "% of calories", "intake_type": "AI",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARVARD_FATS},
            {"age_group": "9–18 years", "sex": "all", "value": 25, "unit": "% of calories", "intake_type": "AI",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARVARD_FATS},
            {"age_group": "Pregnancy / Lactation", "sex": "pregnant", "value": 20, "unit": "% of calories", "intake_type": "AI",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARVARD_FATS},
        ],
    )


# ─── URL constants for extended nutrients ────────────────────────────────────
NIH_B1   = "https://ods.od.nih.gov/factsheets/Thiamin-HealthProfessional/"
NIH_B2   = "https://ods.od.nih.gov/factsheets/Riboflavin-HealthProfessional/"
NIH_B3   = "https://ods.od.nih.gov/factsheets/Niacin-HealthProfessional/"
NIH_B5   = "https://ods.od.nih.gov/factsheets/PantothenicAcid-HealthProfessional/"
NIH_B6   = "https://ods.od.nih.gov/factsheets/VitaminB6-HealthProfessional/"
NIH_B7   = "https://ods.od.nih.gov/factsheets/Biotin-HealthProfessional/"
NIH_VIT_K = "https://ods.od.nih.gov/factsheets/VitaminK-HealthProfessional/"
NIH_POT  = "https://ods.od.nih.gov/factsheets/Potassium-HealthProfessional/"
NIH_PHOS = "https://ods.od.nih.gov/factsheets/Phosphorus-HealthProfessional/"
NIH_SEL  = "https://ods.od.nih.gov/factsheets/Selenium-HealthProfessional/"
NIH_IOD  = "https://ods.od.nih.gov/factsheets/Iodine-HealthProfessional/"
NIH_COP  = "https://ods.od.nih.gov/factsheets/Copper-HealthProfessional/"
NIH_CHRO = "https://ods.od.nih.gov/factsheets/Chromium-HealthProfessional/"
NIH_MANG = "https://ods.od.nih.gov/factsheets/Manganese-HealthProfessional/"
NIH_FLUO = "https://ods.od.nih.gov/factsheets/Fluoride-HealthProfessional/"
NIH_MOL  = "https://ods.od.nih.gov/factsheets/Molybdenum-HealthProfessional/"
HARV_FIBER  = "https://www.hsph.harvard.edu/nutritionsource/carbohydrates/fiber/"
HARV_SUGAR  = "https://www.hsph.harvard.edu/nutritionsource/carbohydrates/added-sugar-in-the-diet/"
HARV_PROT   = "https://www.hsph.harvard.edu/nutritionsource/what-should-you-eat/protein/"
HARV_SODIUM = "https://www.hsph.harvard.edu/nutritionsource/salt-and-sodium/"
HARV_CARBS  = "https://www.hsph.harvard.edu/nutritionsource/carbohydrates/"
MAYO_GEN = "https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/basics/nutrition-basics/hlv-20049477"


def _seed_extended_nutrients(db: Session) -> None:  # noqa: C901
    """Seed all remaining vitamins, minerals, and macronutrients."""

    # ── Vitamin B1 (Thiamine) ────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin B1", category="Vitamins", solubility="water-soluble",
        synonyms=["thiamine", "thiamin", "aneurine", "vitamin B1", "thiamine hydrochloride",
                  "thiamine mononitrate"],
        food_sources=[
            {"food_name": "Pork Loin (roasted)", "serving_size": "3 oz (85g)",
             "amount": 0.81, "unit": "mg",
             "bioavailability_note": "Pork is the richest common dietary source of thiamine.",
             "source_name": NIH, "source_url": NIH_B1},
            {"food_name": "Black Beans (boiled)", "serving_size": "1/2 cup (86g)",
             "amount": 0.42, "unit": "mg",
             "bioavailability_note": "Plant-based thiamine; well absorbed in absence of anti-thiamine factors.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sunflower Seeds (dry roasted)", "serving_size": "1/4 cup (35g)",
             "amount": 0.43, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Fortified Breakfast Cereal", "serving_size": "3/4 cup (30g)",
             "amount": 1.5, "unit": "mg",
             "bioavailability_note": "Synthetic thiamine in fortified foods is highly bioavailable.",
             "source_name": NIH, "source_url": NIH_B1},
            {"food_name": "Lentils (boiled)", "serving_size": "1/2 cup (99g)",
             "amount": 0.17, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Macadamia Nuts (dry roasted)", "serving_size": "1 oz (28g)",
             "amount": 0.34, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "White Rice (enriched, cooked)", "serving_size": "1/2 cup (79g)",
             "amount": 0.13, "unit": "mg",
             "preparation_note": "Do not rinse enriched rice before cooking — rinsing washes away added B vitamins.",
             "source_name": NIH, "source_url": NIH_B1},
            {"food_name": "Whole Wheat Bread", "serving_size": "1 slice (28g)",
             "amount": 0.10, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Adequate Stomach Acid", "helper_type": "nutrient",
             "description": "Gastric acid cleaves thiamine from food proteins, freeing it for intestinal absorption. Conditions that reduce stomach acid (e.g., PPIs, atrophic gastritis) can impair food-bound thiamine release.",
             "source_name": NIH, "source_url": NIH_B1},
            {"helper_name": "Magnesium", "helper_type": "nutrient",
             "description": "Magnesium acts as a cofactor for thiamine-dependent enzymes (e.g., pyruvate dehydrogenase). Adequate magnesium is required for full biological activity of thiamine.",
             "source_name": NIH, "source_url": NIH_B1},
        ],
        blockers=[
            {"blocker_name": "Alcohol", "blocker_type": "food",
             "description": "Alcohol is the leading cause of thiamine deficiency worldwide. It impairs intestinal absorption, reduces hepatic storage, and increases urinary excretion of thiamine.",
             "source_name": NIH, "source_url": NIH_B1},
            {"blocker_name": "Raw Fish / Shellfish (Thiaminase)", "blocker_type": "food",
             "description": "Certain raw fish (carp, herring) and shellfish (clams, mussels) contain thiaminase, an enzyme that cleaves and inactivates thiamine. Cooking destroys thiaminase.",
             "source_name": NIH, "source_url": NIH_B1},
            {"blocker_name": "Tea and Coffee (Tannins)", "blocker_type": "food",
             "description": "Polyphenols and tannins in tea and coffee can form insoluble complexes with thiamine, reducing its bioavailability when consumed regularly with meals.",
             "source_name": MAYO, "source_url": MAYO_GEN},
        ],
        body_roles=[
            {"body_system": "Energy Metabolism", "explanation": "Thiamine pyrophosphate (TPP) is an essential coenzyme for three key metabolic complexes: pyruvate dehydrogenase (converts pyruvate to acetyl-CoA), alpha-ketoglutarate dehydrogenase (in the Krebs cycle), and branched-chain alpha-keto acid dehydrogenase. These reactions are critical for generating ATP from carbohydrates, fats, and proteins.",
             "deficiency_signs": "Beriberi (wet: cardiovascular — heart failure and peripheral oedema; dry: polyneuropathy, muscle wasting); Wernicke–Korsakoff syndrome in alcoholics (confusion, ataxia, ophthalmoplegia).",
             "source_name": NIH, "source_url": NIH_B1},
            {"body_system": "Nervous System", "explanation": "Thiamine is required for the synthesis of myelin sheaths and neurotransmitters. Neuronal membranes are especially dependent on thiamine-mediated energy production, making the brain and peripheral nerves highly vulnerable to deficiency.",
             "source_name": NIH, "source_url": NIH_B1},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "male", "value": 1.2, "unit": "mg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B1},
            {"age_group": "19+ years", "sex": "female", "value": 1.1, "unit": "mg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B1},
            {"age_group": "9–13 years", "sex": "all", "value": 0.9, "unit": "mg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B1},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 1.4, "unit": "mg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B1},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 1.4, "unit": "mg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B1},
        ],
    )

    # ── Vitamin B2 (Riboflavin) ──────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin B2", category="Vitamins", solubility="water-soluble",
        synonyms=["riboflavin", "vitamin B2", "lactoflavin", "vitamin G"],
        food_sources=[
            {"food_name": "Beef Liver (pan-fried)", "serving_size": "3 oz (85g)",
             "amount": 2.9, "unit": "mg",
             "bioavailability_note": "Liver is the most concentrated dietary source of riboflavin.",
             "source_name": NIH, "source_url": NIH_B2},
            {"food_name": "Fortified Breakfast Cereal", "serving_size": "3/4 cup (30g)",
             "amount": 1.3, "unit": "mg", "source_name": NIH, "source_url": NIH_B2},
            {"food_name": "Milk (whole)", "serving_size": "1 cup (244ml)",
             "amount": 0.44, "unit": "mg",
             "preparation_note": "Store milk in opaque containers — riboflavin is rapidly destroyed by UV/sunlight exposure.",
             "source_name": NIH, "source_url": NIH_B2},
            {"food_name": "Almonds (dry roasted)", "serving_size": "1 oz (28g)",
             "amount": 0.32, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Beef (bottom round, braised)", "serving_size": "3 oz (85g)",
             "amount": 0.27, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Mushrooms (shiitake, cooked)", "serving_size": "1/2 cup (73g)",
             "amount": 0.21, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Yogurt (plain, low-fat)", "serving_size": "8 oz (245g)",
             "amount": 0.52, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Clams (cooked)", "serving_size": "3 oz (85g)",
             "amount": 0.36, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Iron", "helper_type": "nutrient",
             "description": "Iron and riboflavin have a synergistic relationship. Riboflavin is required for the conversion of iron to its storage and transport forms. Iron deficiency can impair riboflavin metabolism and vice versa.",
             "source_name": NIH, "source_url": NIH_B2},
            {"helper_name": "Vitamin B6", "helper_type": "nutrient",
             "description": "Riboflavin (as FMN) is required to convert vitamin B6 into its active coenzyme form, pyridoxal-5-phosphate (PLP). Adequate riboflavin status is necessary to activate B6.",
             "source_name": NIH, "source_url": NIH_B2},
        ],
        blockers=[
            {"blocker_name": "Ultraviolet Light", "blocker_type": "food",
             "description": "Riboflavin is extremely photosensitive. Milk left in clear glass bottles can lose up to 50% of its riboflavin within 2 hours of light exposure. Always store milk and riboflavin-rich foods in opaque containers.",
             "source_name": NIH, "source_url": NIH_B2},
            {"blocker_name": "Alcohol", "blocker_type": "food",
             "description": "Chronic alcohol consumption impairs riboflavin absorption in the small intestine and reduces its conversion to active coenzyme forms (FMN and FAD).",
             "source_name": NIH, "source_url": NIH_B2},
        ],
        body_roles=[
            {"body_system": "Energy Production", "explanation": "Riboflavin is a component of flavin adenine dinucleotide (FAD) and flavin mononucleotide (FMN), coenzymes central to the electron transport chain and oxidative phosphorylation. Every cell depends on these flavocoenzymes to generate ATP.",
             "deficiency_signs": "Ariboflavinosis: sore throat, swollen mucous membranes, cracks at corners of mouth (angular cheilitis), magenta-coloured tongue (glossitis), seborrhoeic dermatitis.",
             "source_name": NIH, "source_url": NIH_B2},
            {"body_system": "Antioxidant Defense", "explanation": "FAD is an essential cofactor for glutathione reductase, the enzyme that regenerates reduced glutathione — the body's primary intracellular antioxidant. Riboflavin is therefore indirectly critical for protecting cells from oxidative damage.",
             "source_name": NIH, "source_url": NIH_B2},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "male", "value": 1.3, "unit": "mg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B2},
            {"age_group": "19+ years", "sex": "female", "value": 1.1, "unit": "mg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B2},
            {"age_group": "9–13 years", "sex": "all", "value": 0.9, "unit": "mg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B2},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 1.4, "unit": "mg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B2},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 1.6, "unit": "mg", "intake_type": "RDA",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B2},
        ],
    )

    # ── Vitamin B3 (Niacin) ──────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin B3", category="Vitamins", solubility="water-soluble",
        synonyms=["niacin", "nicotinic acid", "nicotinamide", "niacinamide", "vitamin B3",
                  "vitamin PP", "nicotinamide riboside", "NR", "NMN"],
        food_sources=[
            {"food_name": "Tuna (yellowfin, cooked)", "serving_size": "3 oz (85g)",
             "amount": 13.3, "unit": "mg NE",
             "bioavailability_note": "Among the richest single-serving niacin sources.",
             "source_name": NIH, "source_url": NIH_B3},
            {"food_name": "Chicken Breast (roasted)", "serving_size": "3 oz (85g)",
             "amount": 10.3, "unit": "mg NE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Turkey (roasted)", "serving_size": "3 oz (85g)",
             "amount": 9.0, "unit": "mg NE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Salmon (sockeye, cooked)", "serving_size": "3 oz (85g)",
             "amount": 8.5, "unit": "mg NE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Beef Liver (pan-fried)", "serving_size": "3 oz (85g)",
             "amount": 14.9, "unit": "mg NE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Pork Chop (bone-in, cooked)", "serving_size": "3 oz (85g)",
             "amount": 6.3, "unit": "mg NE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Mushrooms (portobello, cooked)", "serving_size": "1/2 cup (78g)",
             "amount": 3.5, "unit": "mg NE",
             "bioavailability_note": "One of the best plant-based niacin sources.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Peanut Butter (smooth)", "serving_size": "2 tbsp (32g)",
             "amount": 4.2, "unit": "mg NE", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Brown Rice (cooked)", "serving_size": "1 cup (195g)",
             "amount": 3.0, "unit": "mg NE", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Tryptophan (dietary protein)", "helper_type": "nutrient",
             "description": "The body converts the amino acid tryptophan to niacin at a ratio of ~60 mg tryptophan → 1 mg niacin (1 NE). Adequate dietary protein intake therefore provides an indirect niacin source alongside preformed niacin.",
             "source_name": NIH, "source_url": NIH_B3},
            {"helper_name": "Riboflavin (Vitamin B2) and B6", "helper_type": "nutrient",
             "description": "Riboflavin (B2) and pyridoxine (B6) are required coenzymes in the biosynthetic pathway that converts tryptophan to niacin. Deficiencies in B2 or B6 can reduce endogenous niacin synthesis.",
             "source_name": NIH, "source_url": NIH_B3},
        ],
        blockers=[
            {"blocker_name": "Corn-Based Diets Without Nixtamalization", "blocker_type": "food",
             "description": "Niacin in corn is tightly bound to polysaccharides and largely unavailable. Traditional nixtamalization (soaking and cooking corn in alkaline lime/ash) breaks these bonds and releases niacin. Populations relying on unprocessed corn without lime treatment historically developed pellagra.",
             "source_name": NIH, "source_url": NIH_B3},
            {"blocker_name": "Isoniazid (TB Medication)", "blocker_type": "nutrient",
             "description": "Isoniazid is a structural analogue that interferes with niacin metabolism. Long-term use can deplete niacin and cause pellagra-like symptoms in susceptible individuals.",
             "source_name": NIH, "source_url": NIH_B3},
        ],
        body_roles=[
            {"body_system": "Energy Metabolism", "explanation": "Niacin is a precursor for NAD (nicotinamide adenine dinucleotide) and NADP, coenzymes essential in over 400 enzymatic reactions. These include glycolysis, the Krebs cycle, fatty acid synthesis, and the pentose phosphate pathway — making niacin indispensable for every cell's energy production.",
             "deficiency_signs": "Pellagra: the '4 Ds' — Dermatitis (photosensitive skin rash), Diarrhoea, Dementia, and Death if untreated.",
             "source_name": NIH, "source_url": NIH_B3},
            {"body_system": "DNA Repair", "explanation": "NAD+ is consumed by poly(ADP-ribose) polymerases (PARPs), enzymes that detect and repair DNA strand breaks. Niacin status is therefore linked to genomic stability and cancer prevention research.",
             "source_name": NIH, "source_url": NIH_B3},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "male", "value": 16, "unit": "mg NE", "intake_type": "RDA",
             "upper_limit": 35, "source_name": NIH, "source_url": NIH_B3},
            {"age_group": "19+ years", "sex": "female", "value": 14, "unit": "mg NE", "intake_type": "RDA",
             "upper_limit": 35, "source_name": NIH, "source_url": NIH_B3},
            {"age_group": "9–13 years", "sex": "all", "value": 12, "unit": "mg NE", "intake_type": "RDA",
             "upper_limit": 20, "source_name": NIH, "source_url": NIH_B3},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 18, "unit": "mg NE", "intake_type": "RDA",
             "upper_limit": 35, "source_name": NIH, "source_url": NIH_B3},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 17, "unit": "mg NE", "intake_type": "RDA",
             "upper_limit": 35, "source_name": NIH, "source_url": NIH_B3},
        ],
    )

    # ── Vitamin B5 (Pantothenic Acid) ────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin B5", category="Vitamins", solubility="water-soluble",
        synonyms=["pantothenic acid", "pantothenate", "vitamin B5", "calcium pantothenate",
                  "panthenol", "dexpanthenol"],
        food_sources=[
            {"food_name": "Beef Liver (braised)", "serving_size": "3 oz (85g)",
             "amount": 6.0, "unit": "mg",
             "bioavailability_note": "Liver provides the most concentrated dietary source of pantothenic acid.",
             "source_name": NIH, "source_url": NIH_B5},
            {"food_name": "Sunflower Seeds (dry roasted)", "serving_size": "1/4 cup (35g)",
             "amount": 2.3, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Chicken Breast (roasted)", "serving_size": "3 oz (85g)",
             "amount": 1.3, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Avocado (raw)", "serving_size": "1/2 medium (68g)",
             "amount": 1.0, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Shiitake Mushrooms (cooked)", "serving_size": "1/2 cup (73g)",
             "amount": 1.2, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Milk (whole)", "serving_size": "1 cup (244ml)",
             "amount": 0.88, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Lentils (boiled)", "serving_size": "1/2 cup (99g)",
             "amount": 0.64, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Salmon (Atlantic, farmed, cooked)", "serving_size": "3 oz (85g)",
             "amount": 1.9, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Biotin (Vitamin B7)", "helper_type": "nutrient",
             "description": "Biotin and pantothenic acid cooperate in fatty acid metabolism. Biotin is required for the carboxylase enzymes that work alongside pantothenic acid's coenzyme A in fat synthesis and oxidation pathways.",
             "source_name": NIH, "source_url": NIH_B5},
        ],
        blockers=[
            {"blocker_name": "Heat and Canning", "blocker_type": "food",
             "description": "Pantothenic acid is heat-labile. Cooking can reduce content by 15–50%, and commercial canning can destroy up to 75% of the pantothenic acid in food. Minimally processed foods retain more.",
             "source_name": NIH, "source_url": NIH_B5},
            {"blocker_name": "Refined Grain Processing", "blocker_type": "food",
             "description": "Milling of whole grains removes the germ and bran — where most pantothenic acid is concentrated. Unlike some B vitamins, pantothenic acid is not routinely added back in enrichment.",
             "source_name": HARVARD, "source_url": HARVARD_URL},
        ],
        body_roles=[
            {"body_system": "Coenzyme A Synthesis", "explanation": "Pantothenic acid is the metabolic precursor to coenzyme A (CoA), one of the most critical molecules in metabolism. CoA participates in over 100 enzymatic reactions, including fatty acid oxidation (beta-oxidation), fatty acid synthesis, the Krebs cycle, steroid hormone synthesis, and acetylcholine production.",
             "deficiency_signs": "Deficiency is extremely rare due to wide food distribution. Experimental deficiency causes fatigue, headache, insomnia, and a characteristic burning-feet sensation (pantothenate kinase-associated neurodegeneration when genetic).",
             "source_name": NIH, "source_url": NIH_B5},
            {"body_system": "Adrenal Function", "explanation": "Coenzyme A derived from pantothenic acid is essential for the synthesis of steroid hormones (cortisol, aldosterone, sex hormones) in the adrenal cortex. The adrenal glands have the highest concentration of pantothenic acid of any tissue.",
             "source_name": NIH, "source_url": NIH_B5},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "all", "value": 5.0, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B5},
            {"age_group": "9–13 years", "sex": "all", "value": 4.0, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B5},
            {"age_group": "14–18 years", "sex": "all", "value": 5.0, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B5},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 6.0, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B5},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 7.0, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B5},
        ],
    )

    # ── Vitamin B6 (Pyridoxine) ──────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin B6", category="Vitamins", solubility="water-soluble",
        synonyms=["pyridoxine", "pyridoxal", "pyridoxamine", "vitamin B6",
                  "pyridoxal-5-phosphate", "PLP", "pyridoxal phosphate"],
        food_sources=[
            {"food_name": "Chickpeas (canned)", "serving_size": "1/2 cup (120g)",
             "amount": 1.1, "unit": "mg",
             "bioavailability_note": "One of the richest plant-based B6 sources.",
             "source_name": NIH, "source_url": NIH_B6},
            {"food_name": "Beef Liver (pan-fried)", "serving_size": "3 oz (85g)",
             "amount": 0.9, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Tuna (yellowfin, cooked)", "serving_size": "3 oz (85g)",
             "amount": 0.9, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Salmon (sockeye, cooked)", "serving_size": "3 oz (85g)",
             "amount": 0.8, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Chicken Breast (roasted)", "serving_size": "3 oz (85g)",
             "amount": 0.8, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Potato with Skin (baked)", "serving_size": "1 medium (173g)",
             "amount": 0.6, "unit": "mg",
             "preparation_note": "Eat the skin — it contains a significant proportion of the B6.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Banana (raw)", "serving_size": "1 medium (118g)",
             "amount": 0.4, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Fortified Breakfast Cereal", "serving_size": "3/4 cup (30g)",
             "amount": 2.0, "unit": "mg",
             "bioavailability_note": "Synthetic pyridoxine is efficiently absorbed.", "source_name": NIH, "source_url": NIH_B6},
        ],
        helpers=[
            {"helper_name": "Riboflavin (Vitamin B2)", "helper_type": "nutrient",
             "description": "FMN (the active form of riboflavin) is an essential cofactor for pyridox(am)ine-5-phosphate oxidase — the enzyme that converts the dietary forms of B6 into its active coenzyme form, pyridoxal-5-phosphate (PLP). Riboflavin deficiency directly impairs B6 activation.",
             "source_name": NIH, "source_url": NIH_B6},
        ],
        blockers=[
            {"blocker_name": "Alcohol", "blocker_type": "food",
             "description": "Acetaldehyde (produced during alcohol metabolism) accelerates the degradation of PLP, the active form of vitamin B6. Chronic alcohol use is associated with B6 deficiency even at adequate dietary intakes.",
             "source_name": NIH, "source_url": NIH_B6},
            {"blocker_name": "Isoniazid and Cycloserine (TB Drugs)", "blocker_type": "nutrient",
             "description": "These antibiotics form inactive complexes with pyridoxal phosphate, depleting active B6. Supplemental B6 is routinely co-prescribed with these medications.",
             "source_name": NIH, "source_url": NIH_B6},
            {"blocker_name": "Certain Anticonvulsants", "blocker_type": "nutrient",
             "description": "Valproic acid and phenytoin can increase B6 catabolism or interfere with its metabolism, raising requirements in people on long-term anticonvulsant therapy.",
             "source_name": NIH, "source_url": NIH_B6},
        ],
        body_roles=[
            {"body_system": "Protein Metabolism", "explanation": "PLP is a coenzyme for over 100 enzymes, the majority of which are involved in amino acid metabolism — transamination, deamination, and decarboxylation reactions. It is essential for gluconeogenesis (making glucose from amino acids) and for breaking down glycogen.",
             "deficiency_signs": "Peripheral neuropathy, seborrhoeic dermatitis, glossitis, impaired immune function, confusion. High-dose supplement toxicity causes sensory neuropathy.",
             "source_name": NIH, "source_url": NIH_B6},
            {"body_system": "Neurotransmitter Synthesis", "explanation": "PLP is required for the synthesis of serotonin (from tryptophan), dopamine and norepinephrine (from tyrosine), GABA (from glutamate), and histamine (from histidine). B6 is therefore critical for mood regulation, sleep, and nervous system function.",
             "source_name": NIH, "source_url": NIH_B6},
        ],
        rda_values=[
            {"age_group": "19–50 years", "sex": "all", "value": 1.3, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 100, "source_name": NIH, "source_url": NIH_B6},
            {"age_group": "51+ years", "sex": "male", "value": 1.7, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 100, "source_name": NIH, "source_url": NIH_B6},
            {"age_group": "51+ years", "sex": "female", "value": 1.5, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 100, "source_name": NIH, "source_url": NIH_B6},
            {"age_group": "9–13 years", "sex": "all", "value": 1.0, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 60, "source_name": NIH, "source_url": NIH_B6},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 1.9, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 100, "source_name": NIH, "source_url": NIH_B6},
        ],
    )

    # ── Vitamin B7 (Biotin) ──────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin B7", category="Vitamins", solubility="water-soluble",
        synonyms=["biotin", "vitamin B7", "vitamin H", "coenzyme R", "d-biotin"],
        food_sources=[
            {"food_name": "Beef Liver (cooked)", "serving_size": "3 oz (85g)",
             "amount": 30.8, "unit": "mcg",
             "bioavailability_note": "Liver is the richest common dietary source of biotin.",
             "source_name": NIH, "source_url": NIH_B7},
            {"food_name": "Egg (whole, cooked)", "serving_size": "1 large (50g)",
             "amount": 10.0, "unit": "mcg",
             "bioavailability_note": "Cook eggs before eating — raw egg whites contain avidin which blocks biotin absorption.",
             "preparation_note": "Always cook eggs. Raw egg white contains avidin, a protein that tightly binds biotin and prevents its absorption.",
             "source_name": NIH, "source_url": NIH_B7},
            {"food_name": "Salmon (pink, canned)", "serving_size": "3 oz (85g)",
             "amount": 5.0, "unit": "mcg", "source_name": NIH, "source_url": NIH_B7},
            {"food_name": "Pork Chop (cooked)", "serving_size": "3 oz (85g)",
             "amount": 3.8, "unit": "mcg", "source_name": NIH, "source_url": NIH_B7},
            {"food_name": "Sunflower Seeds (roasted)", "serving_size": "1/4 cup (35g)",
             "amount": 2.6, "unit": "mcg", "source_name": NIH, "source_url": NIH_B7},
            {"food_name": "Sweet Potato (cooked)", "serving_size": "1/2 cup (100g)",
             "amount": 2.4, "unit": "mcg", "source_name": NIH, "source_url": NIH_B7},
            {"food_name": "Almonds (roasted)", "serving_size": "1/4 cup (36g)",
             "amount": 1.5, "unit": "mcg", "source_name": NIH, "source_url": NIH_B7},
            {"food_name": "Tuna (canned in water)", "serving_size": "3 oz (85g)",
             "amount": 0.6, "unit": "mcg", "source_name": NIH, "source_url": NIH_B7},
        ],
        helpers=[
            {"helper_name": "Gut Microbiome", "helper_type": "nutrient",
             "description": "Intestinal bacteria (e.g., Bifidobacterium, Lactobacillus) synthesize biotin in the gut. The contribution to systemic biotin levels is uncertain, but maintaining a healthy gut microbiome may support biotin sufficiency.",
             "source_name": NIH, "source_url": NIH_B7},
        ],
        blockers=[
            {"blocker_name": "Raw Egg Whites (Avidin)", "blocker_type": "food",
             "description": "Avidin, a glycoprotein in raw egg whites, binds biotin with extraordinarily high affinity (Kd ~10⁻¹⁵ M) in the gut, completely blocking its absorption. Cooking denatures avidin, eliminating this interaction. Regular consumption of raw egg whites is the most common cause of biotin deficiency.",
             "source_name": NIH, "source_url": NIH_B7},
            {"blocker_name": "Alcohol", "blocker_type": "food",
             "description": "Alcohol impairs biotin absorption and increases its urinary excretion. Chronic alcohol use is associated with reduced biotin status.",
             "source_name": NIH, "source_url": NIH_B7},
        ],
        body_roles=[
            {"body_system": "Carboxylase Enzymes", "explanation": "Biotin is an essential cofactor for five carboxylase enzymes: pyruvate carboxylase (gluconeogenesis), acetyl-CoA carboxylase (fatty acid synthesis), propionyl-CoA carboxylase (amino acid catabolism), methylcrotonyl-CoA carboxylase (leucine catabolism), and 3-methylglutaconyl-CoA hydratase. These reactions span carbohydrate, fat, and protein metabolism.",
             "deficiency_signs": "Hair thinning and loss, brittle nails, scaly red rash around eyes/nose/mouth, neurological symptoms (depression, lethargy, hallucinations). Deficiency is rare except with prolonged raw egg white consumption or biotinidase deficiency (genetic).",
             "source_name": NIH, "source_url": NIH_B7},
            {"body_system": "Gene Expression", "explanation": "Biotin plays a role in gene regulation by biotinylating histone proteins, affecting DNA packaging and accessibility. This epigenetic function is an active area of research into cell differentiation and gene silencing.",
             "source_name": NIH, "source_url": NIH_B7},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "all", "value": 30, "unit": "mcg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B7},
            {"age_group": "9–13 years", "sex": "all", "value": 20, "unit": "mcg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B7},
            {"age_group": "14–18 years", "sex": "all", "value": 25, "unit": "mcg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B7},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 30, "unit": "mcg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B7},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 35, "unit": "mcg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_B7},
        ],
    )

    # ── Vitamin K ────────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Vitamin K", category="Vitamins", solubility="fat-soluble",
        synonyms=["phylloquinone", "vitamin K1", "menaquinone", "vitamin K2", "MK-4", "MK-7",
                  "menadione", "vitamin K3"],
        food_sources=[
            {"food_name": "Natto (fermented soybeans)", "serving_size": "3 oz (85g)",
             "amount": 850, "unit": "mcg",
             "bioavailability_note": "Exceptionally high in vitamin K2 (MK-7), the most bioavailable and longest-acting form.",
             "source_name": NIH, "source_url": NIH_VIT_K},
            {"food_name": "Kale (raw)", "serving_size": "1 cup chopped (67g)",
             "amount": 547, "unit": "mcg",
             "bioavailability_note": "Vitamin K1 (phylloquinone); absorption greatly improved by consuming with dietary fat.",
             "source_name": NIH, "source_url": NIH_VIT_K},
            {"food_name": "Collard Greens (cooked)", "serving_size": "1/2 cup (95g)",
             "amount": 530, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Spinach (cooked)", "serving_size": "1/2 cup (90g)",
             "amount": 444, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Broccoli (cooked)", "serving_size": "1/2 cup (78g)",
             "amount": 92, "unit": "mcg",
             "bioavailability_note": "Moderate source; consume with fat-containing food to maximise K1 absorption.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Edamame (cooked)", "serving_size": "1/2 cup (78g)",
             "amount": 21, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Soybean Oil", "serving_size": "1 tbsp (13.6g)",
             "amount": 25, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Hard Cheese (e.g. Gouda)", "serving_size": "1.5 oz (42g)",
             "amount": 18, "unit": "mcg",
             "bioavailability_note": "Contains vitamin K2 (menaquinones), which has superior bioavailability and longer half-life than K1.",
             "source_name": NIH, "source_url": NIH_VIT_K},
        ],
        helpers=[
            {"helper_name": "Dietary Fat", "helper_type": "food",
             "description": "Vitamin K is fat-soluble. Consuming vitamin K–rich vegetables with a source of fat (e.g., olive oil, avocado, nuts) dramatically increases K1 absorption compared to fat-free consumption.",
             "source_name": NIH, "source_url": NIH_VIT_K},
            {"helper_name": "Vitamin D", "helper_type": "nutrient",
             "description": "Vitamin D and K2 act synergistically in bone metabolism. Vitamin D increases calcium absorption; vitamin K2 (via carboxylation of osteocalcin) directs calcium into bone rather than soft tissue. Together they reduce calcification of arteries.",
             "source_name": NIH, "source_url": NIH_VIT_K},
        ],
        blockers=[
            {"blocker_name": "Warfarin (Coumadin)", "blocker_type": "nutrient",
             "description": "Warfarin works by blocking vitamin K epoxide reductase, impairing vitamin K recycling. Patients on warfarin must maintain consistent vitamin K intake — sudden large increases can reduce drug effectiveness; sudden decreases can cause dangerous over-anticoagulation.",
             "source_name": NIH, "source_url": NIH_VIT_K},
            {"blocker_name": "Mineral Oils and Cholesterol-Lowering Drugs", "blocker_type": "nutrient",
             "description": "Orlistat and mineral oil sequester fat-soluble vitamins including K in the gut. Cholestyramine (bile acid resin) also impairs K absorption by reducing fat absorption broadly.",
             "source_name": NIH, "source_url": NIH_VIT_K},
        ],
        body_roles=[
            {"body_system": "Blood Clotting", "explanation": "Vitamin K is an essential cofactor for carboxylation of clotting factors II (prothrombin), VII, IX, and X in the liver. Without K-mediated gamma-carboxylation, these factors cannot bind calcium and initiate coagulation. Vitamin K deficiency causes uncontrolled bleeding.",
             "deficiency_signs": "Prolonged bleeding, easy bruising, haemorrhage (including intracranial haemorrhage in newborns — reason for routine K injection at birth).",
             "source_name": NIH, "source_url": NIH_VIT_K},
            {"body_system": "Bone Metabolism", "explanation": "Vitamin K2 carboxylates osteocalcin, enabling it to bind calcium within bone mineral. Without carboxylated osteocalcin, bone mineralisation is impaired. Low vitamin K status is associated with decreased bone density and increased fracture risk.",
             "source_name": NIH, "source_url": NIH_VIT_K},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "male", "value": 120, "unit": "mcg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_VIT_K},
            {"age_group": "19+ years", "sex": "female", "value": 90, "unit": "mcg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_VIT_K},
            {"age_group": "9–13 years", "sex": "all", "value": 60, "unit": "mcg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_VIT_K},
            {"age_group": "14–18 years", "sex": "all", "value": 75, "unit": "mcg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_VIT_K},
            {"age_group": "Pregnancy / Lactation (19+)", "sex": "pregnant", "value": 90, "unit": "mcg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_VIT_K},
        ],
    )

    # ── Potassium ────────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Potassium", category="Minerals", solubility=None,
        synonyms=["K", "potassium chloride", "potassium citrate", "potassium bicarbonate",
                  "potassium gluconate"],
        food_sources=[
            {"food_name": "Potato with Skin (baked)", "serving_size": "1 medium (173g)",
             "amount": 926, "unit": "mg",
             "bioavailability_note": "Potatoes are among the most potassium-dense common foods; eat the skin.",
             "source_name": NIH, "source_url": NIH_POT},
            {"food_name": "Beet Greens (cooked)", "serving_size": "1/2 cup (72g)",
             "amount": 655, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sweet Potato (baked)", "serving_size": "1 medium (130g)",
             "amount": 542, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "White Beans (canned)", "serving_size": "1/2 cup (131g)",
             "amount": 502, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Avocado (raw)", "serving_size": "1/2 medium (68g)",
             "amount": 364, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Banana (raw)", "serving_size": "1 medium (118g)",
             "amount": 422, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Salmon (sockeye, cooked)", "serving_size": "3 oz (85g)",
             "amount": 414, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Spinach (cooked)", "serving_size": "1/2 cup (90g)",
             "amount": 419, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Dried Apricots", "serving_size": "1/4 cup (33g)",
             "amount": 378, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Lentils (cooked)", "serving_size": "1/2 cup (99g)",
             "amount": 365, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Magnesium", "helper_type": "nutrient",
             "description": "Magnesium is required for the Na+/K+-ATPase pump to function correctly, helping cells maintain their potassium concentration. Magnesium deficiency can cause refractory hypokalemia — potassium replacement fails until magnesium is repleted.",
             "source_name": NIH, "source_url": NIH_POT},
        ],
        blockers=[
            {"blocker_name": "Excess Sodium Intake", "blocker_type": "food",
             "description": "High sodium intake increases urinary potassium excretion. The kidneys regulate sodium and potassium homeostasis in tandem: diets high in sodium can deplete potassium stores over time.",
             "source_name": NIH, "source_url": NIH_POT},
            {"blocker_name": "Loop and Thiazide Diuretics", "blocker_type": "nutrient",
             "description": "Many diuretics prescribed for hypertension and heart failure promote urinary potassium wasting. Patients on these drugs often require dietary counselling or potassium supplementation to prevent hypokalaemia.",
             "source_name": NIH, "source_url": NIH_POT},
        ],
        body_roles=[
            {"body_system": "Cardiovascular / Blood Pressure", "explanation": "Potassium is the main intracellular cation. Higher potassium intake blunts the blood pressure-raising effects of sodium by promoting urinary sodium excretion (natriuresis) and relaxing blood vessel walls. Each 1 g/day increase in potassium is associated with a ~1 mmHg reduction in systolic blood pressure.",
             "deficiency_signs": "Hypokalemia: muscle weakness and cramps, constipation, fatigue, cardiac arrhythmias. Severe deficiency (K+ <2.5 mmol/L) can be life-threatening.",
             "source_name": NIH, "source_url": NIH_POT},
            {"body_system": "Nerve and Muscle Function", "explanation": "The electrochemical gradient between intracellular potassium and extracellular sodium drives the resting membrane potential of every excitable cell. Potassium flux through voltage-gated channels is required to repolarise the membrane after each nerve impulse or muscle contraction, including the heartbeat.",
             "source_name": NIH, "source_url": NIH_POT},
        ],
        rda_values=[
            {"age_group": "19–50 years", "sex": "male", "value": 3400, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_POT},
            {"age_group": "19–50 years", "sex": "female", "value": 2600, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_POT},
            {"age_group": "51+ years", "sex": "male", "value": 3400, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_POT},
            {"age_group": "51+ years", "sex": "female", "value": 2600, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_POT},
            {"age_group": "9–13 years", "sex": "all", "value": 2300, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_POT},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 2900, "unit": "mg", "intake_type": "AI",
             "upper_limit": None, "source_name": NIH, "source_url": NIH_POT},
        ],
    )

    # ── Phosphorus ───────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Phosphorus", category="Minerals", solubility=None,
        synonyms=["P", "phosphate", "inorganic phosphate", "pyrophosphate",
                  "phosphoric acid", "tricalcium phosphate"],
        food_sources=[
            {"food_name": "Salmon (sockeye, cooked)", "serving_size": "3 oz (85g)",
             "amount": 274, "unit": "mg",
             "bioavailability_note": "Animal-source phosphorus is highly bioavailable (~70–80%).",
             "source_name": NIH, "source_url": NIH_PHOS},
            {"food_name": "Ricotta Cheese (part-skim)", "serving_size": "1/2 cup (124g)",
             "amount": 257, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Milk (whole)", "serving_size": "1 cup (244ml)",
             "amount": 246, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Chicken Breast (roasted)", "serving_size": "3 oz (85g)",
             "amount": 182, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Beef (bottom round, braised)", "serving_size": "3 oz (85g)",
             "amount": 179, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Lentils (cooked)", "serving_size": "1/2 cup (99g)",
             "amount": 178, "unit": "mg",
             "bioavailability_note": "Plant-source phosphorus (as phytate) has lower bioavailability (~50%). Soaking, sprouting, or fermenting lentils reduces phytate and increases phosphorus availability.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Pumpkin Seeds (roasted)", "serving_size": "1 oz (28g)",
             "amount": 332, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Greek Yogurt (plain, non-fat)", "serving_size": "6 oz (170g)",
             "amount": 230, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Vitamin D", "helper_type": "nutrient",
             "description": "Active vitamin D (calcitriol) increases the expression of sodium-phosphate co-transporters in the small intestine, enhancing phosphorus absorption — the same mechanism by which it enhances calcium absorption.",
             "source_name": NIH, "source_url": NIH_PHOS},
            {"helper_name": "Adequate Protein Intake", "helper_type": "food",
             "description": "Protein consumption enhances intestinal phosphorus absorption through unclear mechanisms, likely related to amino acid–mediated stimulation of gut transporters.",
             "source_name": NIH, "source_url": NIH_PHOS},
        ],
        blockers=[
            {"blocker_name": "Aluminium and Magnesium Antacids", "blocker_type": "nutrient",
             "description": "Aluminium hydroxide and magnesium hydroxide antacids bind dietary phosphate in the gut to form insoluble salts, dramatically reducing absorption. Long-term antacid use can cause hypophosphataemia.",
             "source_name": NIH, "source_url": NIH_PHOS},
            {"blocker_name": "Phytic Acid (Phytates)", "blocker_type": "food",
             "description": "In plant foods, phosphorus is largely stored as phytate, which humans cannot efficiently hydrolyse. Fermentation, soaking, sprouting, and cooking all reduce phytate, improving phosphorus bioavailability from plant sources.",
             "source_name": HARVARD, "source_url": HARVARD_URL},
        ],
        body_roles=[
            {"body_system": "Skeletal System", "explanation": "About 85% of the body's phosphorus is stored in bones and teeth as hydroxyapatite [Ca₁₀(PO₄)₆(OH)₂], alongside calcium. Phosphorus provides the structural rigidity of the mineral phase of bone.",
             "deficiency_signs": "Hypophosphataemia: bone pain, muscle weakness, rickets/osteomalacia, haemolytic anaemia, impaired immune function. Severe cases: confusion, cardiac arrest.",
             "source_name": NIH, "source_url": NIH_PHOS},
            {"body_system": "Energy Currency (ATP)", "explanation": "Phosphate groups are the backbone of adenosine triphosphate (ATP), the universal energy currency of all cells. Every energy-releasing or energy-consuming reaction in the body involves phosphate transfer. Phosphorus is also essential for DNA, RNA, and phospholipid cell membranes.",
             "source_name": NIH, "source_url": NIH_PHOS},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "all", "value": 700, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 4000, "source_name": NIH, "source_url": NIH_PHOS},
            {"age_group": "9–18 years", "sex": "all", "value": 1250, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 4000, "source_name": NIH, "source_url": NIH_PHOS},
            {"age_group": "70+ years", "sex": "all", "value": 700, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 3000, "source_name": NIH, "source_url": NIH_PHOS},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 700, "unit": "mg", "intake_type": "RDA",
             "upper_limit": 3500, "source_name": NIH, "source_url": NIH_PHOS},
        ],
    )

    # ── Selenium ─────────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Selenium", category="Minerals", solubility=None,
        synonyms=["Se", "selenomethionine", "selenocysteine", "sodium selenite",
                  "selenium yeast", "selenate"],
        food_sources=[
            {"food_name": "Brazil Nuts (dried)", "serving_size": "1 oz (28g, ~6 nuts)",
             "amount": 544, "unit": "mcg",
             "bioavailability_note": "Brazil nuts are extraordinarily rich in selenium — a single nut can provide the full daily requirement. Amounts vary widely by soil selenium content. Limit to 1–2 nuts/day to avoid toxicity.",
             "source_name": NIH, "source_url": NIH_SEL},
            {"food_name": "Tuna (yellowfin, cooked)", "serving_size": "3 oz (85g)",
             "amount": 92, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Halibut (cooked)", "serving_size": "3 oz (85g)",
             "amount": 47, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sardines (canned in oil)", "serving_size": "3 oz (85g)",
             "amount": 45, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Ham (roasted)", "serving_size": "3 oz (85g)",
             "amount": 42, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Shrimp (cooked)", "serving_size": "3 oz (85g)",
             "amount": 34, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Beef Steak (bottom round, cooked)", "serving_size": "3 oz (85g)",
             "amount": 33, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Enriched White Pasta (cooked)", "serving_size": "1 cup (140g)",
             "amount": 37, "unit": "mcg",
             "bioavailability_note": "Selenium content in grains reflects soil selenium levels; varies geographically.",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Vitamin E", "helper_type": "nutrient",
             "description": "Selenium and vitamin E act synergistically as antioxidants. Both protect cell membranes from lipid peroxidation; selenium does this via selenoproteins (glutathione peroxidases), while vitamin E acts directly as a lipid-soluble radical scavenger.",
             "source_name": NIH, "source_url": NIH_SEL},
        ],
        blockers=[
            {"blocker_name": "Selenium-Depleted Soils", "blocker_type": "food",
             "description": "The selenium content of plant foods entirely depends on soil selenium concentration. Large regions of Europe, New Zealand, and parts of China have selenium-poor soils. People in these areas are at risk of low selenium intake from plant-based foods.",
             "source_name": NIH, "source_url": NIH_SEL},
            {"blocker_name": "Very High Vitamin C Doses (Pharmacological)", "blocker_type": "nutrient",
             "description": "Very high supplemental doses of vitamin C (several grams/day) may reduce selenium absorption by converting selenite to elemental selenium, which is not absorbed. Dietary vitamin C levels pose no risk.",
             "source_name": NIH, "source_url": NIH_SEL},
        ],
        body_roles=[
            {"body_system": "Antioxidant Defense", "explanation": "Selenium is an essential component of 25+ selenoproteins in humans, including glutathione peroxidases (GPx1–4), thioredoxin reductases, and selenoprotein P. These enzymes reduce hydrogen peroxide and lipid hydroperoxides, protecting cells from oxidative damage.",
             "deficiency_signs": "Keshan disease (endemic cardiomyopathy in selenium-poor regions of China); Kashin–Beck disease (osteoarthropathy). Milder deficiency impairs immune function and thyroid metabolism.",
             "source_name": NIH, "source_url": NIH_SEL},
            {"body_system": "Thyroid Hormone Metabolism", "explanation": "The enzyme iodothyronine deiodinase, which converts inactive T4 (thyroxine) to active T3 (triiodothyronine), is a selenoprotein. Selenium deficiency impairs thyroid hormone activation and can exacerbate iodine deficiency.",
             "source_name": NIH, "source_url": NIH_SEL},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "all", "value": 55, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 400, "source_name": NIH, "source_url": NIH_SEL},
            {"age_group": "9–13 years", "sex": "all", "value": 40, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 280, "source_name": NIH, "source_url": NIH_SEL},
            {"age_group": "14–18 years", "sex": "all", "value": 55, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 400, "source_name": NIH, "source_url": NIH_SEL},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 60, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 400, "source_name": NIH, "source_url": NIH_SEL},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 70, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 400, "source_name": NIH, "source_url": NIH_SEL},
        ],
    )

    # ── Iodine ───────────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Iodine", category="Minerals", solubility=None,
        synonyms=["I", "iodide", "potassium iodide", "sodium iodide", "kelp", "iodized salt"],
        food_sources=[
            {"food_name": "Seaweed (nori, dried)", "serving_size": "1 sheet (2.5g)",
             "amount": 42, "unit": "mcg",
             "bioavailability_note": "Iodine content in seaweed varies enormously (16–2984 mcg/g dry weight). Kombu/kelp can deliver toxic amounts — nori is the safest seaweed for regular consumption.",
             "source_name": NIH, "source_url": NIH_IOD},
            {"food_name": "Cod (baked)", "serving_size": "3 oz (85g)",
             "amount": 99, "unit": "mcg",
             "bioavailability_note": "Seafood iodine reflects oceanic iodine levels and is generally well absorbed.",
             "source_name": NIH, "source_url": NIH_IOD},
            {"food_name": "Iodized Salt", "serving_size": "1/4 tsp (1.5g)",
             "amount": 71, "unit": "mcg",
             "bioavailability_note": "Iodized salt is the most reliable and consistent iodine source worldwide. Sea salt and kosher salt are typically NOT iodized.",
             "source_name": NIH, "source_url": NIH_IOD},
            {"food_name": "Milk (whole)", "serving_size": "1 cup (244ml)",
             "amount": 56, "unit": "mcg",
             "bioavailability_note": "Dairy iodine reflects iodine in animal feed and iodophor sanitisers used in dairy equipment. Levels vary by country.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Shrimp (cooked)", "serving_size": "3 oz (85g)",
             "amount": 35, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Egg (whole, poached)", "serving_size": "1 large (50g)",
             "amount": 24, "unit": "mcg",
             "bioavailability_note": "Most of the iodine is in the yolk; content varies with the hen's iodine intake.",
             "source_name": NIH, "source_url": NIH_IOD},
            {"food_name": "Plain Yogurt (low-fat)", "serving_size": "8 oz (245g)",
             "amount": 75, "unit": "mcg", "source_name": NIH, "source_url": NIH_IOD},
            {"food_name": "Tuna (canned in water)", "serving_size": "3 oz (85g)",
             "amount": 17, "unit": "mcg", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Selenium", "helper_type": "nutrient",
             "description": "Selenium is required for iodothyronine deiodinase, the enzyme that activates thyroid hormones from iodine-containing precursors. Selenium deficiency can exacerbate the effects of iodine deficiency on thyroid function.",
             "source_name": NIH, "source_url": NIH_IOD},
        ],
        blockers=[
            {"blocker_name": "Goitrogens (Brassica Vegetables, Raw)", "blocker_type": "food",
             "description": "Raw cruciferous vegetables (cabbage, broccoli, Brussels sprouts, kale) contain glucosinolates that are converted to goitrin in the gut, which blocks thyroid iodine uptake and hormone synthesis. Cooking inactivates the relevant enzyme (myrosinase). Moderate cooked consumption is not a concern for iodine-sufficient individuals.",
             "source_name": NIH, "source_url": NIH_IOD},
            {"blocker_name": "Excess Iodine (Paradoxical Inhibition)", "blocker_type": "nutrient",
             "description": "Very high iodine intake can paradoxically inhibit thyroid hormone synthesis (Wolff-Chaikoff effect) and trigger autoimmune thyroid disease in susceptible individuals. This is why the UL is set at 1,100 mcg/day.",
             "source_name": NIH, "source_url": NIH_IOD},
        ],
        body_roles=[
            {"body_system": "Thyroid Hormone Synthesis", "explanation": "Iodine is the key constituent of the thyroid hormones thyroxine (T4, contains 4 iodine atoms) and triiodothyronine (T3, contains 3 iodine atoms). The thyroid gland avidly concentrates iodine from blood and incorporates it into thyroglobulin to synthesise T3 and T4.",
             "deficiency_signs": "Goitre (enlarged thyroid gland), hypothyroidism, intellectual disability (in children/foetuses — the leading preventable cause of intellectual disability worldwide), cretinism, weight gain, fatigue, cold intolerance.",
             "source_name": NIH, "source_url": NIH_IOD},
            {"body_system": "Metabolic Regulation", "explanation": "T3 and T4 regulate basal metabolic rate, heart rate, body temperature, protein synthesis, and development of the fetal brain and nervous system. Virtually every cell in the body has thyroid hormone receptors.",
             "source_name": NIH, "source_url": NIH_IOD},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "all", "value": 150, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 1100, "source_name": NIH, "source_url": NIH_IOD},
            {"age_group": "9–13 years", "sex": "all", "value": 120, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 600, "source_name": NIH, "source_url": NIH_IOD},
            {"age_group": "14–18 years", "sex": "all", "value": 150, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 900, "source_name": NIH, "source_url": NIH_IOD},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 220, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 1100, "source_name": NIH, "source_url": NIH_IOD},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 290, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 1100, "source_name": NIH, "source_url": NIH_IOD},
        ],
    )

    # ── Copper ───────────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Copper", category="Minerals", solubility=None,
        synonyms=["Cu", "copper sulfate", "copper gluconate", "copper bisglycinate",
                  "copper histidinate"],
        food_sources=[
            {"food_name": "Beef Liver (pan-fried)", "serving_size": "3 oz (85g)",
             "amount": 12.4, "unit": "mg",
             "bioavailability_note": "Liver provides more copper per serving than any other common food.",
             "source_name": NIH, "source_url": NIH_COP},
            {"food_name": "Oysters (eastern, cooked)", "serving_size": "3 oz (85g)",
             "amount": 4.85, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Dark Chocolate (70–85% cacao)", "serving_size": "1 oz (28g)",
             "amount": 0.93, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Cashews (dry roasted)", "serving_size": "1 oz (28g)",
             "amount": 0.62, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Sunflower Seeds (dry roasted)", "serving_size": "1/4 cup (35g)",
             "amount": 0.52, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Almonds (dry roasted)", "serving_size": "1 oz (28g)",
             "amount": 0.30, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Lentils (cooked)", "serving_size": "1/2 cup (99g)",
             "amount": 0.25, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Shiitake Mushrooms (cooked)", "serving_size": "1/2 cup (73g)",
             "amount": 0.32, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Adequate Protein Intake", "helper_type": "food",
             "description": "Dietary amino acids (especially histidine and methionine) form complexes with copper in the gut that are readily transported across the intestinal epithelium. Protein-rich meals generally improve copper bioavailability.",
             "source_name": NIH, "source_url": NIH_COP},
        ],
        blockers=[
            {"blocker_name": "High-Dose Zinc Supplements", "blocker_type": "nutrient",
             "description": "Zinc and copper share the same intestinal transporter (metallothionein). High-dose zinc supplementation (≥50 mg/day) induces metallothionein, which preferentially binds copper and prevents its absorption. Long-term high-dose zinc is the most common cause of copper deficiency.",
             "source_name": NIH, "source_url": NIH_COP},
            {"blocker_name": "Pharmacological Vitamin C Doses", "blocker_type": "nutrient",
             "description": "Supplemental vitamin C at doses of 1,500 mg/day or more may reduce copper absorption by promoting copper reduction from the absorbable Cu²⁺ to the less absorbable Cu⁺ form.",
             "source_name": NIH, "source_url": NIH_COP},
        ],
        body_roles=[
            {"body_system": "Energy Production", "explanation": "Copper is a structural component of cytochrome c oxidase (Complex IV), the terminal enzyme of the mitochondrial electron transport chain. Without copper, ATP synthesis is severely impaired.",
             "deficiency_signs": "Anaemia (hypochromic), neutropenia, bone abnormalities, neurological degeneration (myelopathy), impaired immune function. Menkes disease: severe X-linked copper deficiency disorder.",
             "source_name": NIH, "source_url": NIH_COP},
            {"body_system": "Iron Metabolism", "explanation": "Copper-containing ferroxidases (ceruloplasmin, hephaestin) oxidise ferrous iron (Fe²⁺) to ferric iron (Fe³⁺), which is required for loading iron onto transferrin for blood transport. Copper deficiency causes functional iron deficiency (anaemia) even when iron intake is adequate.",
             "source_name": NIH, "source_url": NIH_COP},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "all", "value": 900, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 10000, "source_name": NIH, "source_url": NIH_COP},
            {"age_group": "9–13 years", "sex": "all", "value": 700, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 5000, "source_name": NIH, "source_url": NIH_COP},
            {"age_group": "14–18 years", "sex": "all", "value": 890, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 8000, "source_name": NIH, "source_url": NIH_COP},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 1000, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 10000, "source_name": NIH, "source_url": NIH_COP},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 1300, "unit": "mcg", "intake_type": "RDA",
             "upper_limit": 10000, "source_name": NIH, "source_url": NIH_COP},
        ],
    )

    # ── Sodium ───────────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Sodium", category="Minerals", solubility=None,
        synonyms=["Na", "table salt", "sodium chloride", "NaCl", "sea salt",
                  "sodium bicarbonate", "baking soda", "MSG", "monosodium glutamate"],
        food_sources=[
            {"food_name": "Soy Sauce", "serving_size": "1 tbsp (18ml)",
             "amount": 879, "unit": "mg",
             "bioavailability_note": "One of the highest-sodium condiments; use sparingly or choose reduced-sodium versions.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Table Salt (iodized)", "serving_size": "1/4 tsp (1.5g)",
             "amount": 575, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Dill Pickle (medium)", "serving_size": "1 medium (65g)",
             "amount": 785, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Canned Soup (chicken noodle)", "serving_size": "1 cup (240ml)",
             "amount": 866, "unit": "mg",
             "bioavailability_note": "Canned and processed soups are among the largest contributors to dietary sodium.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Deli Turkey Breast (sliced)", "serving_size": "3 oz (85g)",
             "amount": 787, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "White Bread", "serving_size": "1 slice (28g)",
             "amount": 147, "unit": "mg",
             "bioavailability_note": "Bread is a major sodium contributor because it is eaten frequently, not because it is extremely salty.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Cheddar Cheese", "serving_size": "1.5 oz (42g)",
             "amount": 264, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Tomato Sauce (canned)", "serving_size": "1/2 cup (122g)",
             "amount": 642, "unit": "mg", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Potassium (moderates sodium effects)", "helper_type": "nutrient",
             "description": "While potassium does not increase sodium absorption, it counteracts sodium's blood pressure-raising effects by promoting urinary sodium excretion (natriuresis) and relaxing blood vessel walls. The sodium-to-potassium ratio in the diet is more predictive of blood pressure than sodium alone.",
             "source_name": HARVARD, "source_url": HARV_SODIUM},
        ],
        blockers=[
            {"blocker_name": "Not applicable", "blocker_type": "food",
             "description": "Sodium absorption is extremely efficient (~98% of ingested sodium is absorbed). There are no common dietary factors that meaningfully reduce sodium absorption in healthy individuals. The primary concern with sodium is overconsumption, not poor absorption.",
             "source_name": HARVARD, "source_url": HARV_SODIUM},
        ],
        body_roles=[
            {"body_system": "Fluid and Electrolyte Balance", "explanation": "Sodium is the primary extracellular cation (140 mmol/L outside cells vs. 10–15 mmol/L inside). It determines extracellular fluid volume, plasma osmolality, and blood pressure. The kidneys regulate sodium excretion minute-to-minute through aldosterone, ADH, and the renin–angiotensin system.",
             "deficiency_signs": "Hyponatraemia (low blood sodium): nausea, headache, confusion, seizures, coma. Occurs with extreme sweating, overhydration, diuretic use, or SIADH. Chronic high intake causes hypertension, stroke, and kidney disease.",
             "source_name": HARVARD, "source_url": HARV_SODIUM},
            {"body_system": "Nerve and Muscle Function", "explanation": "The sodium-potassium ATPase pump maintains the electrochemical gradient across cell membranes required for nerve impulse generation and muscle contraction. Voltage-gated sodium channels generate the depolarisation phase of every action potential.",
             "source_name": NIH, "source_url": NIH_CALCIUM},
        ],
        rda_values=[
            # AI = adequate intake; no formal RDA. CDRR (Chronic Disease Risk Reduction) = <2300 mg
            {"age_group": "19–50 years", "sex": "all", "value": 1500, "unit": "mg", "intake_type": "AI",
             "upper_limit": 2300, "source_name": HARVARD, "source_url": HARV_SODIUM},
            {"age_group": "51–70 years", "sex": "all", "value": 1300, "unit": "mg", "intake_type": "AI",
             "upper_limit": 2300, "source_name": HARVARD, "source_url": HARV_SODIUM},
            {"age_group": "71+ years", "sex": "all", "value": 1200, "unit": "mg", "intake_type": "AI",
             "upper_limit": 2300, "source_name": HARVARD, "source_url": HARV_SODIUM},
            {"age_group": "9–13 years", "sex": "all", "value": 1200, "unit": "mg", "intake_type": "AI",
             "upper_limit": 2300, "source_name": HARVARD, "source_url": HARV_SODIUM},
        ],
    )

    # ── Dietary Fiber ────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Dietary Fiber", category="Macronutrients", solubility=None,
        synonyms=["fibre", "dietary fibre", "roughage", "soluble fiber", "insoluble fiber",
                  "prebiotic fiber", "cellulose", "pectin", "beta-glucan", "inulin",
                  "psyllium", "resistant starch", "FOS", "fructooligosaccharides"],
        food_sources=[
            {"food_name": "Chia Seeds", "serving_size": "1 oz (28g)",
             "amount": 10.6, "unit": "g",
             "bioavailability_note": "Contains a mix of soluble (mucilage gel) and insoluble fiber. Hydrate well.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Lentils (cooked)", "serving_size": "1/2 cup (99g)",
             "amount": 7.8, "unit": "g",
             "bioavailability_note": "Rich in both soluble and insoluble fiber; also a resistant starch source.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Black Beans (cooked)", "serving_size": "1/2 cup (86g)",
             "amount": 7.5, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Pear (with skin)", "serving_size": "1 medium (178g)",
             "amount": 5.5, "unit": "g",
             "bioavailability_note": "Skin contains most of the insoluble fiber; don't peel.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Avocado (raw)", "serving_size": "1/2 medium (68g)",
             "amount": 5.0, "unit": "g",
             "bioavailability_note": "Unusually rich in fiber for a fat-containing food; also provides potassium and B6.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Oats (dry rolled)", "serving_size": "1/2 cup (40g)",
             "amount": 4.0, "unit": "g",
             "bioavailability_note": "Beta-glucan — a soluble fiber in oats — is clinically proven to lower LDL cholesterol at doses of 3+ g/day (≈1.5 cups cooked oatmeal).",
             "source_name": HARVARD, "source_url": HARV_FIBER},
            {"food_name": "Apple (with skin)", "serving_size": "1 medium (182g)",
             "amount": 4.4, "unit": "g",
             "bioavailability_note": "Rich in pectin (soluble fiber), which feeds beneficial gut bacteria.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Broccoli (cooked)", "serving_size": "1 cup (156g)",
             "amount": 5.1, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Almonds (dry roasted)", "serving_size": "1 oz (28g)",
             "amount": 3.5, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Brown Rice (cooked)", "serving_size": "1 cup (195g)",
             "amount": 3.5, "unit": "g",
             "bioavailability_note": "Brown rice retains its bran layer; white rice loses most fiber during milling.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Chickpeas (canned)", "serving_size": "1/2 cup (120g)",
             "amount": 6.3, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Adequate Water Intake", "helper_type": "food",
             "description": "Dietary fiber requires water to function effectively. Soluble fiber absorbs water to form a gel that slows digestion and lowers cholesterol. Insoluble fiber adds bulk to stool. Without sufficient hydration, high fiber intake can cause constipation and bloating.",
             "source_name": HARVARD, "source_url": HARV_FIBER},
            {"helper_name": "Gradual Intake Increase", "helper_type": "food",
             "description": "Increasing fiber intake gradually (rather than suddenly) allows the gut microbiome to adapt, reducing gas, bloating, and discomfort. Add 5 g/week until the target intake is reached.",
             "source_name": HARVARD, "source_url": HARV_FIBER},
        ],
        blockers=[
            {"blocker_name": "Refined Grain Processing", "blocker_type": "food",
             "description": "Milling removes the bran and germ from whole grains, eliminating most of the fiber. White flour, white bread, and white rice contain only a fraction of the fiber in their whole-grain counterparts. Enrichment restores some vitamins but does not replace fiber.",
             "source_name": HARVARD, "source_url": HARV_FIBER},
            {"blocker_name": "Excessive Cooking / Processing", "blocker_type": "food",
             "description": "Extended cooking can break down fiber structures and partially reduce its viscosity and prebiotic activity. Minimally processed, lightly cooked, or raw plant foods generally retain more functional fiber.",
             "source_name": HARVARD, "source_url": HARV_FIBER},
        ],
        body_roles=[
            {"body_system": "Digestive and Gut Health", "explanation": "Insoluble fiber (cellulose, hemicellulose) adds bulk to stool, accelerates intestinal transit, and reduces constipation and colorectal cancer risk. Soluble fiber (pectin, beta-glucan, inulin) is fermented by gut bacteria into short-chain fatty acids (butyrate, propionate, acetate), which nourish colonocytes, reduce inflammation, and support a diverse gut microbiome.",
             "deficiency_signs": "Constipation, diverticular disease, higher risk of colorectal cancer and type 2 diabetes. Most adults consume only ~15 g/day — well below the AI of 25–38 g.",
             "source_name": HARVARD, "source_url": HARV_FIBER},
            {"body_system": "Cardiovascular", "explanation": "Soluble fiber (particularly oat beta-glucan and pectin) binds bile acids in the gut and carries them out of the body in stool. This forces the liver to synthesise new bile acids from cholesterol, lowering circulating LDL. The FDA authorises a health claim linking oat beta-glucan (≥3 g/day) to reduced coronary heart disease risk.",
             "source_name": HARVARD, "source_url": HARV_FIBER},
        ],
        rda_values=[
            {"age_group": "19–50 years", "sex": "male", "value": 38, "unit": "g", "intake_type": "AI",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_FIBER},
            {"age_group": "19–50 years", "sex": "female", "value": 25, "unit": "g", "intake_type": "AI",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_FIBER},
            {"age_group": "51+ years", "sex": "male", "value": 30, "unit": "g", "intake_type": "AI",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_FIBER},
            {"age_group": "51+ years", "sex": "female", "value": 21, "unit": "g", "intake_type": "AI",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_FIBER},
            {"age_group": "9–13 years", "sex": "all", "value": 26, "unit": "g", "intake_type": "AI",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_FIBER},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 28, "unit": "g", "intake_type": "AI",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_FIBER},
        ],
    )

    # ── Added Sugar ──────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Added Sugar", category="Macronutrients", solubility=None,
        synonyms=["sucrose", "added sugars", "table sugar", "fructose", "glucose",
                  "high-fructose corn syrup", "HFCS", "brown sugar", "agave nectar",
                  "honey", "maple syrup", "corn syrup", "dextrose", "maltose"],
        food_sources=[
            {"food_name": "Regular Cola (12 fl oz can)", "serving_size": "12 fl oz (354ml)",
             "amount": 39, "unit": "g",
             "bioavailability_note": "Liquid sugar is absorbed extremely rapidly, causing sharp blood glucose and insulin spikes without fibre to slow absorption.",
             "source_name": HARVARD, "source_url": HARV_SUGAR},
            {"food_name": "Candy Bar (chocolate, ~1.5 oz)", "serving_size": "1.5 oz (42g)",
             "amount": 27, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Flavoured Fruit Yogurt (6 oz)", "serving_size": "6 oz (170g)",
             "amount": 18, "unit": "g",
             "bioavailability_note": "Many 'healthy' yogurts contain as much added sugar as a dessert. Choose plain yogurt and add fresh fruit.",
             "source_name": HARVARD, "source_url": HARV_SUGAR},
            {"food_name": "Commercial Tomato Sauce (jar)", "serving_size": "1/2 cup (122g)",
             "amount": 12, "unit": "g",
             "bioavailability_note": "Sugar is added to most jarred pasta sauces as a preservative and flavour enhancer — a hidden source.",
             "source_name": HARVARD, "source_url": HARV_SUGAR},
            {"food_name": "Sweetened Breakfast Cereal", "serving_size": "1 cup (30g typical)",
             "amount": 15, "unit": "g",
             "bioavailability_note": "Many popular cereals contain more than 50% of calories from added sugar.", "source_name": HARVARD, "source_url": HARV_SUGAR},
            {"food_name": "Energy Drink (8 fl oz)", "serving_size": "8 fl oz (240ml)",
             "amount": 27, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Bottled Salad Dressing (2 tbsp)", "serving_size": "2 tbsp (30ml)",
             "amount": 6, "unit": "g",
             "bioavailability_note": "Fat-free dressings often replace fat with added sugar to improve palatability.",
             "source_name": HARVARD, "source_url": HARV_SUGAR},
            {"food_name": "White Bread (commercial, 2 slices)", "serving_size": "2 slices (56g)",
             "amount": 5, "unit": "g", "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Note: Limit Added Sugar", "helper_type": "nutrient",
             "description": "Unlike most nutrients, added sugar has no established minimum requirement. The body can synthesise all the glucose it needs from other carbohydrates, fats, and proteins. Current dietary guidelines focus on limiting added sugar intake rather than achieving a target.",
             "source_name": HARVARD, "source_url": HARV_SUGAR},
        ],
        blockers=[
            {"blocker_name": "Dietary Fiber (slows absorption)", "blocker_type": "food",
             "description": "Dietary fiber (especially soluble fiber) slows the digestion and absorption of sugars, blunting post-meal blood glucose and insulin spikes. Eating sugar within a meal rich in fiber, protein, and fat significantly reduces its glycaemic impact compared to drinking sugary drinks on an empty stomach.",
             "source_name": HARVARD, "source_url": HARV_SUGAR},
            {"blocker_name": "Protein and Fat (lower glycaemic response)", "blocker_type": "food",
             "description": "Consuming protein and fat alongside sugary foods reduces the rate of gastric emptying, slowing glucose absorption and producing a lower and more sustained blood glucose response.",
             "source_name": HARVARD, "source_url": HARV_SUGAR},
        ],
        body_roles=[
            {"body_system": "Metabolic Health (risk context)", "explanation": "The body rapidly converts added sugars (sucrose, HFCS) to glucose and fructose. Glucose is used directly for energy; fructose is metabolised almost exclusively in the liver. Excess fructose promotes de novo lipogenesis (fat production), leading to non-alcoholic fatty liver disease, insulin resistance, and elevated triglycerides. Chronic high added sugar intake is independently associated with type 2 diabetes, cardiovascular disease, and obesity.",
             "deficiency_signs": "No deficiency syndrome. The liver, brain, and red blood cells can obtain all needed glucose from starches, lactose, proteins, and fats.",
             "source_name": HARVARD, "source_url": HARV_SUGAR},
            {"body_system": "Dental Health", "explanation": "Added sugars are fermented by oral bacteria (Streptococcus mutans) to produce lactic acid, which dissolves tooth enamel. Sucrose and glucose are the primary substrates for dental caries. Frequency of sugar exposure matters more than total amount — sipping sugary drinks throughout the day is more damaging than one discrete intake.",
             "source_name": MAYO, "source_url": MAYO_GEN},
        ],
        rda_values=[
            # No RDA; AHA and FDA guidelines recommend limiting
            {"age_group": "19+ years", "sex": "male", "value": 36, "unit": "g (limit)", "intake_type": "AI",
             "upper_limit": 50, "source_name": HARVARD, "source_url": HARV_SUGAR},
            {"age_group": "19+ years", "sex": "female", "value": 25, "unit": "g (limit)", "intake_type": "AI",
             "upper_limit": 50, "source_name": HARVARD, "source_url": HARV_SUGAR},
            {"age_group": "9–18 years", "sex": "all", "value": 25, "unit": "g (limit)", "intake_type": "AI",
             "upper_limit": 50, "source_name": HARVARD, "source_url": HARV_SUGAR},
            {"age_group": "2–8 years", "sex": "all", "value": 12, "unit": "g (limit)", "intake_type": "AI",
             "upper_limit": 25, "source_name": HARVARD, "source_url": HARV_SUGAR},
        ],
    )

    # ── Protein ──────────────────────────────────────────────────────────────
    seed_nutrient(
        db=db, name="Protein", category="Macronutrients", solubility=None,
        synonyms=["dietary protein", "amino acids", "complete protein", "incomplete protein",
                  "whey protein", "casein", "plant protein", "essential amino acids",
                  "EAA", "BCAA", "branched-chain amino acids"],
        food_sources=[
            {"food_name": "Chicken Breast (roasted, skinless)", "serving_size": "3 oz (85g)",
             "amount": 26, "unit": "g",
             "bioavailability_note": "Complete protein (all essential amino acids). Protein digestibility-corrected amino acid score (PDCAAS) = 1.0.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Tuna (canned in water)", "serving_size": "3 oz (85g)",
             "amount": 25, "unit": "g",
             "bioavailability_note": "Excellent complete protein; PDCAAS = 1.0.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Greek Yogurt (plain, non-fat)", "serving_size": "6 oz (170g)",
             "amount": 17, "unit": "g",
             "bioavailability_note": "Rich in casein and whey — slow and fast-digesting proteins. Also provides calcium and probiotics.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Beef (bottom round, braised)", "serving_size": "3 oz (85g)",
             "amount": 22, "unit": "g",
             "bioavailability_note": "Complete protein with high leucine content, which maximally stimulates muscle protein synthesis.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Cottage Cheese (1% fat)", "serving_size": "1/2 cup (113g)",
             "amount": 14, "unit": "g",
             "bioavailability_note": "Primarily casein protein — slow-digesting, ideal before sleep for overnight muscle protein synthesis.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Tofu (firm)", "serving_size": "1/2 cup (126g)",
             "amount": 10, "unit": "g",
             "bioavailability_note": "Soy protein is the only plant protein with a PDCAAS of 1.0 — a complete plant protein.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Lentils (cooked)", "serving_size": "1/2 cup (99g)",
             "amount": 9, "unit": "g",
             "bioavailability_note": "Incomplete plant protein (low in methionine). Pair with grains to achieve full amino acid complementarity.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Quinoa (cooked)", "serving_size": "1 cup (185g)",
             "amount": 8, "unit": "g",
             "bioavailability_note": "Rare plant-based complete protein; contains all 9 essential amino acids in reasonable amounts.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Egg (whole, scrambled)", "serving_size": "1 large (61g)",
             "amount": 6, "unit": "g",
             "bioavailability_note": "Egg protein has a PDCAAS of 1.0 and is the reference standard for protein quality. Cooked eggs have ~91% digestibility vs. ~51% for raw.",
             "preparation_note": "Cook eggs to denature ovomucin, which increases protein digestibility significantly.",
             "source_name": HARVARD, "source_url": HARV_PROT},
            {"food_name": "Black Beans (cooked)", "serving_size": "1/2 cup (86g)",
             "amount": 7.6, "unit": "g",
             "bioavailability_note": "Incomplete protein; low in methionine. Combine with rice for a complete amino acid profile.",
             "source_name": USDA, "source_url": USDA_URL},
            {"food_name": "Edamame (shelled, cooked)", "serving_size": "1/2 cup (78g)",
             "amount": 9, "unit": "g",
             "bioavailability_note": "Nearly complete soy protein with low saturated fat.",
             "source_name": USDA, "source_url": USDA_URL},
        ],
        helpers=[
            {"helper_name": "Vitamin B6, B12, and Folate", "helper_type": "nutrient",
             "description": "These B vitamins are essential cofactors in amino acid metabolism — transamination, deamination, methylation, and the urea cycle. Adequate B-vitamin status is required to efficiently process dietary protein.",
             "source_name": HARVARD, "source_url": HARV_PROT},
            {"helper_name": "Digestive Enzymes and Stomach Acid", "helper_type": "nutrient",
             "description": "Stomach acid (HCl) denatures dietary proteins and activates pepsin. Pancreatic proteases (trypsin, chymotrypsin, elastase) and brush-border peptidases in the small intestine complete digestion to individual amino acids and di/tripeptides for absorption.",
             "source_name": HARVARD, "source_url": HARV_PROT},
            {"helper_name": "Leucine-Rich Foods", "helper_type": "food",
             "description": "Leucine (a branched-chain amino acid abundant in animal proteins) acts as a metabolic signal that activates mTORC1, the primary stimulator of muscle protein synthesis. Aiming for ~2.5–3 g leucine per meal maximises the anabolic stimulus.",
             "source_name": HARVARD, "source_url": HARV_PROT},
        ],
        blockers=[
            {"blocker_name": "Excessive Alcohol", "blocker_type": "food",
             "description": "Chronic alcohol consumption impairs protein digestion and absorption, increases muscle protein breakdown, and inhibits the liver's ability to synthesise albumin and other blood proteins.",
             "source_name": HARVARD, "source_url": HARV_PROT},
            {"blocker_name": "Protease Inhibitors in Raw Legumes", "blocker_type": "food",
             "description": "Raw legumes and soybeans contain trypsin inhibitors that block protein-digesting enzymes. Cooking thoroughly deactivates these inhibitors and dramatically improves plant protein digestibility.",
             "preparation_note": "Always cook legumes thoroughly before eating to deactivate protease inhibitors.",
             "source_name": HARVARD, "source_url": HARV_PROT},
        ],
        body_roles=[
            {"body_system": "Structural / Tissue Building", "explanation": "Protein is the primary structural component of every cell in the body. Collagen (most abundant protein) forms skin, tendons, ligaments, and bone matrix. Actin and myosin form muscle fibre. Keratin forms hair and nails. The body uses 20 amino acids as building blocks; 9 are essential (must come from diet): histidine, isoleucine, leucine, lysine, methionine, phenylalanine, threonine, tryptophan, valine.",
             "deficiency_signs": "Kwashiorkor (severe protein deficiency with adequate calories): oedema, fatty liver, muscle wasting, impaired immunity, growth failure. Marasmus: total calorie and protein deficiency, severe wasting.",
             "source_name": HARVARD, "source_url": HARV_PROT},
            {"body_system": "Enzymatic and Hormonal Function", "explanation": "All enzymes are proteins — they catalyse every chemical reaction in the body. Major hormones are also proteins: insulin, glucagon, growth hormone, thyroid-stimulating hormone, and erythropoietin. Antibodies (immunoglobulins) that fight infection are proteins. Haemoglobin that carries oxygen is a protein.",
             "source_name": HARVARD, "source_url": HARV_PROT},
        ],
        rda_values=[
            {"age_group": "19+ years", "sex": "male", "value": 56, "unit": "g", "intake_type": "RDA",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_PROT},
            {"age_group": "19+ years", "sex": "female", "value": 46, "unit": "g", "intake_type": "RDA",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_PROT},
            {"age_group": "9–13 years", "sex": "all", "value": 34, "unit": "g", "intake_type": "RDA",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_PROT},
            {"age_group": "Pregnancy (19+ years)", "sex": "pregnant", "value": 71, "unit": "g", "intake_type": "RDA",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_PROT},
            {"age_group": "Lactation (19+ years)", "sex": "lactating", "value": 71, "unit": "g", "intake_type": "RDA",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_PROT},
            # Per-kg alternative for athletes
            {"age_group": "Athletes / Active Adults", "sex": "all", "value": 1.6, "unit": "g/kg/day", "intake_type": "AI",
             "upper_limit": None, "source_name": HARVARD, "source_url": HARV_PROT},
        ],
    )


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
