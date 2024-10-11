
1. cd mle-project-sprint-4-v001/ml_service   

2. Запуск сервиса Feature store - это онлайн рекомендации  
uvicorn features_service:app --port 8010 

3. Запуск сервиса Event Store - это история пользователя    
uvicorn events_service:app --port 8020    
  
4. Запуск сервиса рекомендаций   
uvicorn recommendation_service:app   

5. Запуск тестирования сервиса последних событий 
python test_events_service.py
