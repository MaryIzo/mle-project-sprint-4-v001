import logging

from fastapi import FastAPI
from contextlib import asynccontextmanager

from recommendations import Recommendations

import requests

# uvicorn recommendation_service:app --reload --port 8081 --host 0.0.0.0

features_store_url = "http://127.0.0.1:8010"
events_store_url = "http://127.0.0.1:8020"
recommendations_url = 'http://127.0.0.1:8000/recommendations'

# Создаем файл для логгирования всех действий и сохраняем в test_service.log
logger = logging.getLogger("uvicorn.error")
file_handler = logging.FileHandler('test_service.log')
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

rec_store = Recommendations()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # код ниже (до yield) выполнится только один раз при запуске сервиса
    logger.info("Starting load")

    rec_store.load(
        "personal",
        "data/final_recommendations_feat.parquet",
        columns=["user_id", "item_id", "rank"],
    )
    logger.info("Loaded personal recommendations")
    rec_store.load(
        "default",
        "data/top_popular.parquet",
        columns=["item_id", "rank"],
    )
    logger.info("Loaded top recommendations")

    yield
    # этот код выполнится только один раз при остановке сервиса
    logger.info("Stopping load")
    
# создаём приложение FastAPI
app = FastAPI(title="recommendations", lifespan=lifespan)

@app.post("/recommendations_offline")
async def recommendations_offline(user_id: int, k: int = 100):
    """
    Возвращает список рекомендаций длиной k для пользователя user_id
    """
    logger.info(f"Getting offline recommendations for user: {user_id}")

    recs = rec_store.get(user_id=user_id, k=k)

    return {"recs": recs}

def dedup_ids(ids):
    """
    Дедублицирует список идентификаторов, оставляя только первое вхождение
    """
    seen = set()
    ids = [id for id in ids if not (id in seen or seen.add(id))]

    return ids

@app.post("/recommendations_online")
async def recommendations_online(user_id: int, k: int = 100):
    """
    Возвращает список онлайн-рекомендаций длиной k для пользователя user_id
    """
    logger.info(f"Getiing online recommendations for user: {user_id}")

    headers = {"Content-type": "application/json", "Accept": "text/plain"}

    # получаем последнее событие пользователя
    params = {"user_id": user_id, "k": 3}
    resp = requests.post(events_store_url + "/get", headers=headers, params=params)
    events = resp.json()
    events = events["events"]

    items = []
    scores = []
    for item_id in events:
        params = {"item_id": item_id, "k": k}
        resp = requests.post(features_store_url +"/similar_items", headers=headers, params=params)
        item_similar_items = resp.json()

        items += item_similar_items["item_id_2"]
        scores += item_similar_items["score"]

    # сортируем похожие объекты по scores в убывающем порядке
    # для старта это приемлемый подход
    combined = list(zip(items, scores))
    combined = sorted(combined, key=lambda x: x[1], reverse=True)
    combined = [item for item, _ in combined]

    # удаляем дубликаты, чтобы не выдавать одинаковые рекомендации
    recs = dedup_ids(combined)[:k]

    return {"recs": recs}


@app.post("/recommendations")
async def recommendations(user_id: int, k: int = 100):
    """
    Возвращает список рекомендаций длиной k для пользователя user_id
    """

    logger.info(f"Getiing k blended recommendations for user: {user_id}")

    recs_offline = await recommendations_offline(user_id, k)
    recs_online = await recommendations_online(user_id, k)

    recs_offline = recs_offline["recs"]
    recs_online = recs_online["recs"]

    recs_blended = []

    min_length = min(len(recs_offline), len(recs_online))
    # чередуем элементы из списков, пока позволяет минимальная длина
    for i in range(min_length):
        if i % 2 == 0:
            recs_blended.append(recs_offline[i])
        else:
            recs_blended.append(recs_online[i])

    # добавляем оставшиеся элементы в конец
    recs_blended += recs_offline[min_length:]
    recs_blended += recs_online[min_length:]

    # удаляем дубликаты
    recs_blended = dedup_ids(recs_blended)
    # оставляем только первые k рекомендаций
    recs_blended = recs_blended[:k]

    return {"recs": recs_blended}