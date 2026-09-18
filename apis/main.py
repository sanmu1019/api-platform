from fastapi import FastAPI

from apis.demo.route import router as demo_router
from apis.divination.route import router as divination_router
from apis.domain.route import router as domain_router
from apis.douyin.route import router as douyin_router
from apis.dynamic.route import router as dynamic_router
from apis.dynamic.route import short_router as dynamic_short_router
from apis.exchange.route import router as exchange_router
from apis.freeapi.route import router as freeapi_router
from apis.holiday.route import router as holiday_router
from apis.hot.route import router as hot_router
from apis.ip.route import router as ip_router
from apis.joke.route import router as joke_router
from apis.lunar.route import router as lunar_router
from apis.phone.route import router as phone_router
from apis.price.route import router as price_router
from apis.spider.route import router as spider_router
from apis.time.route import router as time_router
from apis.tools.route import router as tools_router
from apis.versioned import v1_router
from apis.weather.route import router as weather_router
from apis.word.route import router as word_router
from core.config import settings


def register_api_routers(app: FastAPI) -> None:
    app.include_router(demo_router)
    app.include_router(ip_router)
    app.include_router(time_router)
    app.include_router(phone_router)
    app.include_router(word_router)
    app.include_router(freeapi_router)
    app.include_router(tools_router)
    app.include_router(spider_router)
    app.include_router(hot_router)
    app.include_router(exchange_router)
    app.include_router(weather_router)
    app.include_router(holiday_router)
    app.include_router(lunar_router)
    app.include_router(price_router)
    app.include_router(joke_router)
    app.include_router(divination_router)
    app.include_router(domain_router)
    if settings.enable_douyin:
        app.include_router(douyin_router)
    app.include_router(v1_router)
    app.include_router(dynamic_router)
    app.include_router(dynamic_short_router)
