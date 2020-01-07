import json
import jsonschema
import os
import requests

from .errors import DemandAPIError

REQUEST_BODY_SCHEMAS = [
    'create_project',
]

REQUEST_PATH_SCHEMAS = [
    'get_attributes',
    'get_event',
    'get_feasibility',
    'get_line_item',
    'get_line_item_detailed_report',
    'get_line_items',
    'get_project',
    'get_project_detailed_report',
]

REQUEST_QUERY_SCHEMAS = [
    'get_attributes',
    'get_countries',
    'get_events',
    'get_line_items',
    'get_projects',
    'get_survey_topics',
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
            raise DemandAPIError('All authentication data is required.')

        self._access_token = None
        self._refresh_token = None
        self.auth_base_url = '{}/auth/v1'.format(self.base_host)
        self.base_url = '{}/sample/v1'.format(self.base_host)

        self._load_schemas()

    def _load_schemas(self):
        # Load the compiled schemas for use in validation.
        self._request_body_schemas = {}
        for schema_type in REQUEST_BODY_SCHEMAS:
            schema_file = open('dynatademand/schemas/request/body/{}.json'.format(schema_type), 'r')
            self._request_body_schemas[schema_type] = json.load(schema_file)
            schema_file.close()
        self._request_path_schemas = {}
        for schema_type in REQUEST_PATH_SCHEMAS:
            schema_file = open('dynatademand/schemas/request/path/{}.json'.format(schema_type), 'r')
            self._request_path_schemas[schema_type] = json.load(schema_file)
            schema_file.close()
        self._request_query_schemas = {}
        for schema_type in REQUEST_QUERY_SCHEMAS:
            schema_file = open('dynatademand/schemas/request/query/{}.json'.format(schema_type), 'r')
            self._request_query_schemas[schema_type] = json.load(schema_file)
            schema_file.close()

    def _validate_object(self, object_type, schema_type, data):
        # jsonschema.validate will return none if there is no error,
        # otherwise it will raise its' own error with details on the failure.
        schema = ''
        if 'request_body' == object_type:
            schema = self._request_body_schemas[schema_type]
        elif 'request_path' == object_type:
            schema = self._request_path_schemas[schema_type]
        elif 'request_query' == object_type:
            schema = self._request_query_schemas[schema_type]
        jsonschema.validate(schema=schema, instance=data)

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
            raise DemandAPIError('Refreshing Access Token failed with status {} and error: {}'.format(
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
            raise DemandAPIError('Log out failed with status {} and error: {}'.format(
                logout_response.status_code, logout_response.content
            ))
        return logout_response.json()

    def get_attributes(self, country_code, language_code):
        self._validate_object('request_path', 'get_attributes', {'countryCode': country_code, 'languageCode': language_code})
        self._validate_object('request_query', 'get_attributes', {})
        return self._api_get('/attributes/{}/{}'.format(country_code, language_code))

    def get_countries(self):
        self._validate_object('request_query', 'get_countries', {})
        return self._api_get('/countries')

    def get_event(self, event_id):
        self._validate_object('request_path', 'get_event', {event_id})
        return self._api_get('/events/{}'.format(event_id))

    def get_events(self):
        self._validate_object('request_query', 'get_events', {})
        return self._api_get('/events')

    def create_project(self, project_data):
        # self._validate_object('request_body', 'create_project', project_data)
        response_data = self._api_post('/projects', project_data)
        if response_data.get('status').get('message') != 'success':
            raise DemandAPIError(
                'Could not create project. Demand API responded with: {}'.format(
                    response_data
                )
            )
        return response_data

    def get_project(self, project_id):
        self._validate_object('request_path', 'get_project', {project_id})
        return self._api_get('/projects/{}'.format(project_id))

    def get_projects(self):
        self._validate_object('request_query', 'get_projects', {})
        return self._api_get('/projects')

    def get_project_detailed_report(self, project_id):
        self._validate_object('request_path', 'get_project_detailed_report', {'extProjectId': str(project_id)})
        return self._api_get('/projects/{}/detailedReport'.format(project_id))

    def get_line_item(self, project_id, line_item_id):
        self._validate_object('request_path', 'get_line_item', {project_id, line_item_id})
        return self._api_get('/projects/{}/lineItems/{}'.format(project_id, line_item_id))

    def get_line_items(self, project_id):
        self._validate_object('request_path', 'get_line_items', project_id)
        self._validate_object('request_query', 'get_line_items', {})
        return self._api_get('/projects/{}/lineItems'.format(project_id))

    def get_line_item_detailed_report(self, project_id, line_item_id):
        self._validate_object('request_path', 'get_line_item_detailed_report', {project_id, line_item_id})
        return self._api_get('/projects/{}/lineItems/{}/detailedReport'.format(project_id, line_item_id))

    def get_feasibility(self, project_id):
        self._validate_object('request_path', 'get_feasibility', project_id)
        return self._api_get('/projects/{}/feasibility'.format(project_id))

    def get_survey_topics(self):
        self._validate_object('request_query', 'get_survey_topics', {})
        return self._api_get('/categories/surveyTopics')

    def get_sources(self):
        # the get sources endpoint has no request schemas
        return self._api_get('/sources')
