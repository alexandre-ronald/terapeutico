from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.shortcuts import redirect


def redirect_to_login(request):
    return redirect('usuarios:login')

urlpatterns = [
    path('', redirect_to_login, name='home'),  # Redireciona a URL raiz para o login
    path('admin/', admin.site.urls),
    path('usuarios/', include('usuarios.urls')),
    path('centrocirurgico/', include('centrocirurgico.urls')),
    path('upme/', include('upme.urls')),
    path('opme/', include('opme.urls')),
    path('uhh/', include('uhh.urls')),
]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)