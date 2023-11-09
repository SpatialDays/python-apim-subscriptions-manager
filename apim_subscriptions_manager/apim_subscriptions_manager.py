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


class APIMUserNotFoundError(Exception):
    pass


class APIMSubscriptionAlreadyExistsError(Exception):
    pass


class APIMSubscriptionCreationError(Exception):
    pass


class APIMSubscriptionNotFoundError(Exception):
    pass


class APIMSubscriptionKeyRefreshError(Exception):
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

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Return auth headers required for interacting with APIM

        :return: Auth headers
        """
        headers = {
            "Authorization": f"Bearer {self._get_api_token()}",
            "Content-Type": "application/json",
        }
        return headers

    def create_user_on_apim(self, user_id: str, email: str, first_name: str, last_name: str,
                            group_name: str = None) -> Dict[str, Any]:
        """
        Create a user on APIM

        :param user_id: Unique identifier for the user
        :param email: Email address of the user
        :param first_name: First name of the user
        :param last_name: Last name of the user
        :param group_name: Name of the group to which the user should be added
        :return: Details of the user created on APIM

         Examples:
        >>> print(create_user_on_apim("123-unique-id-for-subscription-123", "test.user@spatialdays.com", "test", "user"))
        {
           "id":"<redacted>",
           "type":"Microsoft.ApiManagement/service/users",
           "name":"123-unique-id-for-subscription-123",
           "properties":{
              "firstName":"test",
              "lastName":"user",
              "email":"test.user@spatialdays.com",
              "state":"active",
              "registrationDate":"2023-06-01T09:33:15.997Z",
              "note":"None",
              "groups":[
                 {
                    "id":"<redacted>",
                    "name":"Developers",
                    "description":"Developers is a built-in group. Its membership is managed by the system. Signed-in users fall into this group.",
                    "builtIn":true,
                    "type":"system",
                    "externalId":"None"
                 }
              ],
              "identities":[
                 {
                    "provider":"Basic",
                    "id":"test.user@spatialdays.com"
                 }
              ]
           }
        }
        """

        if not user_id:
            raise ValueError("user_id cannot be empty")
        if not email:
            raise ValueError("email cannot be empty")
        if not first_name:
            raise ValueError("first_name cannot be empty")
        if not last_name:
            raise ValueError("last_name cannot be empty")

        url = (f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/"
               f"{self._apim_rg_name}/providers/Microsoft.ApiManagement/service/{self._apim_name}/users/{user_id}"
               f"?api-version=2022-08-01")

        headers = self._get_auth_headers()

        body = json.dumps({
            "properties": {
                "email": email,
                "firstName": first_name,
                "lastName": last_name
            }
        })

        response = requests.put(url, headers=headers, data=body)

        if response.status_code == 200:
            logging.error(f"User with id {user_id} already exists")
            raise APIMUserAlreadyExistsError(
                f"User with id {user_id} already exists. Status code: {response.status_code}, \
                Response: {response.text}")
        elif response.status_code == 201:
            logging.debug(f"User with id {user_id} created successfully")
            if group_name:
                url_for_adding_user_to_group = (f"https://management.azure.com/subscriptions/"
                                                f"{self._apim_subscription_id}/resourceGroups/"
                                                f"{self._apim_rg_name}/providers/Microsoft.ApiManagement/service/"
                                                f"{self._apim_name}/groups/{group_name}/users/{user_id}"
                                                f"?api-version=2022-08-01")
                response_for_adding_user_to_group = requests.put(url_for_adding_user_to_group, headers=headers)
                if response_for_adding_user_to_group.status_code in [200, 201]:
                    logging.debug(f"User with id {user_id} added to group {group_name} successfully")
                else:
                    raise APIMUserCreationError(
                        f"Failed to add user with id {user_id} to group {group_name}. Status code: \
                        {response_for_adding_user_to_group.status_code},\
                         Response: {response_for_adding_user_to_group.text}")
            return response.json()
        else:
            raise APIMUserCreationError(
                f"Failed to create user. Status code: {response.status_code}, Response: {response.text}")

    def get_user_from_apim(self, user_id: str) -> Dict[str, Any]:
        """
        Gets the user details from APIM

        :param user_id: The unique identifier for the user
        :return: Details of the user from APIM

        Examples:
        >>> print(get_user_from_apim("123-unique-id-for-subscription-123"))
        {
            'id': '/subscriptions/<redacted>/resourceGroups/<redacted>/providers/Microsoft.ApiManagement/service/<redacted>/users/123-unique-id-for-subscription-123',
            'type': 'Microsoft.ApiManagement/service/users',
            'name': '123-unique-id-for-subscription-123',
            'properties': {
                'firstName': 'test',
                'lastName': 'user',
                'email': 'test.user@spatialdays.com',
                'state': 'active',
                'registrationDate': '2023-06-01T09:33:15.997Z',
                'note': None,
                'identities': [{
                    'provider': 'Basic',
                    'id': 'test.user@spatialdays.com'
                }]
            }
        }
        """
        url = (f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/"
               f"{self._apim_rg_name}/providers/Microsoft.ApiManagement/service/{self._apim_name}/users/"
               f"{user_id}?api-version=2022-08-01")

        headers = self._get_auth_headers()

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise APIMUserNotFoundError(
                f"User with id {user_id} not found. Status code: {response.status_code}, Response: {response.text}")

    def delete_user_from_apim(self, user_id: str) -> str:
        """
        Deletes a user from APIM

        :param user_id: The unique identifier of the user to be deleted
        :return: The unique identifier of the user deleted
        Examples:
            >>> print(delete_user_from_apim("123-unique-id-for-subscription-123"))
            123-unique-id-for-subscription-123
        """

        url = (f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/"
               f"{self._apim_rg_name}/providers/Microsoft.ApiManagement/service/{self._apim_name}/users/{user_id}"
               f"?api-version=2022-08-01")

        headers = self._get_auth_headers()

        response = requests.delete(url, headers=headers)

        if response.status_code == 200:
            return user_id
        elif response.status_code == 204:
            raise APIMUserNotFoundError(
                f"User with id {user_id} not found or couldn't be deleted. Status code: {response.status_code}, Response: {response.text}")
        else:
            raise APIMUserNotFoundError(
                f"User with id {user_id} not found or couldn't be deleted. Status code: {response.status_code}, Response: {response.text}")

    def make_subscription_for_user_on_all_apis(self, user_id: str) -> Dict[str, Any]:
        """
        Makes a subscription for a user on all APIs

        :param user_id: The unique identifier of the user
        :return: Details of the subscription created

        Examples:
            >>> print(make_subscription_for_user_on_all_apis("123-unique-id-for-subscription-123"))
            {
                'id': '/subscriptions/<redacted>/resourceGroups/<redacted>/providers/Microsoft.ApiManagement/service/<redacted>/subscriptions/123-unique-id-for-subscription-123',
                'type': 'Microsoft.ApiManagement/service/subscriptions',
                'name': '123-unique-id-for-subscription-123',
                'properties': {
                    'ownerId': '/subscriptions/<redacted>/resourceGroups/<redacted>/providers/Microsoft.ApiManagement/service/<redacted>/users/123-unique-id-for-subscription-123',
                    'user': {
                        'id': '/subscriptions/<redacted>/resourceGroups/<redacted>/providers/Microsoft.ApiManagement/service/<redacted>/users/123-unique-id-for-subscription-123',
                        'firstName': 'test',
                        'lastName': 'user',
                        'email': 'test.user@spatialdays.com',
                        'state': 'active',
                        'registrationDate': '2023-06-01T09:33:15.997Z',
                        'note': None,
                        'groups': [],
                        'identities': []
                    },
                    'scope': '/subscriptions/<redacted>/resourceGroups/<redacted>/providers/Microsoft.ApiManagement/service/<redacted>/apis',
                    'displayName': '123-unique-id-for-subscription-123',
                    'state': 'active',
                    'createdDate': '2023-06-01T09:37:51.0432183Z',
                    'startDate': '2023-06-01T00:00:00Z',
                    'expirationDate': None,
                    'endDate': None,
                    'notificationDate': None,
                    'primaryKey': '<redacted>',
                    'secondaryKey': '<redacted>',
                    'stateComment': None,
                    'allowTracing': False
                }
            }
        """
        url = (f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/"
               f"{self._apim_rg_name}/providers/Microsoft.ApiManagement/service/{self._apim_name}"
               f"/subscriptions/{user_id}"
               f"?api-version=2022-08-01")

        headers = {
            "Authorization": f"Bearer {self._get_api_token()}",
            "Content-Type": "application/json",
        }

        body = json.dumps({
            "properties": {
                "scope": "/apis",
                "displayName": user_id,
                "state": "active",
                "ownerId": f"/users/{user_id}",
            }
        })

        response = requests.put(url, headers=headers, data=body)

        if response.status_code == 201:
            return response.json()
        elif response.status_code == 200:
            raise APIMSubscriptionAlreadyExistsError(
                f"Subscription for user with id {user_id} already exists. Status code: {response.status_code},"
                f" Response: {response.text}")
        else:
            raise APIMSubscriptionCreationError(
                f"Failed to create subscription. Status code: {response.status_code}, Response: {response.text}")

    def get_subscription_for_user(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieves a subscription for a user from the API Management (APIM) service.

        :param user_id: The unique identifier of the user for whom the subscription is to be retrieved.
        :return:  dictionary containing the details of the user's subscription. This includes the subscription ID, type,
            name, associated properties such as owner ID, scope, display name, state, creation date, start date, expiration date,
            end date, notification date, state comment and whether tracing is allowed.

        Examples:
            >>> print(get_subscription_for_user("123-unique-id-for-subscription-123"))
            {
                'id': '/subscriptions/<redacted>/resourceGroups/<redacted>/providers/Microsoft.ApiManagement/service/<redacted>/subscriptions/123-unique-id-for-subscription-123',
                'type': 'Microsoft.ApiManagement/service/subscriptions',
                'name': '123-unique-id-for-subscription-123',
                'properties': {
                    'ownerId': '/subscriptions/<redacted>/resourceGroups/<redacted>/providers/Microsoft.ApiManagement/service/<redacted>/users/123-unique-id-for-subscription-123',
                    'scope': '/subscriptions/<redacted>/resourceGroups/<redacted>/providers/Microsoft.ApiManagement/service/<redacted>/apis',
                    'displayName': '123-unique-id-for-subscription-123',
                    'state': 'active',
                    'createdDate': '2023-06-01T09:37:51.043Z',
                    'startDate': '2023-06-01T00:00:00Z',
                    'expirationDate': None,
                    'endDate': None,
                    'notificationDate': None,
                    'stateComment': None,
                    'allowTracing': False
                }
            }
        """

        url = (f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/"
               f"{self._apim_rg_name}/providers/Microsoft.ApiManagement/service/{self._apim_name}"
               f"/subscriptions/{user_id}"
               f"?api-version=2022-08-01")

        headers = self._get_auth_headers()

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise APIMSubscriptionNotFoundError(
                f"Subscription for user with id {user_id} not found. Status code: {response.status_code},"
                f" Response: {response.text}")

    def get_subscription_secrets_for_user(self, user_id: str) -> Dict[str, str]:
        """
        Retrieves the primary and secondary keys for a user's subscription from the API Management (APIM) service.

        :param user_id: The unique identifier of the user for whom the subscription keys are to be retrieved.
        :return: dictionary containing the primary and secondary keys for the user's subscription.

        Examples:
            >>> print(get_subscription_secrets_for_user("123-unique-id-for-subscription-123"))
            {
                'primaryKey': '<redacted>',
                'secondaryKey': '<redacted>'
            }
        """

        url = (f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/"
               f"{self._apim_rg_name}/providers/Microsoft.ApiManagement/service/{self._apim_name}/"
               f"subscriptions/{user_id}/listSecrets"
               f"?api-version=2022-08-01")

        headers = self._get_auth_headers()

        response = requests.post(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise APIMSubscriptionNotFoundError(
                f"Subscription for user with id {user_id} not found. Status code: {response.status_code}, "
                f"Response: {response.text}")

    def delete_subscription_for_user(self, user_id: str) -> str:
        """
        Deletes a subscription for a user in the API Management (APIM) service.

        :param user_id: The unique identifier of the user for whom the subscription is to be deleted.

        :return: The unique identifier of the user for whom the subscription was deleted.
        Examples:
            >>> print(delete_subscription_for_user("123-unique-id-for-subscription-123"))
            '123-unique-id-for-subscription-123'
        """

        url = (f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/"
               f"{self._apim_rg_name}/providers/Microsoft.ApiManagement/service/{self._apim_name}/subscriptions"
               f"/{user_id}?"
               f"api-version=2022-08-01")

        headers = self._get_auth_headers()

        response = requests.delete(url, headers=headers)

        if response.status_code == 200:
            return user_id
        elif response.status_code == 204:
            raise APIMSubscriptionNotFoundError(
                f"Subscription for user with id {user_id} not found or couldn't be deleted. Status code:"
                f" {response.status_code}, Response: {response.text}")
        else:
            raise APIMSubscriptionNotFoundError(
                f"Subscription for user with id {user_id} not found or couldn't be deleted. Status code:"
                f" {response.status_code}, Response: {response.text}")

    def regenerate_subscription_for_user(self, user_id: str) -> str:
        """
        Regenerates the subscription keys for a user in the API Management (APIM) service.

        :param user_id: The unique identifier of the user for whom the subscription keys are to be regenerated.

        :return: The unique identifier of the user for whom the subscription keys were regenerated.
        Examples:
            >>> print(regenerate_subscription_for_user("123-unique-id-for-subscription-123"))
            '123-unique-id-for-subscription-123'
        """

        urls = [
            (
                f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/"
                f"{self._apim_rg_name}/"
                f"providers/Microsoft.ApiManagement/service/{self._apim_name}/subscriptions/{user_id}/"
                f"regeneratePrimaryKey?api-version=2022-08-01"),
            (
                f"https://management.azure.com/subscriptions/{self._apim_subscription_id}/resourceGroups/"
                f"{self._apim_rg_name}/"
                f"providers/Microsoft.ApiManagement/service/{self._apim_name}/subscriptions/{user_id}/"
                f"regenerateSecondaryKey?api-version=2022-08-01")
        ]

        logging.debug(f"Urls are {urls}")
        headers = self._get_auth_headers()
        responses = []
        for url in urls:
            response = requests.post(url, headers=headers)
            responses.append(response)

        if all(response.status_code == 204 for response in responses):
            return user_id
        else:
            raise APIMSubscriptionKeyRefreshError(
                f"Failed to refresh subscription keys for user with id {user_id}. "
                f"Status codes: {[response.status_code for response in responses]}, "
                f"Responses: {[response.text for response in responses]}")
