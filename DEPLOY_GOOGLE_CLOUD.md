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
sudo apt install -y python3 python3-pip python3-venv git chromium chromium-driver
```

## 3. Завантаж проєкт

```bash
git clone YOUR_REPO_URL
cd olx_notify_me_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.exsample .env
nano .env
```

У `.env` обов'язково:

```env
TELEGRAM_TOKEN=...
ADMIN_TELEGRAM_IDS=YOUR_TELEGRAM_ID
WORKERS_NUMBER=1
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

## 6. Адмін-функції в Telegram

Для користувачів з `ADMIN_TELEGRAM_IDS` або з прапорцем `is_admin` у БД:

- статистика
- список користувачів
- всі моніторинги
- останні оголошення
- Instagram підписки
- логи
- ручний запуск перевірок OLX/Rieltor та Instagram

## 7. Оновлення

```bash
cd ~/olx_notify_me_bot
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart olx-notify-bot
```
