import logging

logger = logging.getLogger("apim_subscriptions_manager")
logger.setLevel(logging.DEBUG)

import json
import requests
import datetime

from typing import Dict, Any


class ApimSubscriptionsManager:
    _tenant_id: str = None
    _client_id: str = None
    _client_secret: str = None
    _api_token: str = None
    _api_token_expiry: datetime.datetime = None

    def __init__(self, tenant_id: str, client_id: str, client_secret):
        """

        :param tenant_id:
        :param client_id:
        :param client_secret:
        """
        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")
        if not client_id:
            raise ValueError("client_id cannot be empty")
        if not client_secret:
            raise ValueError("client_secret cannot be empty")
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret

    def _get_api_token(self):
        if self._api_token and self._api_token_expiry > datetime.datetime.now() - datetime.timedelta(minutes=5):
            logger.debug(f"Using cached token: {self._api_token}")
            return self._api_token

        logger.debug("Getting new token as cached token is expired or not set")
        url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "resource": "https://management.azure.com/",
        }
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        logger.debug(f"Response as json: {response.json()}")
        token_expires_on = datetime.datetime.fromtimestamp(int(response.json()["expires_on"]))
        logger.debug(f"Token expires on: {token_expires_on}")
        self._api_token = response.json()["access_token"]
        self._api_token_expiry = token_expires_on
        return self._api_token
