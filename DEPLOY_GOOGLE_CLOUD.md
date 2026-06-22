# Deploy on Google Cloud e2-micro (Telegram-only)

Мінімальний async Telegram-бот без Docker, Django, Redis і Celery.

## 1. Створи VM

- Machine type: `e2-micro`
- OS: `Ubuntu 24.04 LTS`
- Disk: `20-30 GB`
- Swap: `2 GB` (рекомендовано)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. Встанови залежності

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git nano \
  libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
  libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
  libgbm1 libasound2t64 libpango-1.0-0 libcairo2
```

## 3. Завантаж проєкт

```bash
git clone https://github.com/vkovalchuk-91/olx_notify_me_bot
cd olx_notify_me_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
sudo playwright install-deps chromium
cp .env.exsample .env
nano .env
```

Якщо `nano` недоступний:

```bash
sudo apt install -y nano
# або
vi .env
```

У `.env` обов'язково:

```env
TELEGRAM_TOKEN=...
ADMIN_TELEGRAM_IDS=YOUR_TELEGRAM_ID
WORKERS_NUMBER=1
REQUEST_INTERVAL_MINUTES=5
INSTA_REQUEST_INTERVAL_MINUTES=30
```

Опційно — системний Chromium замість bundled Playwright:

```env
CHROME_BIN=/usr/bin/chromium
```

Перевір Playwright (у venv):

```bash
source .venv/bin/activate
python -c "
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = await browser.new_page()
        await page.goto('about:blank')
        print('Playwright OK')
        await browser.close()

asyncio.run(main())
"
```

## 4. Запуск

```bash
source .venv/bin/activate
python main.py
```

## 5. systemd service

```bash
sudo nano /etc/systemd/system/olx-notify-bot.service
```

```ini
[Unit]
Description=OLX Notify Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/olx_notify_me_bot
Environment=PATH=/home/YOUR_USER/olx_notify_me_bot/.venv/bin
Environment=PLAYWRIGHT_BROWSERS_PATH=/home/YOUR_USER/.cache/ms-playwright
ExecStart=/home/YOUR_USER/olx_notify_me_bot/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable olx-notify-bot
sudo systemctl start olx-notify-bot
sudo systemctl status olx-notify-bot
```

Логи:

```bash
sudo journalctl -u olx-notify-bot -f
```

## 6. Адмін-функції в Telegram

Для користувачів з `ADMIN_TELEGRAM_IDS` або з прапорцем `is_admin` у БД:

- статистика
- список користувачів
- всі моніторинги
- останні оголошення
- логи
- ручний запуск перевірок OLX/Rieltor та Instagram

## 7. Оновлення

```bash
cd ~/olx_notify_me_bot
git pull
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
sudo systemctl restart olx-notify-bot
```
