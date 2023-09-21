from fastapi import APIRouter
from rest_endpoints.rest_callback import CallbackModel
from utils.log import create_logger

logger = create_logger("Callback Router")

callback_router = APIRouter()


@callback_router.post("{$callback_url}", response_model=CallbackModel)
def post(body: CallbackModel):
    pass
