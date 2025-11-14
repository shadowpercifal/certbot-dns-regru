# certbot-dns-regru
Reg.ru DNS authenticator plugin for Certbot

English|[Русский](README.ru.md)

An authenticator plugin for [certbot](https://certbot.eff.org/) to support [Let's Encrypt](https://letsencrypt.org/) 
DNS challenges (dns-01) for domains managed by the nameservers of [Reg.ru](https://www.reg.ru).

Huge thanks to @free2er for creating initial version

## Requirements
* certbot (>=0.21.1)

For older Ubuntu distributions check out this PPA: 
[ppa:certbot/certbot](https://launchpad.net/~certbot/+archive/ubuntu/certbot)

## Installation
1. First install the plugin:
   ```
   sudo pip install certbot-dns-regru
   ```

2. Configure it with your Reg.ru Credentials:
   ```
   sudo nano /etc/letsencrypt/regru.ini
   ```

3. Make sure the file is only readable by root! Otherwise all your domains might be in danger:
   ```
   sudo chmod 0600 /etc/letsencrypt/regru.ini
   ```

## Usage
Request new certificates via a certbot invocation like this (adjust paths as needed):

Linux:

```
sudo certbot certonly \
   --authenticator dns-regru \
   --dns-regru-credentials /etc/letsencrypt/regru.ini \
   --dns-regru-propagation-seconds 180 \
   -d sub.domain.tld -d '*.wildcard.tld'
```

Windows (PowerShell):

```
certbot certonly \
   --authenticator dns-regru \
   --dns-regru-credentials C:\path\to\regru.ini \
   --dns-regru-propagation-seconds 180 \
   -d sub.domain.tld -d '*.wildcard.tld'
```

- Note that shell might try to resolve wildcard subdomain (`*`), you should put in in parentheses

Renewals will automatically be performed using the same authenticator and credentials by certbot.

See also `certbot --help certbot-dns-regru` for further information.

## SWAG

To use this plugin with [docker-swag](https://github.com/linuxserver/docker-swag) you need to follow their [guide](https://github.com/linuxserver/docker-swag?tab=readme-ov-file#certbot-plugins)

Add the following environment variables to your container:

```
DOCKER_MODS=linuxserver/mods:universal-package-install
INSTALL_PIP_PACKAGES=certbot-dns-regru
```

Then modify `/config/dns-conf/regru.ini` and provide credentials


## Removal
```
   sudo pip uninstall certbot-dns-regru
```
