import os
import logging
import sys
import time

from http import HTTPStatus

import requests
import telegram

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler


load_dotenv()

PRACTICUM_TOKEN = os.getenv('practicum_token')
TELEGRAM_TOKEN = os.getenv('telegram_token')
TELEGRAM_CHAT_ID = os.getenv('telegram_chat_id')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
)
handler = RotatingFileHandler(
    'logs.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение отправлено: {message}')
    except telegram.TelegramError as error:
        logger.error(f'Ошибка телеграма: {error}')


def get_api_answer(current_timestamp):
    """Получения ответа от API эндпоинта."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error('Эндпоинт практикума не доступен')
            raise AssertionError('Эндпоинт практикума не доступен')
        return response.json()
    except Exception as error:
        logger.error(f'Ошибка при запросе эндпоинта: {error}')
        raise AssertionError('Ошибка при запросе эндпоинта')
    return response.json()


def check_response(response):
    """Проверка API ответа."""
    if not isinstance(response, dict):
        raise TypeError('Ответ не формата dict')
    if "homeworks" not in response:
        raise KeyError('Ответ не содержит ключ homeworks.')
    if "current_date" not in response:
        raise KeyError('Ответ не содержит ключ current_date.')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Ответ не формата list')
    return homeworks


def parse_status(homework):
    """Парсинг статуса ответа."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(f'Неизвестный статус {homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Нет переменной окружения')
        sys.exit('Нет переменной окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_status = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if isinstance(homework, list) and homework:
                status = parse_status(homework[0])
            else:
                logger.info('Нет домашней работы.')
                raise AssertionError('Нет домашней работы.')
            if status != last_status:
                send_message(bot=bot, message=status)
                last_status = status
            else:
                logger.debug('Статус домашней работы не изменился.')
            current_timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            send_message(bot=bot, message=message)
        else:
            logging.info('Программа отработала без ошибок.')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Работа бота завершена.')
        sys.exit(0)
