class SendMessageError(Exception):
    """Ошибка при отправке сообщения в телеграм"""
    pass


class MissingTokenError(Exception):
    """Отсутствие константы окружения"""
    pass


class HomeworkPracticumError(Exception):
    """Ошибки сервиса при взаимодействии с яндекс.домашка"""


class EndpointAPIError(HomeworkPracticumError):
    """Ошибка при запросе эндпоинта"""
    pass


class EndpointHTTPStatusError(HomeworkPracticumError):
    """Статус ответа эндпоинта вернул ошибку"""
    pass


class HomeworkJSONError(HomeworkPracticumError):
    """Нет домашней работы для проверки"""
    pass

