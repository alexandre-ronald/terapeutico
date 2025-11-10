from ldap3 import Server, Connection, ALL, core, NTLM

from django.conf import settings

def autenticar_usuario_ldap(username, password):
    """
    Autentica um usuário no servidor LDAP/AD usando NTLM.
    Retorna True se a autenticação for bem-sucedida, False caso contrário.
    """

    
    LDAP_SERVER = Server(settings.AUTH_LDAP_SERVER_URI, get_info=ALL)  # Substitua pelo endereço real
    DOMAIN = f"{settings.AUTH_LDAP_DOMAIN}\\{username}"                # Substitua pelo seu domínio real

    user_dn = f'{DOMAIN}\\{username}'  # Para AD, usa-se NTLM: DOMÍNIO\\usuário
    # Configurações do LDAP
    server = Server(settings.AUTH_LDAP_SERVER_URI, get_info=ALL)
    user_dn = f"{settings.AUTH_LDAP_DOMAIN}\\{username}"  # Formato: ebserhnet\username


    try:
       # server = Server(LDAP_SERVER, get_info=ALL)

        conn = Connection(
                server,
                user=user_dn,
                password=password,
                authentication='SIMPLE',
                auto_bind=True,
                auto_referrals=False
            )
        
        conn.unbind()
        return True
    except core.exceptions.LDAPBindError:
        return False
