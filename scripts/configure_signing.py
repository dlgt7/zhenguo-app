import argparse
import base64
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--clean', action='store_true')
parser.add_argument('--require-release', action='store_true')
parser.add_argument('--edition', choices=['hongguojian', 'zhenguojian'], default='hongguojian')
options = parser.parse_args()
properties_file = root / 'android' / 'key.properties'

if options.clean:
    properties_file.unlink(missing_ok=True)
    runner_temp = os.environ.get('RUNNER_TEMP')
    if runner_temp:
        cached = Path(runner_temp) / 'duanju-release.jks'
        cached.unlink(missing_ok=True)
    raise SystemExit(0)

suffixes = ['KEYSTORE_BASE64', 'KEYSTORE_PASSWORD', 'KEY_ALIAS', 'KEY_PASSWORD']
edition_prefix = 'ANDROID_' + options.edition.upper() + '_'
values = [os.environ.get(edition_prefix + suffix, '') for suffix in suffixes]
if options.edition == 'hongguojian' and not any(values):
    values = [os.environ.get('ANDROID_' + suffix, '') for suffix in suffixes]

keystore_base64, store_password, key_alias, key_password = values
inrepo_keystore = root / 'android' / (options.edition + '.jks')

if keystore_base64:
    runner_temp = os.environ.get('RUNNER_TEMP')
    if not runner_temp:
        raise SystemExit('KEYSTORE_BASE64 需要 RUNNER_TEMP；本机构建请改用仓库内 jks + android/key.properties。')
    try:
        data = base64.b64decode(''.join(keystore_base64.split()), validate=True)
    except ValueError:
        raise SystemExit(edition_prefix + 'KEYSTORE_BASE64 不是有效的 Base64。')
    if not data:
        raise SystemExit('Android 签名文件为空。')
    key_file = Path(runner_temp) / 'duanju-release.jks'
    key_file.write_bytes(data)
    key_file.chmod(0o600)
elif inrepo_keystore.exists():
    if not all([store_password, key_alias, key_password]):
        if options.require_release:
            missing = edition_prefix + '{KEYSTORE_PASSWORD, KEY_ALIAS, KEY_PASSWORD}'
            raise SystemExit('仓库内 ' + options.edition + '.jks 已存在，正式发布仍需配置 ' + missing + ' 三个密码 Secrets。')
        print('仓库内 ' + options.edition + '.jks 存在但未配置密码 Secrets：生成预览 APK；正式发布请配置三个密码 Secrets。')
        raise SystemExit(0)
    key_file = inrepo_keystore
else:
    if options.require_release:
        raise SystemExit('正式发布需要 ' + options.edition + '.jks 入库或配置 ' + edition_prefix + '* 固定签名 Secrets。')
    print('未配置签名：生成预览 APK；正式发布请把 ' + options.edition + '.jks 放入 android/ 或配置固定签名 Secrets。')
    raise SystemExit(0)


def escape(value):
    result = ''
    for character in value:
        if character in '\\:=#! ':
            result += '\\' + character
        elif character == '\n':
            result += '\\n'
        elif character == '\r':
            result += '\\r'
        elif character == '\t':
            result += '\\t'
        elif ord(character) > 126:
            encoded = character.encode('utf-16-be')
            result += ''.join('\\u' + encoded[i:i + 2].hex() for i in range(0, len(encoded), 2))
        else:
            result += character
    return result


properties = {'storeFile': key_file.as_posix(), 'storePassword': store_password,
              'keyAlias': key_alias, 'keyPassword': key_password}
properties_file.write_text(''.join(name + '=' + escape(value) + '\n'
                                for name, value in properties.items()), encoding='ascii')
properties_file.chmod(0o600)
print('已配置 ' + options.edition + ' 发布签名：' + str(key_file))
