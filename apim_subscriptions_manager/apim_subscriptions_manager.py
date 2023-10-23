import logging

logger = logging.getLogger("apim_subscriptions_manager")
logger.setLevel(logging.DEBUG)

import json
import requests
import datetime

from typing import Dict, Any


class APIMUserAlreadyExistsError(Exception):
    pass


class APIMUserCreationError(Exception):
    pass


class ApimSubscriptionsManager:
    _tenant_id: str = None
    _client_id: str = None
    _client_secret: str = None
    _apim_subscription_id: str = None
    _apim_rg_name: str = None
    _apim_name: str = None
    _api_token: str = None
    _api_token_expiry: datetime.datetime = None

    def __init__(self, tenant_id: str,
                 client_id: str,
                 client_secret,
                 apim_subscription_id: str,
                 apim_rg_name: str,
                 apim_name: str):

        if not tenant_id:
            raise ValueError("tenant_id cannot be empty")
        if not client_id:
            raise ValueError("client_id cannot be empty")
        if not client_secret:
            raise ValueError("client_secret cannot be empty")
        if not apim_subscription_id:
            raise ValueError("apim_subscription_id cannot be empty")
        if not apim_rg_name:
            raise ValueError("apim_rg_name cannot be empty")
        if not apim_name:
            raise ValueError("apim_name cannot be empty")

        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._apim_subscription_id = apim_subscription_id
        self._apim_rg_name = apim_rg_name
        self._apim_name = apim_name

    def _get_api_token(self):
        """

        :return:
        """
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

    def create_user_on_apim(self, user_id: str, email: str, first_name: str, last_name: str,
                            group_name: str = None) -> Dict[str, Any]:
        """

        :param user_id:
        :param email:
        :param first_name:
        :param last_name:
        :param group_name:
        :return:
        """

        if not user_id:
            raise ValueError("user_id cannot be empty")
        if not email:
            raise ValueError("email cannot be empty")
        if not first_name:
            raise ValueError("first_name cannot be empty")
        if not last_name:
            raise ValueError("last_name cannot be empty")

        url = f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/{self._apim_rg_name}/providers/Microsoft.ApiManagement/service/{self._apim_name}/users/{user_id}?api-version=2022-08-01"

        headers = {
            "Authorization": f"Bearer {self._get_api_token()}",
            "Content-Type": "application/json",
        }

        body = json.dumps({
            "properties": {
                "email": email,
                "firstName": first_name,
                "lastName": last_name
            }
        })

        response = requests.put(url, headers=headers, data=body)

        if response.status_code == 200:
            raise APIMUserAlreadyExistsError(
                f"User with id {user_id} already exists. Status code: {response.status_code}, Response: {response.text}")
        elif response.status_code == 201:
            logging.info(f"User with id {user_id} created successfully")
            if group_name:
                url_for_adding_user_to_group = f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/{self._apim_rg_name}/providers/Microsoft.ApiManagement/service/{self._apim_name}/groups/{group_name}/users/{user_id}?api-version=2022-08-01"
                response_for_adding_user_to_group = requests.put(url_for_adding_user_to_group, headers=headers)
                if response_for_adding_user_to_group.status_code in [200, 201]:
                    logging.info(f"User with id {user_id} added to group {group_name} successfully")
                else:
                    raise APIMUserCreationError(
                        f"Failed to add user with id {user_id} to group {group_name}. Status code: {response_for_adding_user_to_group.status_code}, Response: {response_for_adding_user_to_group.text}")
            return response.json()
        else:
            raise APIMUserCreationError(
                f"Failed to create user. Status code: {response.status_code}, Response: {response.text}")
