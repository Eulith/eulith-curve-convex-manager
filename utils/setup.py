import os.path
import secrets
import sys

if __name__ == '__main__':
    secret_material = secrets.token_hex(32)
    private_key = f'0x{secret_material}'

    args = sys.argv
    if len(args) != 2:
        print('cannot proceed without the refresh token')
        exit(1)

    refresh_token = args[1]

    if not os.path.isfile('utils/settings.py'):
        with open('utils/settings.py', 'w+') as file:
            file.write(f'PRIVATE_KEY = "{private_key}"\n')
            file.write(f'EULITH_REFRESH_TOKEN = "{refresh_token}"\n')
    else:
        print('utils/settings.py file already exists. not going to overwrite with a new key.')
