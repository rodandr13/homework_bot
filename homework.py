import os
import logging
import sys
import time
import json

from http import HTTPStatus

import requests
import telegram

from dotenv import load_dotenv


load_dotenv()

PRACTICUM_TOKEN = 'AQAAAAAD7JqhAAYckda81eiXxk-_uuG5WGjYOds'
TELEGRAM_TOKEN = '5062990002:AAGME8a2Wx49EIbr4Kv9bI1ZqlClDl61MCI'
TELEGRAM_CHAT_ID = 318657667

RETRY_TIME = 60
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
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError:
        logger.error('Телеграм не работает')
    logger.info(f'Сообщение отправлено: {message}')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': 0}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error('URL практикума не доступен')
            raise AssertionError('URL практикума не доступен')
        return response.json()
    except Exception as error:
        logger.error(f'Ошибка при запросе: {error}')
        raise AssertionError('Ошибка при запросе')


def check_response(response):
    try:
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            raise ValueError
        if not homeworks:
            raise ValueError
    except KeyError:
        raise KeyError('В ответе что-то не то.')
    except TypeError:
        raise TypeError('Недопустимый тип данных.')
    return homeworks


def parse_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(f'Неизвестный статус {homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))

def main():
    """Основная логика работы бота."""
    if not check_tokens:
        raise AssertionError('')
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
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            send_message(bot=bot, message=message)
        else:
            logging.info('Программа отработала без ошибок.')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
