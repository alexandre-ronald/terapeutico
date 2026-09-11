import logging
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from ldap3 import ALL, SIMPLE, Connection, Server
from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError


logger = logging.getLogger(__name__)


def _criar_servidor_ldap():
    """Cria o servidor LDAP a partir de uma URI ou de um hostname."""
    endereco = settings.AUTH_LDAP_SERVER_URI.strip()
    if not endereco:
        raise ImproperlyConfigured("AUTH_LDAP_SERVER_URI não foi configurado.")

    uri = endereco if "://" in endereco else f"ldap://{endereco}"
    parsed = urlparse(uri)

    if not parsed.hostname or parsed.scheme not in {"ldap", "ldaps"}:
        raise ImproperlyConfigured(
            "AUTH_LDAP_SERVER_URI deve usar o formato "
            "ldap://servidor:389 ou ldaps://servidor:636."
        )

    use_ssl = parsed.scheme == "ldaps"
    port = parsed.port or (636 if use_ssl else 389)

    return Server(
        parsed.hostname,
        port=port,
        use_ssl=use_ssl,
        get_info=ALL,
    )


def autenticar_usuario_ldap(username, password):
    """
    Autentica no Active Directory com o mesmo bind SIMPLE usado pelo sistema legado.

    Retorna True quando o bind é bem-sucedido e False para credenciais
    inválidas ou indisponibilidade do servidor.
    """
    if not username or not password:
        return False

    server = _criar_servidor_ldap()
    usuario_ad = f"{settings.AUTH_LDAP_DOMAIN}\\{username}"

    try:
        conn = Connection(
            server,
            user=usuario_ad,
            password=password,
            authentication=SIMPLE,
            auto_bind=True,
            auto_referrals=False,
        )
        conn.unbind()
        return True
    except LDAPBindError:
        return False
    except LDAPSocketOpenError:
        logger.exception("Não foi possível estabelecer conexão com o servidor LDAP.")
        return False
