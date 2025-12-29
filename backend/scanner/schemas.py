from pydantic import BaseModel, Field

class IngredientSafety(BaseModel):
    name: str
    isHarmful: bool
    harmfulEffects: str = Field(description="Health risks or 'None'")
    riskScore: int = Field(ge=0, le=10, description="Risk rating 0-10")

class ProductSafetyReport(BaseModel):
    summary: str = Field(description="Brief health verdict of the product")
    analysis: list[IngredientSafety]