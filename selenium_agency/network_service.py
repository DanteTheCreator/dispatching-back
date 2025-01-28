import requests

class NetworkService:
    API_BASE_URL = ""
    VERIFY = True
    USER_AGENT = ''

    @staticmethod
    def handle_response(response):
        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            response_data = None

        if not response.ok:
            error_data = response_data if response_data else {'detail': 'Something went wrong!'}
            raise Exception(error_data.get('detail', 'Something went wrong!'))
        
        return response_data

    @classmethod
    def get_default_headers(cls):
        return {
            'Content-Type': 'application/json',
            'User-Agent': cls.USER_AGENT
        }

    @staticmethod
    def build_query_string(params):
        return '?' + '&'.join([f"{param['key']}={param['value']}" for param in params])

    @classmethod
    def get(cls, url, params=None, headers=None):
        if params is None:
            params = []
        if headers is None:
            headers = {}
        default_headers = cls.get_default_headers()
        query_string = cls.build_query_string(params) if params else ''
        response = requests.get(f"{cls.API_BASE_URL}{url}{query_string}", headers={**default_headers, **headers}, verify=cls.VERIFY)
        return cls.handle_response(response)

    @classmethod
    def post(cls, url, data, params=None, headers=None):
        if params is None:
            params = []
        if headers is None:
            headers = {}
        default_headers = cls.get_default_headers()
        query_string = cls.build_query_string(params) if params else ''
        response = requests.post(f"{cls.API_BASE_URL}{url}{query_string}", json=data, headers={**default_headers, **headers}, verify=cls.VERIFY)
        return cls.handle_response(response)

    @classmethod
    def put(cls, url, data, params=None, headers=None):
        if params is None:
            params = []
        if headers is None:
            headers = {}
        default_headers = cls.get_default_headers()
        query_string = cls.build_query_string(params) if params else ''
        response = requests.put(f"{cls.API_BASE_URL}{url}{query_string}", json=data, headers={**default_headers, **headers}, verify=cls.VERIFY)
        return cls.handle_response(response)

    @classmethod
    def patch(cls, url, data, params=None, headers=None):
        if params is None:
            params = []
        if headers is None:
            headers = {}
        default_headers = cls.get_default_headers()
        query_string = cls.build_query_string(params) if params else ''
        response = requests.patch(f"{cls.API_BASE_URL}{url}{query_string}", json=data, headers={**default_headers, **headers}, verify=cls.VERIFY)
        return cls.handle_response(response)

    @classmethod
    def delete(cls, url, data, params=None, headers=None):
        if params is None:
            params = []
        if headers is None:
            headers = {}
        default_headers = cls.get_default_headers()
        query_string = cls.build_query_string(params) if params else ''
        response = requests.delete(f"{cls.API_BASE_URL}{url}{query_string}", json=data, headers={**default_headers, **headers}, verify=cls.VERIFY)
        return cls.handle_response(response)