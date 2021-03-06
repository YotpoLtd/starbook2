from env import *
from flask import request, jsonify
from verify import verify_email_from_request, verify_admin, get_role


class Api:
    def __init__(self, utils):
        self.utils = utils

    def add_person(self):
        es = self.utils.es
        not_allow = verify_admin()
        if not_allow is not None:
            return not_allow
        person = request.json
        missing_keys = [key for key in PERSON_REQUIRED_KEYS if key not in person]
        if any(missing_keys):
            return jsonify({'error': 'the following keys are missing', 'keys': missing_keys}), 400
        try:
            existing = es.search(PERSONS_INDEX, PERSONS_TYPE, {
                'query': {
                    'match': {
                        PERSON_UNIQUE_KEY: {
                            'query': person[PERSON_UNIQUE_KEY],
                            'type': 'phrase'
                        }
                    }
                }
            })
            id = [i for i in existing['hits']['hits'] if i['_source'][PERSON_UNIQUE_KEY] ==
                  person[PERSON_UNIQUE_KEY]][0]['_id']
        except:
            id = None
        res = es.index(PERSONS_INDEX, PERSONS_TYPE, person, id)
        return jsonify({'created': res['created']})

    def remove_person(self):
        es = self.utils.es
        not_allow = verify_admin()
        if not_allow is not None:
            return not_allow
        person = request.json
        try:
            existing = es.search(PERSONS_INDEX, PERSONS_TYPE, {
                'query': {
                    'match': {
                        PERSON_UNIQUE_KEY: {
                            'query': person[PERSON_UNIQUE_KEY],
                            'type': 'phrase'
                        }
                    }
                }
            })
            found = [i for i in existing['hits']['hits'] if i['_source'][PERSON_UNIQUE_KEY] ==
                     person[PERSON_UNIQUE_KEY]][0]
        except:
            return jsonify({'status': 'Not found'}), 404

        boss = found['_source'].get('boss', None)
        if not boss:
            return jsonify({'status': 'Cannot remove root'}), 400

        children = es.search(PERSONS_INDEX, PERSONS_TYPE, {
            'size': 1000,
            'query': {
                'match': {
                    'boss': {
                        'query': person[PERSON_UNIQUE_KEY],
                        'type': 'phrase'
                    }
                }
            }
        })['hits']['hits']

        for child in children:
            self.utils.update_person_with_json({PERSON_UNIQUE_KEY: child['_source'][PERSON_UNIQUE_KEY],
                                                'boss': boss})
        es.delete(PERSONS_INDEX, PERSONS_TYPE, found['_id'])
        return jsonify({'found': found, 'children': children})

    def update_person(self):
        not_allow = verify_email_from_request()
        if not_allow is not None:
            return not_allow
        person = request.json
        return self.utils.update_person_with_json(person)

    def query(self):
        query = request.json
        query_string = query['query']
        elastic_query = {
            'size': 1000,
            'query': {
                'simple_query_string': {
                    'query': query_string
                }},
            'highlight': {
                'fields': {
                    '*': {}
                },
                'require_field_match': False
            }}

        fields = query.get('fields')
        if fields:
            elastic_query['query']['simple_query_string']['fields'] = fields
            elastic_query['highlight']['require_field_match'] = True

        res = self.utils.es.search(PERSONS_INDEX, PERSONS_TYPE, elastic_query)
        return jsonify(res)

    def tree(self):
        res = self.utils.es.search(PERSONS_INDEX, PERSONS_TYPE, {'size': 1000})
        persons = {}
        for p in res['hits']['hits']:
            persons[p['_source'][PERSON_UNIQUE_KEY]] = p['_source']

        for p in persons.keys():
            current_person = persons[p]
            his_boss = persons.get(current_person['boss'])
            if his_boss and his_boss.get('_children'):
                his_boss['_children'].append(current_person)
            elif his_boss:
                his_boss['_children'] = [current_person]

        p = list(persons.keys())[0]
        while persons.get(persons[p]['boss']):
            p = persons[persons[p]['boss']][PERSON_UNIQUE_KEY]

        res = persons[p]
        return jsonify(res)

    def get_all(self):
        res = self.utils.es.search(PERSONS_INDEX, PERSONS_TYPE, {
            '_source': request.json.get('fields') or '*',
            'from': request.json.get('from') or 0,
            'size': request.json.get('size') or 0
        })
        return jsonify(res)

    @staticmethod
    def get_role():
        return get_role()
