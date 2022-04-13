class SendMessageError(Exception):
    """Ошибка при отправке сообщения в телеграм"""
    pass


class EndpointAPIError(Exception):
    """Эндпоинт практикума недоступен"""
    pass


class HomeworkJSONError(Exception):
    """Нет домашней работы для проверки"""
    pass
