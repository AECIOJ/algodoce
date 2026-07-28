from flask import url_for, request
from flask_login import current_user

from app.routes.app_defs import APP


def modulo_atual():
    if current_user.is_authenticated:
        return APP['system']
    return APP['site']


def url_do_item(item):
    if 'endpoint' in item:
        return url_for(item['endpoint'])
    return item.get('url', '#')


def item_ativo(item, path):
    href = url_do_item(item)
    return path.rstrip('/') == href.rstrip('/') or path.startswith(href.rstrip('/') + '/')


def menus_para_json():
    mod = modulo_atual()
    result = {}
    for label, item in mod['menus'].items():
        sub = item.get('submenus')
        if sub:
            result[label.lower()] = {
                'title': label,
                'items': [
                    {'label': sl, 'url': url_do_item(si), 'icon': si.get('icon', '')}
                    for sl, si in sub.items()
                ],
            }
    return result
