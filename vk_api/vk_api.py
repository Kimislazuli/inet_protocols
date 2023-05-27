from argparse import ArgumentParser

import requests
from jproperties import Properties

BASE_URL = 'https://api.vk.com/method/'
API_VER = '5.131'


class Args:
    """
    Args parser to extract args from command line.
    """

    def __init__(self):
        self.user_id = self._parse_args()

    @staticmethod
    def _parse_args() -> str:
        parser = ArgumentParser(description='VK API friends parser')

        parser.add_argument('user_id', type=str, help='user id to parse')

        args = parser.parse_args()

        return args.user_id


def request_maker(method: str, params: str, access_token: str) -> str:
    return BASE_URL + method + '?' + params + '&access_token=' + \
           access_token + '&v=' + API_VER


def get_user_id(target_user: str) -> int:

    with requests.get(request_maker('users.get', 'user_ids=' + target_user, access_token)) as response:
        data = response.json()
        if 'response' in data:
            return data['response'][0]['id']


def get_user_friends(target_user: str, access_token: str) -> set[str]:
    user_id = get_user_id(target_user)
    friends_set = set()
    with requests.get(request_maker(
            'friends.get',
            'user_id=' + str(user_id) + '&fields=first_name,last_name',
            access_token
    )) as response:
        data = response.json()
        if 'response' in data:
            friends = data['response']['items']
            for friend in friends:
                friend_name = friend['first_name'] + ' ' + friend['last_name']
                friends_set.add(friend_name)
    return friends_set


if __name__ == '__main__':
    args = Args()

    configs = Properties()
    with open('token.properties', 'rb') as config_file:
        configs.load(config_file)
    access_token = configs.get('access_token').data
    user_id = configs.get('user_id').data

    friends = get_user_friends(args.user_id, access_token)

    for friend in friends:
        print(friend)
