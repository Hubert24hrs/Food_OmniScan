export type Color = "green" | "amber" | "red" | "grey";

export interface Adjustment {
  code: string;
  points: number;
  reason: string;
  evidence_type: "product_measurement" | "regulatory" | "published_research" | "estimate" | "unverified";
  source_keys: string[];
  pct_dv?: number;
  ingredient?: string;
}

export interface Component {
  assessed: boolean;
  score: number | null;
  weight: number;
  adjustments: Adjustment[];
  notes: string[];
  basis?: string;
  nova_group?: number;
  nova_source?: string;
  match_rate?: number;
}

export interface HighlightItem { slug: string; name: string; e_number?: string | null; concern_level: string }

export interface Score {
  methodology_version: string;
  overall: number | null;
  grade: string;
  color: Color;
  label: string;
  confidence: "high" | "medium" | "low";
  coverage: number;
  insufficient_data: boolean;
  missing_components: string[];
  components: Record<"nutrition" | "ingredients" | "processing" | "dietary_suitability" | "product_concerns", Component>;
  caps_applied: { code: string; max: number; reason: string }[];
  highlights: Record<string, HighlightItem[]> & { organic: boolean; organic_note: string; trans_fat_g_per_100: number | null };
  front_of_pack: null | { basis: string } & Record<"saturated_fat" | "sodium" | "added_sugars", { pct_dv: number | null; level: "low" | "medium" | "high" | null }>;
  disclaimer: string;
}

export interface IngredientRow {
  text: string;
  normalized: string;
  depth: number;
  percent: number | null;
  e_numbers: string[];
  is_group: boolean;
  match_method: string;
  match_confidence: number;
  ingredient: null | { slug: string; name: string; category: string; function: string | null; concern_level: string; e_number: string | null; flags: string[]; summary: string | null; verification_status: string };
}

export interface AllergenRow { code: string; name: string; status: "contains" | "may_contain" | "not_detected" | "unknown"; evidence: { source: string; text: string; note?: string }[]; regulated_in_region: boolean }

export interface Reason { severity: "red" | "yellow" | "green"; rule: string; message: string; ingredient: string | null }
export interface Compatibility {
  profile_id: string | null;
  profile_name: string;
  verdict: "red" | "yellow" | "green";
  critical_allergen_alerts: { allergen: string; name: string; status: string; severity: string; message: string }[];
  reasons: Reason[];
  disclaimer: string;
}

export interface Analysis {
  score: Score;
  ingredients: IngredientRow[];
  ingredients_parse: null | { confidence: number; precautionary_statement: string | null; contains_statement: string | null };
  allergens: AllergenRow[];
  compatibility: Compatibility[];
  recalls?: { id: string; title: string; authority: string; reason: string; url: string | null; recall_date: string | null; jurisdiction: string }[];
  lab_reports?: { id: string; analyte: string; value: number; unit: string; threshold: number | null; threshold_jurisdiction: string | null; exceeds_threshold: boolean | null; lab_name: string; tested_on: string | null }[];
  contaminant_testing?: { has_product_specific_data: boolean; message: string };
}

export type Nutrients = Partial<Record<"energy_kcal" | "energy_kj" | "fat" | "saturated_fat" | "trans_fat" | "cholesterol_mg" | "carbohydrates" | "sugars" | "added_sugars" | "fiber" | "protein" | "salt" | "sodium", number | null>>;

export interface Product {
  id: string;
  name: string | null;
  brand: string | null;
  quantity: string | null;
  serving_size: string | null;
  barcodes: { barcode: string; format: string }[];
  categories: string[];
  category: string | null;
  labels: string[];
  packaging: string | null;
  image_url: string | null;
  images: { kind: string; url: string }[];
  ingredients_text: string | null;
  nova_group: number | null;
  nova_source: string | null;
  is_beverage: boolean;
  nutrition: null | { basis: string; per_100: Nutrients; serving_size_g: number | null; per_serving: Nutrients | null; source: string };
  provenance: { source: string; source_url: string | null; license: string | null; attribution: string | null; fields: Record<string, string>; last_synced_at: string | null; verified_at: string | null };
  completeness: number;
}

export interface ProductSummary {
  id: string;
  name: string | null;
  brand: string | null;
  image_url: string | null;
  barcode: string | null;
  score: number | null;
  grade: string;
  color: Color;
  nova_group: number | null;
  category: string | null;
  source: string;
}

export interface Me {
  id: string;
  email: string;
  display_name: string | null;
  role: "user" | "contributor" | "moderator" | "admin";
  country: string | null;
  locale: string;
  currency: string;
  region: "US" | "EU" | "INTL";
  consent_health_data: boolean;
  consent_ai_history: boolean;
  active_profile_id: string | null;
  units: string;
  tier: "free" | "plus" | "premium" | "family";
}

export interface Profile {
  id: string;
  name: string;
  relationship: string | null;
  is_primary: boolean;
  is_active: boolean;
  avatar_color: string | null;
  goals: Record<string, number>;
  allergens: { code: string; severity: string; avoid_traces: boolean }[];
  diets: string[];
  avoid: string[];
}
