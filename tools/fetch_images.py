#!/usr/bin/env python3
"""
Fetches Wikipedia thumbnail images for nutrients and food sources.
Stores image_url in the database. Safe to re-run (skips already-populated rows).

Usage:
    python tools/fetch_images.py           # skip rows that already have an image
    python tools/fetch_images.py --force   # re-fetch everything
"""
import re
import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Nutrient, NutrientFoodSource

# Polite rate limit for Wikipedia (they ask for ~100ms between requests)
DELAY = 0.35
HEADERS = {
    "User-Agent": "NutrientCheck/1.0 (https://github.com/nutrients-check; eevezek@gmail.com) Python/httpx",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

# Map nutrient names to food-focused Wikipedia article titles so we get
# food photos rather than molecular diagrams.
NUTRIENT_WIKI = {
    "Vitamin A":           "Carrot",
    "Vitamin B1":          "Whole grain",
    "Vitamin B2":          "Dairy product",
    "Vitamin B3":          "Chicken as food",
    "Vitamin B5":          "Avocado",
    "Vitamin B6":          "Banana",
    "Vitamin B7":          "Egg as food",
    "Vitamin B9":          "Spinach",
    "Vitamin B12":         "Oily fish",
    "Vitamin C":           "Orange (fruit)",
    "Vitamin D":           "Salmon (food)",
    "Vitamin E":           "Almond",
    "Vitamin K":           "Broccoli",
    "Iron":                "Red meat",
    "Calcium":             "Milk",
    "Zinc":                "Oyster",
    "Magnesium":           "Magnesium in biology",
    "Potassium":           "Banana",
    "Phosphorus":          "Sardine",
    "Selenium":            "Brazil nut",
    "Iodine":              "Seaweed",
    "Copper":              "Shellfish",
    "Sodium":              "Salt",
    "Dietary Fiber":       "Whole grain",
    "Added Sugar":         "Sugar",
    "Protein":             "Meat",
    "Omega-3 Fatty Acids": "Flaxseed",
    "Omega-6 Fatty Acids": "Safflower",
    "Omega-9 Fatty Acids": "Olive oil",
}

# Map food keywords to Wikipedia article titles for better photo coverage
FOOD_WIKI_OVERRIDES = {
    "liver":       "Liver (food)",
    "beef":        "Beef",
    "lamb":        "Lamb (food)",
    "venison":     "Venison",
    "pork":        "Pork",
    "bacon":       "Bacon",
    "chicken":     "Chicken as food",
    "turkey":      "Turkey as food",
    "salmon":      "Salmon (food)",
    "tuna":        "Tuna",
    "sardine":     "Sardine",
    "mackerel":    "Mackerel",
    "trout":       "Trout",
    "herring":     "Herring",
    "cod":         "Cod",
    "egg":         "Egg as food",
    "milk":        "Milk",
    "yogurt":      "Yogurt",
    "cheese":      "Cheese",
    "butter":      "Butter",
    "carrot":      "Carrot",
    "sweet potato":"Sweet potato",
    "spinach":     "Spinach",
    "kale":        "Kale",
    "broccoli":    "Broccoli",
    "tomato":      "Tomato",
    "potato":      "Potato",
    "avocado":     "Avocado",
    "banana":      "Banana",
    "orange":      "Orange (fruit)",
    "lemon":       "Lemon",
    "apple":       "Apple",
    "blueberry":   "Blueberry",
    "strawberry":  "Strawberry",
    "mango":       "Mango",
    "pineapple":   "Pineapple",
    "mushroom":    "Mushroom",
    "almond":      "Almond",
    "walnut":      "Walnut",
    "cashew":      "Cashew",
    "peanut":      "Peanut",
    "sunflower":   "Sunflower seed",
    "flax":        "Flax",
    "oat":         "Oat",
    "wheat":       "Wheat",
    "rice":        "Rice",
    "bread":       "Bread",
    "lentil":      "Lentil",
    "chickpea":    "Chickpea",
    "soy":         "Soybean",
    "tofu":        "Tofu",
    "seaweed":     "Seaweed",
    "salt":        "Salt",
    "olive":       "Olive oil",
    "chocolate":   "Chocolate",
    "coconut":     "Coconut",
}


def get_wiki_thumbnail(article_title: str) -> str | None:
    """Return the thumbnail URL from a Wikipedia article using the Action API."""
    params = {
        "action": "query",
        "titles": article_title,
        "prop": "pageimages",
        "pithumbsize": 400,
        "format": "json",
        "redirects": 1,
    }
    try:
        r = httpx.get(
            "https://en.wikipedia.org/w/api.php",
            params=params,
            headers=HEADERS,
            timeout=12,
            follow_redirects=True,
        )
        if r.status_code != 200:
            print(f"    HTTP {r.status_code} for '{article_title}'")
            return None
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "thumbnail" in page:
                src = page["thumbnail"].get("source", "")
                if src:
                    src = re.sub(r"/\d+px-", "/400px-", src)
                return src or None
    except Exception as exc:
        print(f"    Error fetching '{article_title}': {exc}")
    return None


def clean_food_term(food_name: str) -> str:
    """Extract the core food term from a DB food_name string.

    'Atlantic salmon, cooked, 100g'  → 'Atlantic salmon'
    'Beef liver (raw)'               → 'Beef liver'
    'Spinach, boiled'                → 'Spinach'
    """
    term = re.sub(r",.*$", "", food_name)          # cut at first comma
    term = re.sub(r"\s*\(.*?\)", "", term)         # remove (parenthetical)
    term = re.sub(r"\b\d+\s*(g|mg|mcg|ml|oz)\b", "", term, flags=re.IGNORECASE)
    return term.strip()


def get_food_wiki_title(food_name: str) -> str:
    """Map a food_name to the best Wikipedia article title."""
    lower = food_name.lower()
    for keyword, title in FOOD_WIKI_OVERRIDES.items():
        if keyword in lower:
            return title
    return clean_food_term(food_name)


def fetch_nutrient_images(db: Session, force: bool = False) -> None:
    nutrients = db.query(Nutrient).order_by(Nutrient.id).all()
    print(f"\n== Nutrients ({len(nutrients)}) ==")
    updated = 0
    for n in nutrients:
        if n.image_url and not force:
            print(f"  skip  {n.name}")
            continue
        article = NUTRIENT_WIKI.get(n.name, n.name)
        url = get_wiki_thumbnail(article)
        if url:
            n.image_url = url
            db.add(n)
            updated += 1
            print(f"  ✓  {n.name:<30} → {article}")
        else:
            print(f"  ✗  {n.name:<30} (no image for '{article}')")
        time.sleep(DELAY)
    db.commit()
    print(f"  Updated {updated} nutrients.")


def fetch_food_images(db: Session, force: bool = False) -> None:
    foods = db.query(NutrientFoodSource).order_by(NutrientFoodSource.id).all()
    print(f"\n== Food sources ({len(foods)}) ==")

    # Cache: wiki_title → url  (avoids duplicate API calls for same food)
    cache: dict[str, str | None] = {}
    updated = 0

    for food in foods:
        if food.image_url and not force:
            continue
        title = get_food_wiki_title(food.food_name)
        if title not in cache:
            url = get_wiki_thumbnail(title)
            cache[title] = url
            status = "✓" if url else "✗"
            print(f"  {status}  {food.food_name[:50]:<50} → {title}")
            time.sleep(DELAY)
        else:
            url = cache[title]

        if url:
            food.image_url = url
            db.add(food)
            updated += 1

    db.commit()
    print(f"  Updated {updated} food sources.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Wikipedia images for nutrients and foods.")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if image_url is already set")
    args = parser.parse_args()

    db: Session = SessionLocal()
    try:
        fetch_nutrient_images(db, force=args.force)
        fetch_food_images(db, force=args.force)
        print("\nDone! Restart the server to see images.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
