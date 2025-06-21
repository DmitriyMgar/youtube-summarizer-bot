# Устранение проблем с YouTube Summarizer Bot

## Проблема: "Failed to extract any player response"

### Описание
При использовании команд `/raw_subtitles` или `/corrected_subtitles` может возникать ошибка:
```
ERROR: [youtube] qOZnjHof2vA: Failed to extract any player response
```

Эта ошибка указывает на проблемы с доступом к YouTube API, обычно связанные с блокировкой YouTube в вашем регионе или сети.

### Диагностика

1. **Проверьте доступность YouTube:**
   ```bash
   ping youtube.com
   curl -I https://www.youtube.com
   ```

2. **Проверьте SSL соединение:**
   ```bash
   curl -I --connect-timeout 10 https://www.youtube.com
   ```

3. **Запустите диагностический скрипт:**
   ```bash
   cd youtube-summarizer-bot
   source venv/bin/activate
   python test_network.py
   ```

### Решения

#### 1. Использование VPN (Рекомендуется)

**Установка OpenVPN:**
```bash
sudo apt update
sudo apt install openvpn
```

**Подключение к VPN серверу:**
```bash
sudo openvpn --config your-vpn-config.ovpn
```

#### 2. Использование Tor

**Установка Tor:**
```bash
sudo apt install tor
sudo systemctl start tor
sudo systemctl enable tor
```

**Настройка прокси через Tor:**
```bash
export HTTP_PROXY=socks5://127.0.0.1:9050
export HTTPS_PROXY=socks5://127.0.0.1:9050
```

**Запуск бота с Tor:**
```bash
cd youtube-summarizer-bot
source venv/bin/activate
HTTP_PROXY=socks5://127.0.0.1:9050 HTTPS_PROXY=socks5://127.0.0.1:9050 python src/main.py
```

#### 3. Использование публичных прокси

**Найдите рабочий прокси:**
- https://free-proxy-list.net/
- https://www.proxy-list.download/
- https://spys.one/

**Настройка прокси:**
```bash
export HTTP_PROXY=http://proxy-ip:port
export HTTPS_PROXY=http://proxy-ip:port
```

#### 4. Смена DNS серверов

**Cloudflare DNS:**
```bash
sudo systemctl stop systemd-resolved
echo "nameserver 1.1.1.1" | sudo tee /etc/resolv.conf
echo "nameserver 1.0.0.1" | sudo tee -a /etc/resolv.conf
```

**Google DNS:**
```bash
sudo systemctl stop systemd-resolved
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf
```

#### 5. Использование мобильного интернета

Если у вас есть мобильный интернет без блокировок:
```bash
# Подключитесь к мобильной точке доступа
# Запустите бота через мобильное соединение
```

### Тестирование решений

После применения любого из решений, протестируйте работу:

```bash
cd youtube-summarizer-bot
source venv/bin/activate
python test_proxy.py
```

### Автоматическая настройка прокси

Бот автоматически определяет настройки прокси из переменных окружения:
- `HTTP_PROXY`
- `HTTPS_PROXY`
- `http_proxy`
- `https_proxy`

### Дополнительные настройки

#### Увеличение таймаутов
Если соединение медленное, можно увеличить таймауты в `src/youtube/processor.py`:
```python
'socket_timeout': 60,  # Увеличить до 60 секунд
'retries': 10,         # Увеличить количество попыток
```

#### Отключение SSL проверки
В крайнем случае можно отключить проверку SSL сертификатов:
```python
'nocheckcertificate': True,
'prefer_insecure': True,
```

### Альтернативные решения

#### Использование youtube-dl вместо yt-dlp
```bash
pip uninstall yt-dlp
pip install youtube-dl
```

#### Использование других библиотек
- `pytube` - альтернативная библиотека для YouTube
- `youtube-transcript-api` - только для субтитров (уже используется как fallback)

### Поддержка

Если ни одно из решений не помогает:

1. Проверьте логи бота на предмет дополнительной информации
2. Попробуйте другое время суток (возможны временные блокировки)
3. Обратитесь к системному администратору сети
4. Рассмотрите возможность смены хостинг-провайдера

### Профилактика

Для предотвращения проблем в будущем:

1. Регулярно обновляйте yt-dlp:
   ```bash
   pip install -U yt-dlp
   ```

2. Используйте стабильное VPN соединение

3. Мониторьте доступность YouTube API

4. Настройте автоматический fallback на альтернативные методы 