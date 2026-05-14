from pydantic import BaseModel, ConfigDict


class SourceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    url: str


class NutrientSynonymSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    synonym: str


class NutrientRdaValueSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    age_group: str
    sex: str
    value: float
    unit: str
    intake_type: str
    upper_limit: float | None
    source: SourceSchema


class NutrientFoodSourceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    food_name: str
    serving_size: str
    amount: float
    unit: str
    bioavailability_note: str | None
    preparation_note: str | None
    source: SourceSchema


class NutrientAbsorptionHelperSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    helper_name: str
    helper_type: str
    description: str
    source: SourceSchema


class NutrientAbsorptionBlockerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    blocker_name: str
    blocker_type: str
    description: str
    source: SourceSchema


class NutrientBodyRoleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    body_system: str
    explanation: str
    deficiency_signs: str | None
    source: SourceSchema


class NutrientListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str
    slug: str


class NutrientDetailSchema(NutrientListItemSchema):
    solubility: str | None
    synonyms: list[NutrientSynonymSchema]
    rda_values: list[NutrientRdaValueSchema]
    food_sources: list[NutrientFoodSourceSchema]
    absorption_helpers: list[NutrientAbsorptionHelperSchema]
    absorption_blockers: list[NutrientAbsorptionBlockerSchema]
    body_roles: list[NutrientBodyRoleSchema]


class PaginatedNutrientsSchema(BaseModel):
    items: list[NutrientListItemSchema]
    total: int
    offset: int
    limit: int


class PaginatedFoodsSchema(BaseModel):
    items: list[NutrientFoodSourceSchema]
    total: int
    offset: int
    limit: int


class SuggestItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str
