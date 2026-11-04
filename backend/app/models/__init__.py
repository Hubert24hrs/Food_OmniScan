"""Import every model so Base.metadata is complete (Alembic, create_all)."""

from app.models.activity import (
    CommunitySubmission,
    FavouriteProduct,
    FoodDiary,
    FoodScan,
    MealEntry,
    MealPlan,
    ProductAlternative,
    ProductComparison,
    Recipe,
    ReviewReport,
    ScanHistory,
    ShoppingList,
    ShoppingListItem,
    UserBlock,
    UserReview,
)
from app.models.commerce import (
    AdminAuditLog,
    AIUsageRecord,
    Notification,
    PaymentEvent,
    Subscription,
    SubscriptionEntitlement,
)
from app.models.ingredient import FoodAdditive, Ingredient, IngredientSynonym
from app.models.lifestyle import (
    Article,
    BodyMetric,
    Budget,
    Household,
    HouseholdMember,
    PantryItem,
    PriceObservation,
    Purchase,
    SharedReport,
    WaterLog,
)
from app.models.product import (
    FoodBrand,
    FoodCategory,
    Manufacturer,
    NutritionFacts,
    Product,
    ProductBarcode,
    ProductImage,
    ProductIngredient,
)
from app.models.research import (
    LaboratoryReport,
    ProductEvidence,
    ProductRecall,
    ScientificSource,
)
from app.models.scoring import (
    ProductScore,
    ProductWarning,
    ScoringMethodology,
    ScoringRule,
)
from app.models.user import (
    AdminUser,
    AllergenProfile,
    DietaryPreference,
    FamilyProfile,
    IngredientAvoidanceRule,
    User,
    UserProfile,
)

__all__ = [name for name in dir() if not name.startswith("_")]
