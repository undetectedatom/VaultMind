from app.schemas.external_model import ServiceModel


def select_generation_model(
    confidence: float,
    generation_models: list[ServiceModel],
    confidence_threshold: float = 0.5,
) -> tuple[ServiceModel, str]:
    """Route to a generation model based on retrieval confidence.

    High confidence (>= threshold) -> models[0] (cheap/fast)
    Low confidence (< threshold)   -> models[1] (capable)

    Returns (selected_model, route_reason).
    """
    if len(generation_models) < 2:
        return generation_models[0], "single_model_fallback"

    if confidence >= confidence_threshold:
        return generation_models[0], "high_confidence_fast_model"
    else:
        return generation_models[1], "low_confidence_capable_model"
