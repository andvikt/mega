# MegaD Homeassistant custom component

Интеграция с megad

## Основные особенности:
    
- Возможность работы с несколькими megad
- Обратная связь по mqtt
- Команды выполняются друг за другом без конкурентного доступа к ресурсам megad
## Устройства
Пока поддерживаются только базовые устройства: light, switch. light может работать как диммер
## Установка
В папке config/custom_components выполнить:
```shell
git clone https://github.com/andvikt/mega.git
```

## Пример настройки:
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

