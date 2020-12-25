# MegaD HomeAssistant custom component

Интеграция с [MegaD-2561](https://www.ab-log.ru/smart-house/ethernet/megad-2561)

## Основные особенности:
- Настройка как из yaml так и из веб-интерфейса
- При настройки из веба все порты автоматически добавляются как устройства (для обычных релейных выходов создается 
  `light`, для шим - `light` с поддержкой яркости, для цифровых входов `binary_sensor`)
- Возможность работы с несколькими megad
- Обратная связь по mqtt
- Команды выполняются друг за другом без конкурентного доступа к ресурсам megad
## Устройства
Пока поддерживаются только базовые устройства: light, switch, binary_sensor. light может работать как диммер
## Установка
В папке config/custom_components выполнить:
```shell
git clone https://github.com/andvikt/mega.git
```
## Зависимости
Перед использованием необходимо настроить интеграцию mqtt в HomeAssistant

Перезагрузить HA
## Настройка из веб-интерфейса
`Настройки` -> `Интеграции` -> `Добавить интеграцию` в поиске ищем mega

## Пример настройки с помощью yaml:
```yaml
mega: 
  mega1:
    host: 192.168.0.14
    name: hello
    password: sec
    mqtt_id: mega # это id в конфиге меги

light:
  - platform: mega
    mega1:
      switch:
        - 1 # можно просто перечислить порты
        - 2
        - 3
      dimmer:
        - port: 7
          name: hello # можно использовать расширенный вариант с названиями
        - 9
        - 10

switch:
  - platform: mega
    mega1:
      - 11

```

