#!/usr/bin/env bash
# Mandatory live test runner for certbot-dns-regru
#
# Always runs live DNS add/delete tests (dns_test_real) against Reg.ru API.
# Credentials & domain can be supplied via environment variables OR CLI flags.
# If still missing, an interactive prompt is used (unless -y supplied).
# Works with bash (Git Bash / WSL / Linux). For PowerShell use run_tests.py.
#
# Steps:
# 1. Optionally create/activate virtualenv (skip with -n)
# 2. Install package editable if requested (auto yes with -y)
# 3. Collect credentials & domain (env, flags, or prompt)
# 4. Run live tests (dns_test_real)
#
# Required:
#   REG_RU_USERNAME  / -u <user>
#   REG_RU_PASSWORD  / -p <pass>
#   REG_RU_TEST_DOMAIN / -d <domain>
# Optional:
#   REG_RU_TEST_SUBDOMAIN / -s <label> (default: sub)
#   REG_RU_CERT_PATH / -c <path>  (optional client SSL cert PEM)
#   REG_RU_KEY_PATH  / -k <path>  (optional client SSL key  PEM)
# Flags:
#   -n  Skip virtualenv creation/activation
#   -y  Non-interactive: do not prompt; abort if required values missing
#   -h  Show help
#
# Examples:
#   REG_RU_USERNAME=u REG_RU_PASSWORD=p REG_RU_TEST_DOMAIN=example.com bash test.sh
#   bash test.sh -u u -p p -d example.com -s test
#   bash test.sh -u u -p p -d example.com -c /path/cert.pem -k /path/key.pem
#   bash test.sh -u u -p p -d example.com -n -y   # CI mode

set -euo pipefail

echo "=== certbot-dns-regru Live Test Runner ==="

SHOW_HELP=0
SKIP_VENV=0
NON_INTERACTIVE=0

while getopts ":u:p:d:s:c:k:nyh" opt; do
	case $opt in
		u) REG_RU_USERNAME="$OPTARG" ;;
		p) REG_RU_PASSWORD="$OPTARG" ;;
		d) REG_RU_TEST_DOMAIN="$OPTARG" ;;
		s) REG_RU_TEST_SUBDOMAIN="$OPTARG" ;;
		c) REG_RU_CERT_PATH="$OPTARG" ;;
		k) REG_RU_KEY_PATH="$OPTARG" ;;
		n) SKIP_VENV=1 ;;
		y) NON_INTERACTIVE=1 ;;
		h) SHOW_HELP=1 ;;
		:) echo "Missing argument for -$OPTARG" >&2; exit 2 ;;
		\?) echo "Unknown option: -$OPTARG" >&2; exit 2 ;;
	esac
done

if [[ $SHOW_HELP -eq 1 ]]; then
	grep '^#' "$0" | sed 's/^# //'
	exit 0
fi

# Detect Python interpreter (prefer python, fallback to python3)
if command -v python >/dev/null 2>&1; then
	PYTHON=python
elif command -v python3 >/dev/null 2>&1; then
	PYTHON=python3
else
	echo "Neither 'python' nor 'python3' found in PATH. Aborting." >&2
	exit 1
fi
echo "Using interpreter: $PYTHON"

if [[ $SKIP_VENV -eq 0 ]]; then
	read -r -p "Create/ensure virtualenv (.venv)? [Y/n]: " VENV_CHOICE
	VENV_CHOICE=${VENV_CHOICE:-Y}
	if [[ $VENV_CHOICE =~ ^[Yy]$ ]]; then
			if [[ ! -d .venv ]]; then
					echo "Creating virtualenv .venv"; $PYTHON -m venv .venv
			fi
			# shellcheck disable=SC1091
			source .venv/bin/activate || { echo "Failed to activate .venv"; exit 1; }
			echo "(venv active)"
	fi
else
	echo "Skipping virtualenv per -n flag"
fi

if [[ $NON_INTERACTIVE -eq 1 ]]; then
	INSTALL_CHOICE=Y
else
	read -r -p "Install/editable package (pip install -e .)? [Y/n]: " INSTALL_CHOICE
	INSTALL_CHOICE=${INSTALL_CHOICE:-Y}
fi
if [[ $INSTALL_CHOICE =~ ^[Yy]$ ]]; then
	$PYTHON -m pip install --upgrade pip >/dev/null
	$PYTHON -m pip install -e . certbot >/dev/null
fi

echo "Collecting mandatory Reg.ru credentials and test domain"

if [[ -z ${REG_RU_USERNAME:-} && $NON_INTERACTIVE -eq 0 ]]; then
	read -r -p "Reg.ru Username: " REG_RU_USERNAME
fi
if [[ -z ${REG_RU_PASSWORD:-} && $NON_INTERACTIVE -eq 0 ]]; then
	read -r -s -p "Reg.ru Password: " REG_RU_PASSWORD; echo
fi
if [[ -z ${REG_RU_TEST_DOMAIN:-} && $NON_INTERACTIVE -eq 0 ]]; then
	read -r -p "Base domain (e.g. example.com): " REG_RU_TEST_DOMAIN
fi
if [[ -z ${REG_RU_TEST_SUBDOMAIN:-} && $NON_INTERACTIVE -eq 0 ]]; then
	read -r -p "Subdomain label for tests (default: sub): " REG_RU_TEST_SUBDOMAIN
fi
REG_RU_TEST_SUBDOMAIN=${REG_RU_TEST_SUBDOMAIN:-sub}

# Optional client cert/key prompts (press Enter to skip)
if [[ -z ${REG_RU_CERT_PATH:-} && $NON_INTERACTIVE -eq 0 ]]; then
	read -r -p "Client SSL certificate path (optional): " REG_RU_CERT_PATH || true
fi
if [[ -z ${REG_RU_KEY_PATH:-} && $NON_INTERACTIVE -eq 0 ]]; then
	read -r -p "Client SSL key path (optional): " REG_RU_KEY_PATH || true
fi

if [[ -z ${REG_RU_USERNAME:-} || -z ${REG_RU_PASSWORD:-} || -z ${REG_RU_TEST_DOMAIN:-} ]]; then
	echo "All of REG_RU_USERNAME, REG_RU_PASSWORD, REG_RU_TEST_DOMAIN are required." >&2
	if [[ $NON_INTERACTIVE -eq 1 ]]; then
		echo "Non-interactive mode (-y) set; aborting." >&2
		exit 1
	else
		echo "Re-run and provide missing values via env vars or flags (-u/-p/-d)." >&2
		exit 1
	fi
fi

export REG_RU_USERNAME REG_RU_PASSWORD REG_RU_TEST_DOMAIN REG_RU_TEST_SUBDOMAIN RUN_REG_RU_LIVE_TESTS=1
if [[ -n ${REG_RU_CERT_PATH:-} ]]; then
	export REG_RU_CERT_PATH
fi
if [[ -n ${REG_RU_KEY_PATH:-} ]]; then
	export REG_RU_KEY_PATH
fi

echo "Running mandatory live tests (dns_test_real)"
LIVE_STATUS=0
$PYTHON -m unittest certbot_regru.dns_test_real -v || LIVE_STATUS=$? || true

echo "--- Summary ---"
echo "Live tests exit code: $LIVE_STATUS"
if [[ $LIVE_STATUS -eq 0 ]]; then
  echo "Live tests passed."; exit 0
else
  echo "Live tests failed."; exit 1
fi
