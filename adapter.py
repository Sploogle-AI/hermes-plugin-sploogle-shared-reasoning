"""Delegate host/profile precedence to the installed Honcho provider.

This initial adapter requires an explicitly resolved endpoint and static credential.
It deliberately does not refresh OAuth or guess SDK environment defaults.
"""
import re
from .shared_reasoning import Connection


def resolve_connection(*, config_reader=None, module_importer=None):
    if config_reader is None:
        from hermes_cli.config import load_config_readonly
        config_reader = load_config_readonly
    if module_importer is None:
        from plugins.memory import import_provider_module
        module_importer = import_provider_module
    settings = config_reader()
    if (settings.get('memory', {}).get('provider') != 'honcho'
            or {'honcho', 'memory/honcho'} & set(settings.get('plugins', {}).get('disabled') or [])):
        raise ValueError('Honcho is not the active enabled provider')
    client_module = module_importer('honcho', 'client')
    cfg = client_module.HonchoClientConfig.from_global_config()
    if not cfg.enabled:
        raise ValueError('Honcho connection is disabled')
    return Connection(base_url=re.sub(r'/v\d+/*$', '', cfg.base_url or '').rstrip('/'),
                      workspace=cfg.workspace_id, human_peer=cfg.peer_name,
                      api_key=cfg.api_key or '', timeout=cfg.timeout or 60.0)
