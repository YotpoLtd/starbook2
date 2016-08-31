import json

from oauth2client import client, crypt

from env import *
from flask import request, jsonify, Flask


class FlaskMethods:
    def __init__(self, api):
        self.app = Flask(__name__)
        app = self.app

        @app.route(APPLICATION_ROOT, methods=['GET', 'POST'])
        def all_routes():
            if request.method == 'OPTIONS':
                return ''

            action = (request.json and request.json.pop('action', None)) or (
                request.args and request.args.pop('action', None))
            if not action:
                return '<html><body><h1>Hi there!</h1></body></html>'

            if action == 'tree':
                return api.tree()
            elif action == 'query':
                return api.query()
            elif action == 'update_person':
                return api.update_person()
            elif action == 'add_person':
                return api.add_person()
            else:
                return '<html><body><h1>Unknown action</h1></body></html>', 404

        @app.after_request
        def after_request(response):
            allow_origin = '*' if DEBUG else ORIGIN
            response.headers.add('Access-Control-Allow-Origin', allow_origin)
            response.headers.add('Access-Control-Allow-Credentials', str(not DEBUG).lower())
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response

        @app.before_request
        def verify_token():
            if DEBUG or request.method == 'OPTIONS':
                return
            token = request.cookies.get('starbook-token') or (request.json and request.json.get('starbook-token'))
            if not token:
                return jsonify({'error': 'no token'}), 401
            try:
                idinfo = client.verify_id_token(token, CLIENT_ID)
                # If multiple clients access the backend server:
                if idinfo['aud'] not in CLIENT_IDS:
                    return jsonify({'error': 'Unrecognized client'}), 401
                if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    return jsonify({'error': 'Wrong issuer'}), 401
                if idinfo['hd'] != APPS_DOMAIN_NAME:
                    return jsonify({'error': 'Wrong hosted domain'}), 401
            except crypt.AppIdentityError as e:
                # Invalid token
                return jsonify({'error': 'Invalid token'}), 401

            outdated = False
            google_id_redis_key = 'google_id:{}'.format(idinfo['sub'])
            cached_google_info = api.cache.redis.get(google_id_redis_key)
            if cached_google_info:
                google_info = json.loads(cached_google_info.decode())
                if google_info['image'] != idinfo['picture'] or google_info[PERSON_UNIQUE_KEY] != idinfo['email']:
                    outdated = True
            else:
                outdated = True

            if outdated:
                api.utils.update_person_with_json(
                    {PERSON_UNIQUE_KEY: idinfo['email'], 'image': idinfo['picture'], 'google_id': idinfo['sub']})
                api.cache.redis.set(google_id_redis_key,
                                    json.dumps(
                                        {'image': idinfo['picture'], PERSON_UNIQUE_KEY: idinfo['email']}).encode(),
                                    ex=REDIS_EXPIRY)