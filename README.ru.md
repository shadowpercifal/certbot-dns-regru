# certbot-dns-regru (русская версия)
Плагин аунтефикатор DNS для Certbot, работающий с Reg.ru

[**English**](README.md) | **Русский**

Плагин-аутентификатор для [certbot](https://certbot.eff.org/) для поддержки DNS‑проверок (dns‑01) для доменов, обслуживаемых DNS‑серверами [Reg.ru](https://www.reg.ru).

Особая благодарность @free2er за создание первоначальной версии плагина.

## Требования

- certbot (>= 0.21.1)

Для старых версий Ubuntu можно использовать PPA:  
[ppa:certbot/certbot](https://launchpad.net/~certbot/+archive/ubuntu/certbot)

## Установка

1. Установите плагин:

   ```bash
   sudo pip install certbot-dns-regru
   ```

2. Настройте файл с учётными данными Reg.ru:

   ```bash
   sudo nano /etc/letsencrypt/regru.ini
   ```

   Пример содержимого `regru.ini`:

   ```ini
   dns_regru_username = login
   dns_regru_password = password
   ```

   ### Не работает
   Если вы настроили авторизацию через SSL сертификат - укажите путь до сертификата и ключа в файле конфигурации
   ```
   dns_regru_cert_path=/path/to/cert.pem
   dns_regru_key_path=/path/to/key.pem
   ```
   
   Если вы используете услугу для управления внешним доменным именем - плагин автоматически пробует как обычный домен так и услугу с `"servtype":"srv_dns_both"`

3. Ограничьте права доступа к файлу (иначе ваши данные могут оказаться под угрозой):

   ```bash
   sudo chmod 0600 /etc/letsencrypt/regru.ini
   ```

## Использование

Запрос нового сертификата через certbot может выглядеть так (при необходимости скорректируйте пути и доменные имена).

Linux:

```bash
sudo certbot certonly \
  --authenticator dns-regru \
  --dns-regru-credentials /etc/letsencrypt/regru.ini \
  --dns-regru-propagation-seconds 180 \
  -d sub.domain.tld -d '*.wildcard.tld'
```

Windows (PowerShell):

```powershell
certbot certonly `
  --authenticator dns-regru `
  --dns-regru-credentials C:\path\to\regru.ini `
  --dns-regru-propagation-seconds 180 `
  -d sub.domain.tld -d '*.wildcard.tld'
```

- Рекомендуется заключать подстановочный домен (`*.example.com`) в одинарные кавычки, чтобы избежать конфликтов с консолью.

Продление сертификатов будет выполняться автоматически с использованием того же аутентификатора и тех же учётных данных.

Дополнительно см. `certbot --help certbot-dns-regru` для получения справки по параметрам плагина.

## Использование с SWAG (docker-swag)

Для работы плагина с контейнером [docker-swag](https://github.com/linuxserver/docker-swag) следуйте их [руководству](https://github.com/linuxserver/docker-swag?tab=readme-ov-file#certbot-plugins).

1. Добавьте в переменные окружения контейнера:

   ```text
   DOCKER_MODS=linuxserver/mods:universal-package-install
   INSTALL_PIP_PACKAGES=certbot-dns-regru
   ```

2. Отредактируйте файл `/config/dns-conf/regru.ini` в контейнере и укажите учётные данные

## Удаление

```bash
sudo pip uninstall certbot-dns-regru
```
