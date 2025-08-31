from fastapi import FastAPI

from api.routers import products, categories
from api.deps import get_settings, get_aws_clients