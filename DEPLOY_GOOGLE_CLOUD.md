# Deploy To Google Cloud Free Tier

Ця інструкція описує безкоштовний або майже безкоштовний деплой проєкту на Google Cloud.

Рекомендований варіант для цього проєкту: Google Compute Engine `e2-micro` + Docker Compose + безкоштовний український домен `.pp.ua` + Caddy для HTTPS.

Cloud Run менш підходить, бо проєкт має кілька довгоживучих сервісів: `web`, `worker`, `beat`, `bot`, `redis`, Playwright і локальну SQLite базу для логів.

## 1. Google Cloud Free Tier

Створи VM у Google Cloud:

- Product: `Compute Engine`
- Machine type: `e2-micro`
- Region: тільки `us-central1`, `us-west1` або `us-east1`
- OS: `Ubuntu 24.04 LTS`
- Disk: `Standard persistent disk`, до `30 GB`
- Firewall: увімкнути `Allow HTTP traffic` і `Allow HTTPS traffic`

Не використовуй `Cloud SQL`, `Load Balancer`, `Cloud NAT`, `Cloud DNS`, якщо хочеш тримати деплой максимально безкоштовним.

Рекомендовано створити budget alert:

```text
Billing -> Budgets & alerts -> Create budget
```

Наприклад, встанови бюджет `$1`.

## 2. Підключення до VM

Підключись до VM:

```bash
ssh your-user@VM_EXTERNAL_IP
```

Онови сервер:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl ca-certificates
```

Встанови Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Вийди з SSH і зайди знову, щоб застосувалась група `docker`.

Перевір Docker Compose:

```bash
docker compose version
```

## 3. Додай Swap

На `e2-micro` мало RAM, тому краще додати swap:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 4. Завантаж Проєкт

```bash
git clone YOUR_REPO_URL
cd olx_notify_me_bot
```

Створи `.env`:

```bash
cp .env.exsample .env
nano .env
```

Приклад важливих змінних:

```env
DEBUG=false
SECRET_KEY=your-long-secret-key
ALLOWED_HOSTS=my-olx-bot.pp.ua,VM_EXTERNAL_IP

DB_HOST=your-external-postgres-host
DB_NAME=your-db
DB_USER=your-user
DB_PASSWORD=your-password
DB_PORT=5432

LOG_DB_NAME=/app/local_data/job_logs.sqlite3

TELEGRAM_TOKEN=your-token
TELEGRAM_BOT_USERNAME=your_bot_username_without_at
WEB_REGISTRATION_BASE_URL=https://my-olx-bot.pp.ua
WEB_REGISTRATION_CODE_TTL_MINUTES=15
```

## 5. Запусти Проєкт

```bash
docker compose up --build -d
```

Міграції:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py migrate --database logs audit_logs
docker compose exec web python manage.py createsuperuser
```

Перевір логи:

```bash
docker compose logs -f web
docker compose logs -f worker
docker compose logs -f bot
```

## 6. Безкоштовний Український Домен `.pp.ua`

Для українського безкоштовного домену можна використати зону `.pp.ua`, наприклад:

```text
my-olx-bot.pp.ua
```

Це безкоштовний український домен. Його можна зареєструвати через акредитованого реєстратора, наприклад NIC.UA:

```text
https://nic.ua/uk/domains/.pp.ua
```

Загальні кроки:

1. Перевір, чи вільний потрібний домен `.pp.ua`.
2. Подай заявку на реєстрацію через реєстратора.
3. Активуй домен через SMS або Telegram-бота `@ppuabot`.
4. Додай DNS `A record`, який вказує на `External IP` твоєї Google VM.

Приклад DNS запису:

```text
Type: A
Name: @
Value: VM_EXTERNAL_IP
TTL: default
```

Якщо хочеш використовувати `www`, додай ще один запис:

```text
Type: CNAME
Name: www
Value: my-olx-bot.pp.ua
TTL: default
```

Після цього онови `.env`:

```env
ALLOWED_HOSTS=my-olx-bot.pp.ua,www.my-olx-bot.pp.ua
WEB_REGISTRATION_BASE_URL=https://my-olx-bot.pp.ua
```

Важливо: для `.pp.ua` можуть бути обмеження, наприклад до 3 доменів на один номер за 30 днів. Також домен зазвичай треба продовжувати раз на рік.

## 7. HTTPS Через Caddy

Встанови Caddy:

```bash
sudo apt install -y caddy
```

Відкрий конфіг:

```bash
sudo nano /etc/caddy/Caddyfile
```

Приклад:

```caddy
my-olx-bot.pp.ua {
    reverse_proxy 127.0.0.1:8000
}
```

Перезапусти Caddy:

```bash
sudo systemctl reload caddy
```

Caddy сам отримає безкоштовний SSL-сертифікат Let's Encrypt.

## 8. Оновлення Після Змін

Коли оновлюєш код:

```bash
git pull
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py migrate --database logs audit_logs
```

Сайт буде доступний за адресою:

```text
https://my-olx-bot.pp.ua
```

## Важливі Нотатки

- Для безкоштовного Compute Engine використовуй тільки регіони `us-central1`, `us-west1` або `us-east1`.
- Не створюй Google Cloud Load Balancer, якщо хочеш уникнути платних витрат.
- Не використовуй Cloud SQL для цього free-tier варіанту.
- Основна БД може бути зовнішнім free PostgreSQL.
- Логи проєкту зберігаються в локальній SQLite базі через `LOG_DB_NAME`.
- Домен `.pp.ua` безкоштовний, але його треба активувати через SMS або Telegram-бота і продовжувати після завершення строку дії.
- Після деплою варто перевірити Billing Dashboard і Budget Alerts.
