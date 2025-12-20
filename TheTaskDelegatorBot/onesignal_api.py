import requests
import json
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class OneSignalAPI:
    """
    OneSignal API интеграция для внешних уведомлений
    Без зависимостей от ID уведомлений
    """

    def __init__(self):
        """Инициализация OneSignal клиента"""
        self.base_url = "https://onesignal.com/api/v1"
        self.app_id = os.getenv("ONESIGNAL_APP_ID")
        self.api_key = os.getenv("ONESIGNAL_API_KEY")

        self.is_configured = bool(self.app_id and self.api_key)

        if not self.is_configured:
            logger.warning("OneSignal не настроен. Добавьте ONESIGNAL_APP_ID и ONESIGNAL_API_KEY в .env")
        else:
            logger.info(f"OneSignal инициализирован. App ID: {self.app_id[:8]}...")

    def send_notification(self,
                          contents: Dict[str, str],
                          headings: Optional[Dict[str, str]] = None,
                          included_segments: Optional[list] = None,
                          filters: Optional[list] = None,
                          data: Optional[Dict] = None,
                          url: Optional[str] = None,
                          priority: int = 10,
                          ttl: int = 259200) -> Dict[str, Any]:
        """
        Отправить уведомление через OneSignal API
        Возвращает только success/error без ID
        """
        if not self.is_configured:
            return {
                'success': False,
                'error': 'OneSignal not configured. Add credentials to .env',
                'service': 'onesignal'
            }

        # Подготовка payload
        payload = {
            "app_id": self.app_id,
            "contents": contents,
            "priority": priority,
            "ttl": ttl
        }

        if headings:
            payload["headings"] = headings

        if included_segments:
            payload["included_segments"] = included_segments
        elif filters:
            payload["filters"] = filters
        else:
            payload["included_segments"] = ["All"]

        if data:
            payload["data"] = data

        if url:
            payload["url"] = url

        try:
            logger.info(f"📤 Отправка OneSignal уведомления")

            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Basic {self.api_key}"
            }

            # Используем json параметр для автоматической сериализации
            response = requests.post(
                f"{self.base_url}/notifications",
                headers=headers,
                json=payload,
                timeout=15
            )

            # Проверяем успешный статус
            if response.status_code in [200, 201]:
                logger.info("✅ OneSignal уведомление отправлено успешно")
                return {
                    'success': True,
                    'service': 'onesignal',
                    'status_code': response.status_code
                }
            else:
                logger.warning(f"⚠️ OneSignal ответил с кодом: {response.status_code}")
                try:
                    error_data = response.json()
                    logger.warning(f"Ошибки: {error_data.get('errors', ['Unknown'])}")
                    return {
                        'success': False,
                        'error': f"HTTP {response.status_code}: {error_data.get('errors', ['Unknown'])[0]}",
                        'service': 'onesignal',
                        'status_code': response.status_code
                    }
                except:
                    return {
                        'success': False,
                        'error': f"HTTP {response.status_code}",
                        'service': 'onesignal',
                        'status_code': response.status_code
                    }

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ OneSignal API ошибка: {e}")
            return {
                'success': False,
                'error': f"OneSignal API error: {str(e)}",
                'service': 'onesignal'
            }
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'service': 'onesignal'
            }

    def send_task_notification(self,
                               task_title: str,
                               from_user: str,
                               task_description: Optional[str] = None,
                               task_id: Optional[int] = None,
                               deadline: Optional[str] = None,
                               priority_level: str = "normal") -> Dict[str, Any]:
        """
        Специальный метод для уведомлений о задачах
        Упрощенный - не зависит от ID
        """
        # Определяем приоритет OneSignal
        priority_map = {
            "low": 5,
            "normal": 7,
            "high": 9,
            "urgent": 10
        }
        priority = priority_map.get(priority_level, 7)

        # Формируем содержимое
        message_parts = []
        if task_description:
            message_parts.append(f"📝 {task_description}")
        if from_user:
            message_parts.append(f"👤 От: {from_user}")
        if deadline:
            message_parts.append(f"⏰ Срок: {deadline}")

        message_text = "\n".join(message_parts) if message_parts else "Новая задача!"

        contents = {
            "en": f"New task: {task_title}",
            "ru": message_text
        }

        headings = {
            "en": "📋 TaskBuddy",
            "ru": f"📋 {task_title}"
        }

        # Дополнительные данные
        data = {
            "type": "task_notification",
            "task_title": task_title,
            "from_user": from_user,
            "priority": priority_level,
            "source": "telegram_bot"
        }

        # URL для открытия бота
        url = "https://t.me/TheTaskDelegatorBot"

        return self.send_notification(
            contents=contents,
            headings=headings,
            included_segments=["Subscribed Users"],
            data=data,
            url=url,
            priority=priority
        )

    def send_reminder_notification(self,
                                   task_title: str,
                                   hours_left: int,
                                   task_id: Optional[int] = None) -> Dict[str, Any]:
        """Отправить напоминание о дедлайне"""
        if hours_left <= 1:
            message = f"⏳ ОСТАЛСЯ 1 ЧАС! Задача: {task_title}"
            priority = 10
            headings = {"ru": "🚨 СРОЧНО! Задача скоро истекает"}
        elif hours_left <= 24:
            message = f"⏰ Напоминание: задача '{task_title}' через {hours_left} часов"
            priority = 8
            headings = {"ru": "⏰ Напоминание о задаче"}
        else:
            message = f"📅 Задача '{task_title}' через {hours_left} часов"
            priority = 6
            headings = {"ru": "📅 Напоминание"}

        contents = {"ru": message}

        data = {
            "type": "reminder",
            "task_title": task_title,
            "hours_left": hours_left
        }

        return self.send_notification(
            contents=contents,
            headings=headings,
            data=data,
            priority=priority
        )

    def get_app_stats(self) -> Dict[str, Any]:
        """Получить статистику приложения (работает без проблем)"""
        if not self.is_configured:
            return {'success': False, 'error': 'Not configured'}

        try:
            url = f"{self.base_url}/apps/{self.app_id}"
            headers = {"Authorization": f"Basic {self.api_key}"}

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            app_info = response.json()

            return {
                'success': True,
                'app_name': app_info.get('name'),
                'players': app_info.get('players'),
                'messageable_players': app_info.get('messageable_players'),
                'created_at': app_info.get('created_at')
            }

        except Exception as e:
            logger.error(f"Error getting app stats: {e}")
            return {'success': False, 'error': str(e)}

    def test_connection(self) -> Dict[str, Any]:
        """Тестирование подключения к OneSignal"""
        if not self.is_configured:
            return {
                'success': False,
                'error': 'Not configured',
                'configured': False
            }

        # Пробуем отправить тестовое уведомление
        test_result = self.send_notification(
            contents={"ru": "🔧 Тестовое уведомление от TaskBuddy Bot"},
            headings={"ru": "✅ OneSignal подключен"},
            included_segments=["All"]
        )

        if test_result['success']:
            # Получаем статистику приложения
            stats = self.get_app_stats()

            return {
                'success': True,
                'configured': True,
                'notification_sent': True,
                'app_stats': stats if stats['success'] else None
            }
        else:
            return {
                'success': False,
                'configured': True,
                'error': test_result.get('error'),
                'notification_sent': False
            }


# Глобальный экземпляр для использования во всем приложении
onesignal_api = OneSignalAPI()