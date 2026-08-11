import asyncio
import aiohttp
import ssl

async def test():
    # Отключаем проверку SSL сертификатов
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Создаём коннектор с отключенным SSL
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get('https://api.telegram.org', timeout=10) as resp:
                print(f"✅ Telegram доступен! Статус: {resp.status}")
        except Exception as e:
            print(f" Telegram НЕ доступен: {e}")

asyncio.run(test())