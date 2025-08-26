"""
Модуль для обработки webhook запросов от TradingView и других источников
"""
import os
import logging
from typing import Dict, Any, Tuple
from flask import request
from dotenv import load_dotenv

from .database import db_manager
from .binance_client import binance_client
from .messages_database import messages_db_manager

# Настройка логирования
logger = logging.getLogger(__name__)

load_dotenv()

class WebhookHandler:
    """Класс для обработки webhook запросов"""
    
    def __init__(self):
        self.signal_key = os.getenv("SIGNAL_KEY")
        if not self.signal_key:
            raise ValueError("SIGNAL_KEY должен быть установлен в .env файле")
    
    def validate_request(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Валидирует входящий запрос
        
        Args:
            data: Данные запроса
            
        Returns:
            Tuple[bool, str]: (валидность, сообщение об ошибке)
        """
        if not data:
            return False, "Пустые данные запроса"
        
        if 'auth_key' not in data:
            return False, "Отсутствует auth_key"
        
        if data['auth_key'] != self.signal_key:
            return False, "Неверный auth_key"
        
        required_fields = ['action', 'symbol', 'quantity']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return False, f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
        
        # Проверяем корректность action
        valid_actions = ['ENTER_LONG', 'EXIT_LONG', 'ENTER_SHORT', 'EXIT_SHORT']
        if data['action'] not in valid_actions:
            return False, f"Неверное действие: {data['action']}. Допустимые: {', '.join(valid_actions)}"
        
        # Проверяем quantity
        try:
            quantity = float(data['quantity'])
            if quantity <= 0:
                return False, "Количество должно быть положительным числом"
        except (ValueError, TypeError):
            return False, "Неверный формат количества"
        
        return True, "OK"
    
    def extract_signal_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает и обрабатывает данные сигнала
        
        Args:
            data: Сырые данные запроса
            
        Returns:
            Dict[str, Any]: Обработанные данные сигнала
        """
        # Основные поля
        signal_data = {
            'action': data['action'],
            'symbol': data['symbol'],
            'quantity_raw': float(data['quantity']),
            'strategy': data.get('strategy', '')
        }
        
        # Подгоняем количество под требования Binance
        signal_data['quantity'] = binance_client.adjust_quantity(
            signal_data['symbol'], 
            signal_data['quantity_raw']
        )
        
        # Извлекаем дополнительные поля (кроме основных и служебных)
        CORE_FIELDS = {'auth_key', 'action', 'symbol', 'quantity', 'strategy'}
        extra_data = {k: v for k, v in data.items() if k not in CORE_FIELDS}
        
        if extra_data:
            signal_data['extra_data'] = extra_data
            logger.info(f"📋 Дополнительные поля: {extra_data}")
        
        return signal_data
    


    def execute_trading_action(self, signal_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Выполняет торговое действие
        
        Args:
            signal_data: Данные сигнала
            
        Returns:
            Tuple[bool, str, Dict]: (успех, сообщение, дополнительные данные)
        """
        action = signal_data['action']
        symbol = signal_data['symbol']
        quantity = signal_data['quantity']
        
        logger.info(f"🎯 Выполнение действия: {action} {symbol} {quantity}")
        
        try:
            if action == 'ENTER_LONG':
                success, message = binance_client.open_position(symbol, 'LONG', quantity)
            elif action == 'EXIT_LONG':
                success, message = binance_client.close_position(symbol, 'LONG', quantity)
            elif action == 'ENTER_SHORT':
                success, message = binance_client.open_position(symbol, 'SHORT', quantity)
            elif action == 'EXIT_SHORT':
                success, message = binance_client.close_position(symbol, 'SHORT', quantity)
            else:
                return False, f"Неизвестное действие: {action}", {}
            
            # Извлекаем order_id из ответа Binance
            extra_data = {}
            try:
                import json
                response_data = json.loads(message)
                if 'orderId' in response_data:
                    extra_data['binance_order_id'] = response_data['orderId']
                    extra_data['binance_status'] = response_data.get('status', 'UNKNOWN')
                    logger.info(f"📋 Сохранен order_id: {response_data['orderId']}")
            except:
                logger.warning("⚠️ Не удалось извлечь order_id из ответа")


            
            # Записываем ответ от Binance API в общую базу
            try:
                binance_response = json.loads(message) if isinstance(message, str) else message
                binance_response['e'] = 'BINANCE_API'
                messages_db_manager.log_message('BINANCE_API', binance_response)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось записать ответ Binance API: {e}")


            return success, message, extra_data






                
        except Exception as e:
            error_msg = f"Ошибка выполнения {action}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {}




    def process_webhook(self) -> Tuple[Dict[str, Any], int]:
        """
        Основная функция обработки webhook
        
        Returns:
            Tuple[Dict, int]: (ответ JSON, HTTP статус код)
        """
        try:
            # Проверяем режим позиций
            binance_client.check_position_mode()
            
            # Получаем данные запроса
            data = request.get_json()
            logger.info(f"🔔 Webhook получен: {data}")




            # Записываем сообщение от стратегии в общую базу
            from .messages_database import messages_db_manager
            try:
                strategy_message = data.copy()
                strategy_message['e'] = 'STRATEGY_SIGNAL'
                messages_db_manager.log_message('STRATEGY_SIGNAL', strategy_message)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось записать сообщение стратегии: {e}")



            
            # Валидируем запрос
            is_valid, error_message = self.validate_request(data)
            if not is_valid:
                logger.warning(f"⚠️ Невалидный запрос: {error_message}")
                return {"status": "error", "message": error_message}, 400
            
            # Извлекаем данные сигнала
            signal_data = self.extract_signal_data(data)
            
            # Выполняем торговое действие
            success, message, binance_extra_data = self.execute_trading_action(signal_data)

            # Объединяем дополнительные данные
            extra_data = signal_data.get('extra_data', {})
            extra_data.update(binance_extra_data)

            # Логируем в базу данных
            result_status = 'success' if success else 'error'
            signal_id = db_manager.log_signal(
                action=signal_data['action'],
                symbol=signal_data['symbol'],
                quantity=signal_data['quantity'],
                result=result_status,
                message=message,
                strategy=signal_data['strategy'],
                extra_data=extra_data
            )
            
            logger.info(f"📌 Сигнал #{signal_id} обработан: {result_status}")
            
            # Формируем ответ
            response = {
                'status': 'success' if success else 'error',
                'message': message,
                'signal_id': signal_id,
                'action': signal_data['action'],
                'symbol': signal_data['symbol'],
                'quantity': signal_data['quantity']
            }
            
            status_code = 200 if success else 500
            return response, status_code
            
        except Exception as e:
            error_msg = f"Критическая ошибка обработки webhook: {str(e)}"
            logger.error(f"💥 {error_msg}")
            
            # Пытаемся записать ошибку в БД
            try:
                db_manager.log_signal(
                    action="ERROR",
                    symbol="N/A",
                    quantity=0,
                    result="error",
                    message=error_msg,
                    strategy="system"
                )
            except:
                pass  # Игнорируем ошибки записи в БД
            
            return {"status": "error", "message": "Внутренняя ошибка сервера"}, 500

# Создаем глобальный экземпляр для использования в приложении
webhook_handler = WebhookHandler()

if __name__ == "__main__":
    # Тестирование модуля
    print("🧪 Тестирование модуля webhook_handler...")
    
    handler = WebhookHandler()
    
    # Тест валидации
    test_data = {
        'auth_key': 'test_key',
        'action': 'ENTER_LONG',
        'symbol': 'BTCUSDT',
        'quantity': '0.001',
        'strategy': 'test_strategy',
        'custom_field': 'custom_value'
    }
    
    is_valid, message = handler.validate_request(test_data)
    print(f"✅ Валидация (ожидается False): {is_valid}, {message}")
    
    # Тест извлечения данных
    signal_data = handler.extract_signal_data(test_data)
    print(f"✅ Извлеченные данные: {signal_data}")