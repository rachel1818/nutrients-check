import difflib

from sqlalchemy.orm import Session

from app.models import Nutrient, NutrientSynonym


def search_nutrient(db: Session, query: str) -> dict:
    q = query.strip().lower()

    # 1. Exact or partial match on nutrient name
    nutrient = db.query(Nutrient).filter(Nutrient.name.ilike(q)).first()

    # 2. Partial match if exact failed
    if not nutrient:
        nutrient = db.query(Nutrient).filter(Nutrient.name.ilike(f"%{q}%")).first()

    # 3. Try synonyms
    if not nutrient:
        synonym_row = (
            db.query(NutrientSynonym).filter(NutrientSynonym.synonym.ilike(q)).first()
        )
        if not synonym_row:
            synonym_row = (
                db.query(NutrientSynonym)
                .filter(NutrientSynonym.synonym.ilike(f"%{q}%"))
                .first()
            )
        if synonym_row:
            nutrient = synonym_row.nutrient

    # 4. Typo fallback with difflib
    suggestions: list[Nutrient] = []
    if not nutrient:
        all_names = [n.name for n in db.query(Nutrient).all()]
        all_synonyms = [s.synonym for s in db.query(NutrientSynonym).all()]
        candidates = all_names + all_synonyms
        candidates_lower = [c.lower() for c in candidates]
        close_matches = difflib.get_close_matches(q, candidates_lower, n=3, cutoff=0.6)
        seen_ids: set[int] = set()
        for match in close_matches:
            # Find original candidate (may be a synonym)
            n = db.query(Nutrient).filter(Nutrient.name.ilike(match)).first()
            if not n:
                syn = db.query(NutrientSynonym).filter(NutrientSynonym.synonym.ilike(match)).first()
                if syn:
                    n = syn.nutrient
            if n and n.id not in seen_ids:
                suggestions.append(n)
                seen_ids.add(n.id)

    return {"nutrient": nutrient, "suggestions": suggestions}
