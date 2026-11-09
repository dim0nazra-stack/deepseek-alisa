import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# Получение ключа из переменных окружения Render
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Согласно официальной документации DeepSeek, базовый URL обычно не требует /v1
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

@app.post("/")
async def main(request: Request):
    # 1. Парсинг запроса от Алисы
    req_data = await request.json()
    
    # Обработка проверочного запроса "ping" от Яндекса (крайне важно, иначе платформа будет считать сервис недоступным)
    if req_data.get("request", {}).get("original_utterance", "").lower() == "ping":
        return JSONResponse(content={
            "response": {"text": "pong", "end_session": False},
            "version": "1.0"
        })

    # Извлечение текста, введенного пользователем
    user_text = req_data.get("request", {}).get("command", "")
    
    # Если пользователь ничего не сказал, возвращаем приглашение (предотвращаем пустой запрос к API)
    if not user_text:
        return JSONResponse(content={
            "response": {"text": "Я слушаю, спросите меня о чем-нибудь.", "end_session": False},
            "version": "1.0"
        })

    # 2. Подготовка запроса к DeepSeek
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",  # Используйте deepseek-chat; если нужна модель рассуждений, можно заменить на deepseek-reasoner
        "messages": [
            {"role": "user", "content": user_text}
        ],
        "max_tokens": 500,  # Ограничение длины для ускорения ответа и избежания таймаута Алисы
        "temperature": 0.7
    }

    # 3. Вызов API DeepSeek
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
            data = response.json()

            # --- Ключевое исправление: защита от отсутствия поля choices ---
            if "choices" not in data or not data["choices"]:
                # Вывод полного ответа в лог для диагностики конкретной причины (недействительный ключ, неправильная модель и т.д.)
                print("DeepSeek API вернул некорректный ответ:", data)
                answer = "Извините, DeepSeek временно не может ответить. Попробуйте позже."
            else:
                answer = data["choices"][0]["message"]["content"]
                
    except httpx.TimeoutException:
        print("Таймаут запроса к DeepSeek")
        answer = "Сервис отвечает слишком долго, попробуйте еще раз."
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
        answer = "Произошла внутренняя ошибка, попробуйте позже."

    # 4. Возврат ответа в формате, требуемом Алисой
    return JSONResponse(content={
        "response": {
            "text": answer,
            "end_session": False
        },
        "version": "1.0"
    })

# Для локального тестирования (на Render не обязательно)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
