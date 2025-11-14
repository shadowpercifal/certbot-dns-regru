"""DNS Authenticator for Reg.ru DNS."""
# Copyright (C) 2018 Max Pryakhin

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import logging

import json
import requests

import zope.interface

from certbot import errors
from certbot import interfaces
from certbot.plugins import dns_common

logger = logging.getLogger(__name__)


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for Reg.ru DNS

    This Authenticator uses the Reg.ru DNS API to fulfill a dns-01 challenge.
    """

    description = 'Obtain certificates using a DNS TXT record (if you are using Reg.ru for DNS).'

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add):  # pylint: disable=arguments-differ
        super(Authenticator, cls).add_parser_arguments(add, default_propagation_seconds=180)
        add('credentials', help='Path to Reg.ru credentials INI file', default='/etc/letsencrypt/regru.ini')

    def more_info(self):  # pylint: disable=missing-docstring,no-self-use
        return 'This plugin configures a DNS TXT record to respond to a dns-01 challenge using ' + \
               'the Reg.ru API.'

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'path to Reg.ru credentials INI file',
            {
                'username': 'Username of the Reg.ru account.',
                'password': 'Password of the Reg.ru account.',
            }
        )

    def _perform(self, domain, validation_name, validation):
        self._get_regru_client().add_txt_record(validation_name, validation)

    def _cleanup(self, domain, validation_name, validation):
        self._get_regru_client().del_txt_record(validation_name, validation)

    def _get_regru_client(self):
        return _RegRuClient(self.credentials.conf('username'), self.credentials.conf('password'))


class _RegRuClient(object):
    """
    Encapsulates all communication with the Reg.ru
    """

    def __init__(self, username, password):
        self.http = _HttpClient()
        self.options = {
            'username': username,
            'password': password,
            'io_encoding': 'utf8',
            'show_input_params': 1,
            'output_format': 'json',
            'input_format': 'json',
        }

    def add_txt_record(self, record_name, record_content):
        """
        Add a TXT record using the supplied information.
        :param str record_name: The record name (typically beginning with '_acme-challenge.').
        :param str record_content: The record content (typically the challenge validation).
        :raises certbot.errors.PluginError: if an error occurs communicating with the Reg.ru API
        """

        data = self._create_params(record_name, {'text': record_content})

        try:
            logger.debug(f'Attempting to add record: {data}')
            response = self.http.send('https://api.reg.ru/api/regru2/zone/add_txt', data)
        except requests.exceptions.RequestException as e:
            logger.error(f'Encountered error adding TXT record: {e}')
            raise errors.PluginError(f'Error communicating with the Reg.ru API: {e}')

        if not self._is_success_response(response):
            logger.error(f'Encountered error adding TXT record: {response}')
            raise errors.PluginError(f'Error communicating with the Reg.ru API: {response}')

        logger.debug('Successfully added TXT record')

    def del_txt_record(self, record_name, record_content):
        """
        Delete a TXT record using the supplied information.
        Note that both the record's name and content are used to ensure that similar records
        created concurrently (e.g., due to concurrent invocations of this plugin) are not deleted.
        Failures are logged, but not raised.
        :param str record_name: The record name (typically beginning with '_acme-challenge.').
        :param str record_content: The record content (typically the challenge validation).
        """

        data = self._create_params(record_name, {
            'record_type': 'TXT',
            'content': record_content
        })

        try:
            logger.debug(f'Attempting to delete record: {data}')
            response = self.http.send('https://api.reg.ru/api/regru2/zone/remove_record', data)
        except requests.exceptions.RequestException as e:
            logger.warning(f'Encountered error deleting TXT record: {e}')
            return

        if not self._is_success_response(response):
            logger.warning(f'Encountered error deleting TXT record: {response}')
            return

        logger.debug('Successfully deleted TXT record.')

    def _create_params(self, domain, input_data):
        """
        Creates POST parameters.
        :param str domain: Domain name
        :param dict input_data: Input data
        :returns: POST parameters
        :rtype: dict
        """
        pieces = domain.split('.')

        input_data['subdomain'] = '.'.join(pieces[:-2])
        input_data['domains'] = [{'dname': '.'.join(pieces[-2:])}]

        data = self.options.copy()
        data.update({'input_data': json.dumps(input_data)})

        return data

    def _is_success_response(self, response):
        """Safely check whether Reg.ru API response indicates success.

        Ensures each nested object exists and has the expected type before
        accessing, avoiding KeyError/IndexError/TypeError.
        """
        if not isinstance(response, dict):
            return False

        if response.get('result') != 'success':
            return False

        answer = response.get('answer')
        if not isinstance(answer, dict):
            return False

        domains = answer.get('domains')
        if not isinstance(domains, list) or not domains:
            return False

        first_domain = domains[0]
        if not isinstance(first_domain, dict):
            return False

        return first_domain.get('result') == 'success'


class _HttpClient(object):
    """
    Encapsulates HTTP requests
    """

    def send(self, url, data):
        """
        Sends a POST request.
        :param str url: URL for the new :class:`Request` object.
        :param dict data: Dictionary (will be form-encoded) to send in the body of the :class:`Request`.
        :raises requests.exceptions.RequestException: if an error occurs communicating with HTTP server
        """

        response = requests.post(url, data=data)
        response.raise_for_status()

        return response.json()
