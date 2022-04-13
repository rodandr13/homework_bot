import os
import logging
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (
    SendMessageError,
    EndpointAPIError,
    HomeworkJSONError,
    EndpointHTTPStatusError,
    MissingTokenError,
    HomeworkPracticumError
)


load_dotenv()

PRACTICUM_TOKEN = os.getenv('practicum_token')
TELEGRAM_TOKEN = os.getenv('telegram_token')
TELEGRAM_CHAT_ID = os.getenv('telegram_chat_id')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_RESULTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)

handler = RotatingFileHandler(
    'logs.log',
    maxBytes=50_000_000,
    backupCount=5
)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение отправлено: {message}')
    except telegram.TelegramError as error:
        raise SendMessageError(f'Ошибка телеграма: {error}')


def get_api_answer(current_timestamp):
    """Получения ответа от API эндпоинта."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise EndpointHTTPStatusError('Эндпоинт практикума не доступен')
        return response.json()
    except Exception as error:
        raise EndpointAPIError(f'Ошибка при запросе эндпоинта: {error}')


def check_response(response):
    """Проверка API ответа."""
    if not isinstance(response, dict):
        raise TypeError('Ответ не формата dict')
    if 'homeworks' not in response:
        raise KeyError('Ответ не содержит ключ homeworks.')
    if 'current_date' not in response:
        raise KeyError('Ответ не содержит ключ current_date.')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Ответ не формата list')
    return homeworks


def parse_status(homework):
    """Парсинг статуса ответа."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_RESULTS[homework_status]
    if homework_status not in HOMEWORK_RESULTS:
        raise KeyError(f'Неизвестный статус {homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Нет переменной окружения')
        raise MissingTokenError('Проверьте значение токенов')
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
                raise HomeworkJSONError('Нет домашней работы.')
            if status != last_status:
                send_message(bot=bot, message=status)
                last_status = status
            else:
                logger.debug('Статус домашней работы не изменился.')
            current_timestamp = response['current_date']
        except HomeworkPracticumError as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        except Exception as error:
            logger.error(error)
        else:
            logger.info('Программа отработала без ошибок.')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    )

    try:
        main()
    except KeyboardInterrupt:
        print('Работа бота завершена.')
        sys.exit(0)
