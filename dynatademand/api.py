import json
import jsonschema
import os
import requests

from .errors import DemandAPIError

SCHEMAS = [
    "project_new",
]


class DemandAPIClient(object):
    def __init__(self, client_id=None, username=None, password=None, base_host=None):
        if client_id is not None:
            self.client_id = client_id
        else:
            self.client_id = os.getenv('DYNATA_DEMAND_CLIENT_ID', None)
        if username is not None:
            self.username = username
        else:
            self.username = os.getenv('DYNATA_DEMAND_USERNAME', None)
        if password is not None:
            self.password = password
        else:
            self.password = os.getenv('DYNATA_DEMAND_PASSWORD', None)
        if base_host is not None:
            self.base_host = base_host
        else:
            self.base_host = os.getenv('DYNATA_DEMAND_BASE_URL', default='https://api.researchnow.com')

        if None in [self.client_id, self.username, self.password]:
            raise DemandAPIError("All authentication data is required.")

        self._access_token = None
        self._refresh_token = None
        self.auth_base_url = '{}/auth/v1'.format(self.base_host)
        self.base_url = '{}/sample/v1'.format(self.base_host)

        self._load_schemas()

    def _load_schemas(self):
        # Load the compiled schemas for use in validation.
        self._schemas = {}
        for schema_type in SCHEMAS:
            schema_file = open('dynatademand/schemas/{}.json'.format(schema_type), 'r')
            self._schemas[schema_type] = json.load(schema_file)
            schema_file.close()

    def _validate_object(self, schema_type, data):
        # jsonschema.validate will return none if there is no error,
        # otherwise it will raise its' own error with details on the failure.
        jsonschema.validate(self._schemas[schema_type], data)

    def _check_authentication(self):
        # This doesn't check if the access token is valid, just that it exists.
        # The access_token is generated by calling the `authenticate` method.
        if self._access_token is None:
            raise DemandAPIError('The API instance must be authenticated before calling this method.')

    def _api_post(self, uri, payload):
        # Send an authenticated POST request to an API endpoint.
        self._check_authentication()
        url = '{}{}'.format(self.base_url, uri)
        request_headers = {
            'oauth_access_token': self._access_token,
            'Content-Type': "application/json",
        }
        response = requests.post(url=url, json=payload, headers=request_headers)
        if response.status_code > 399:
            raise DemandAPIError('Demand API request to {} failed with status {}. Response: {}'.format(
                url, response.status_code, response.content
            ))
        return response.json()

    def _api_get(self, uri, query_params=None):
        # Send an authenticated POST request to an API endpoint.
        self._check_authentication()
        url = '{}{}'.format(self.base_url, uri)
        request_headers = {
            'oauth_access_token': self._access_token,
            'Content-Type': "application/json",
        }
        response = requests.get(url=url, params=query_params, headers=request_headers)
        if response.status_code > 399:
            raise DemandAPIError('Demand API request to {} failed with status {}. Response: {}'.format(
                url, response.status_code, response.content
            ))
        return response.json()

    def authenticate(self):
        # Sends the authentication data to
        url = '{}/token/password'.format(self.auth_base_url)
        auth_response = requests.post(url, json={
            'clientId': self.client_id,
            'password': self.password,
            'username': self.username,
        })
        if auth_response.status_code > 399:
            raise DemandAPIError('Authentication failed with status {} and error: {}'.format(
                auth_response.status_code,
                auth_response.json())
            )
        response_data = auth_response.json()
        self._access_token = response_data.get('accessToken')
        self._refresh_token = response_data.get('refreshToken')
        return response_data

    def refresh_access_token(self):
        url = '{}/token/refresh'.format(self.auth_base_url)
        refresh_response = requests.post(url, json={
            'clientId': self.client_id,
            'refreshToken': self._refresh_token
        })
        if refresh_response.status_code != 200:
            raise DemandAPIError("Refreshing Access Token failed with status {} and error: {}".format(
                refresh_response.status_code, refresh_response.content
            ))
        response_data = refresh_response.json()
        self._access_token = response_data.get('accessToken')
        self._refresh_token = response_data.get('refreshToken')
        return response_data

    def logout(self):
        url = '{}/logout'.format(self.auth_base_url)
        logout_response = requests.post(url, json={
            'clientId': self.client_id,
            'refreshToken': self._refresh_token,
            'accessToken': self._access_token
        })
        if logout_response.status_code != 204:
            raise DemandAPIError("Log out failed with status {} and error: {}".format(
                logout_response.status_code, logout_response.content
            ))
        return logout_response.json()

    def get_event(self, event_id):
        return self._api_get('/events/{}'.format(event_id))

    def get_events(self):
        return self._api_get('/events')

    def create_project(self, project_data):
        # Creates a new project. Uses the "new project" schema.
        self._validate_object("project_new", project_data)
        response_data = self._api_post('/projects', project_data)
        if response_data.get('status').get('message') != 'success':
            raise DemandAPIError(
                "Could not create project. Demand API responded with: {}".format(
                    response_data
                )
            )
        return response_data

    def get_project(self, project_id):
        return self._api_get('/projects/{}'.format(project_id))

    def get_project_detailed_report(self, project_id):
        return self._api_get('/projects/{}/detailedReport'.format(project_id))

    def get_line_item(self, project_id, line_item_id):
        return self._api_get('/projects/{}/lineItems/{}'.format(project_id, line_item_id))

    def get_line_items(self, project_id):
        return self._api_get('/projects/{}/lineItems'.format(project_id))

    def get_line_item_detailed_report(self, project_id, line_item_id):
        return self._api_get('/projects/{}/lineItems/{}/detailedReport'.format(project_id, line_item_id))

    def get_feasibility(self, project_id):
        return self._api_get('/projects/{}/feasibility'.format(project_id))

    def get_sources(self):
        return self._api_get('/sources')
