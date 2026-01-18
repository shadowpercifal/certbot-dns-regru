"""Live tests for certbot_regru.dns using the real Reg.ru API.

These tests create and delete temporary TXT records on a real domain you own.
They are DISABLED unless required environment variables are present and
RUN_REG_RU_LIVE_TESTS=1 is set.

Required environment variables:
  REG_RU_USERNAME        Reg.ru account login
  REG_RU_PASSWORD        Reg.ru account password
  REG_RU_TEST_DOMAIN     Base domain existing in your Reg.ru DNS (e.g. example.com)
  RUN_REG_RU_LIVE_TESTS  Must be '1' to enable execution

Optional:
  REG_RU_TEST_SUBDOMAIN  Subdomain label to test (default: 'sub')

Safety:
- Records use a random token to avoid collisions.
- No sleep for DNS propagation (we validate API success only, not external DNS).
- Use in CI only if you accept modifying live DNS zone.

Run (PowerShell):
  $env:REG_RU_USERNAME='user'
  $env:REG_RU_PASSWORD='pass'
  $env:REG_RU_TEST_DOMAIN='example.com'
  $env:RUN_REG_RU_LIVE_TESTS='1'
  python -m unittest certbot_regru.dns_test_real -v
"""
import os
import unittest
import secrets
import string
import tempfile
from types import SimpleNamespace

from certbot import errors
from certbot_regru.dns import Authenticator
from certbot_regru.dns import _RegRuClient  # fallback direct usage if needed
try:
    from certbot.tests import util as test_util  # for patching display
except Exception:  # pragma: no cover
    test_util = None

REQUIRED_VARS = ["REG_RU_USERNAME", "REG_RU_PASSWORD", "REG_RU_TEST_DOMAIN", "RUN_REG_RU_LIVE_TESTS"]

LIVE_ENABLED = all(os.environ.get(v) for v in REQUIRED_VARS) and os.environ.get("RUN_REG_RU_LIVE_TESTS") == "1"

USERNAME = os.environ.get("REG_RU_USERNAME")
PASSWORD = os.environ.get("REG_RU_PASSWORD")
BASE_DOMAIN = os.environ.get("REG_RU_TEST_DOMAIN")  # e.g. example.com
SUB_LABEL = os.environ.get("REG_RU_TEST_SUBDOMAIN", "sub")  # sub.example.com


def _rand_token(length=20):
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@unittest.skipUnless(LIVE_ENABLED, "Live Reg.ru tests disabled (set env vars & RUN_REG_RU_LIVE_TESTS=1)")
class RegRuLiveTests(unittest.TestCase):
    """Live add/delete tests against Reg.ru DNS API using a temporary regru.ini credentials file."""

    def setUp(self):
        if BASE_DOMAIN is None or BASE_DOMAIN.count('.') < 1:
            self.skipTest("REG_RU_TEST_DOMAIN must be a valid base domain (e.g., example.com)")
        if not USERNAME or not PASSWORD:
            self.skipTest("REG_RU_USERNAME and REG_RU_PASSWORD must be set for live tests")

        # Patch display utility to avoid early UI errors when configuring credentials
        if test_util is not None:
            try:
                test_util.patch_display_util()
            except Exception:
                pass

        # Create a temporary regru.ini file with proper key names expected by the plugin
        self.temp_credentials_file = tempfile.NamedTemporaryFile(prefix="regru", suffix=".ini", delete=False)
        creds_content = [f"dns_regru_username={USERNAME}", f"dns_regru_password={PASSWORD}"]
        creds_content = "\n".join(creds_content) + "\n"
        self.temp_credentials_file.write(creds_content.encode("utf-8"))
        self.temp_credentials_file.flush()
        self.temp_credentials_file.close()

        # Build a minimal config object providing path and propagation seconds
        self.config = SimpleNamespace(dns_regru_credentials=self.temp_credentials_file.name, dns_regru_propagation_seconds=0)

        # Instantiate authenticator which will read credentials file
        self.auth = Authenticator(self.config, "dns-regru")
        self.auth._setup_credentials()  # pylint: disable=protected-access
        # Get client via authenticator (ensures same path used)
        self.client = self.auth._get_regru_client()  # pylint: disable=protected-access

        # Random TXT content each test run
        self.txt_value = _rand_token(32)

    def _record_name(self, *labels):
        return '.'.join(labels + (BASE_DOMAIN,))

    def test_add_and_delete_root_domain_record(self):
        record_name = self._record_name('_acme-challenge')
        # Add
        self.client.add_txt_record(record_name, self.txt_value)
        # Delete
        self.client.del_txt_record(record_name, self.txt_value)

    def test_add_and_delete_subdomain_record(self):
        record_name = self._record_name('_acme-challenge', SUB_LABEL)
        self.client.add_txt_record(record_name, self.txt_value)
        self.client.del_txt_record(record_name, self.txt_value)

    def test_add_and_delete_arbitrary_token_label(self):
        token_label = _rand_token(8)
        record_name = self._record_name('_acme-challenge', token_label)
        self.client.add_txt_record(record_name, self.txt_value)
        self.client.del_txt_record(record_name, self.txt_value)

    def test_invalid_credentials_fail(self):
        bad_user = USERNAME + '_bad'
        bad_client = _RegRuClient(bad_user, PASSWORD)
        record_name = self._record_name('_acme-challenge', 'badcreds')
        with self.assertRaises(errors.PluginError):
            bad_client.add_txt_record(record_name, self.txt_value)

    def test_delete_nonexistent_record_is_safe(self):
        record_name = self._record_name('_acme-challenge', 'nonexistent')
        # Should not raise; deletion errors are logged only.
        self.client.del_txt_record(record_name, self.txt_value)

    def tearDown(self):  # pragma: no cover
        try:
            if hasattr(self, 'temp_credentials_file'):
                os.unlink(self.temp_credentials_file.name)
        except Exception:
            pass


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
