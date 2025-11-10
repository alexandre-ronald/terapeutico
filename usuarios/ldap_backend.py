from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from ldap3 import Server, Connection, ALL, NTLM
from django.conf import settings
import logging

# Configurar logging para debug
logger = logging.getLogger(__name__)

UserModel = get_user_model()

class LDAPBackend(BaseBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            logger.warning("Username ou password não fornecidos.")
            request.ldap_auth_error = "Campos obrigatórios não fornecidos."
            return None

        # Configurações do LDAP
        server = Server(settings.AUTH_LDAP_SERVER_URI, get_info=ALL)
        user_dn = f"{settings.AUTH_LDAP_DOMAIN}\\{username}"  # Formato: ebserhnet\username

        try:
            # Conexão com autenticação NTLM
            logger.debug(f"Tentando autenticar usuário: {user_dn}")
            conn = Connection(
                server,
                user=user_dn,
                password=password,
                authentication=NTLM,
                auto_bind=True,
                auto_referrals=False
            )
            logger.debug(f"Resultado da conexão: {conn.result}")

            # Verificar se a autenticação foi bem-sucedida
            if conn.result['result'] != 0 or conn.result['description'] != 'success':
                logger.warning(f"Autenticação falhou para {user_dn}: {conn.result['message']}")
                request.ldap_auth_error = "Usuário ou senha inválidos."
                return None

            # Busca o usuário no Django
            try:
                user = UserModel.objects.get(username=username)
                print ('Usuario:',user)
                #user = User.objects.get(username=username)
                logger.debug(f"Usuário {username} encontrado no Django.")
            except UserModel.DoesNotExist:
                logger.debug(f"Usuário {username} não possui acesso ao sistema.")
                request.ldap_auth_error = f"Usuário {username} não possui acesso ao sistema."
                return None

        except Exception as e:
            logger.error(f"Erro de autenticação LDAP: {str(e)}")
            request.ldap_auth_error = "Usuário ou senha inválidos."
            return None
        finally:
            if 'conn' in locals():
                conn.unbind()

    def get_user(self, user_id):
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
