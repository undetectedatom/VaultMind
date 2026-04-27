from models.doubao import VolcanoCodingPlanEmbeddings
from app.settings import get_sys_settings


# def get_embeddings(
#     provider: str = get_sys_settings().provider,
#     service_url: str = get_sys_settings().service_url,
#     api_key: str = get_sys_settings().api_key,
#     model: str = get_sys_settings().service_model,
# ):
#     if provider == "doubao":
#         return VolcanoCodingPlanEmbeddings(service_url, api_key, model)
