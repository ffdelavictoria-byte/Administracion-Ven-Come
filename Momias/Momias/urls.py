"""
URL configuration for Momias project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from Sistema_Momias.views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Ruta raíz: Mandamos el inicio directamente al Login
    path('', Login_View, name='login'), # Esta es la que reconoce el formulario 
    
    # Si prefieres mantener /login/ explícito, usa este name:
    path('login/', Login_View, name='login_page'), 
    path('nuevo_usuario/',  registrar_usuario, name='registrar_usuario'),
    path('main/', Main_Content, name='main'),
    path('logout/', Logout_view, name='logout'),
    path('usuarios/', Lista_Usuarios_View, name='lista_usuarios'),
    path('usuarios/borrar/<int:usuario_id>/', Borrar_Usuario_View, name='borrar_usuario'),
    path('emp/', Emp, name='empleados'),
    path('asistencia/', Asistencias_view, name='asistencias'),
    path('asistenciaff/', Asistencias_FF_view, name='asistenciasff'),
    path('nomina/', calcular_nomina_web, name='nomina'),
    path('gestionar-documentos/<int:emp_id>/', gestionar_documentos_ajax, name='gestionar_docs'),
    path('nomina/excel/', exportar_excel_nomina, name='exportar_excel'),
    path('nomina/pdf/', exportar_pdf_nomina, name='exportar_pdf'),
    path('reportes/', vista_reportes, name='reportes'),
    path('registro/', gestion_usuario_admin, name='registro_usuario'),
    path('cambiar-password/<int:user_id>/', gestion_usuario_admin, name='admin_cambiar_password'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)