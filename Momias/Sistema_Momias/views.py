from django.shortcuts import render, redirect, get_object_or_404
from .models import Perfil  # <--- ESTA ES VITAL
from .models import ConfigSueldo # Añade esto a tus imports
from datetime import datetime, date, timedelta
from django.db.models import Q, Value, CharField
from django.db.models.functions import Concat
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from Sistema_Momias.models import *
from datetime import date
from .models import Empleado, Asistencia  # Asegúrate de tener estos modelos
from datetime import datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
import json  # <--- IMPORTANTE: Agrega esto al inicio de tu archivo
from django.db.models import Q
from collections import Counter
import pandas as pd
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.contrib.auth.models import User
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime # Asegúrate de importar esto
import re
from django.db.models import Q
from collections import Counter
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import json



HORAS_POR_PUESTO = {
    "6 horas": 6, "9 horas": 9, "12 horas": 12, "6 hrs": 6, "9 hrs": 9
}

# Diccionarios de configuración (Basados en tu código original)
RANGOS_RETARDOS = {
    "09:06 - 09:10": 1, "09:11 - 09:20": 2, "09:21 - 09:30": 3, "09:31 - 09:40": 4, "09:41 - 09:50": 5, "09:51 - 10:00": 6, "10:00 - 10:10": 7, "10:11 - 10:20": 8, "10:21 - 10:30": 9, "10:31 - 10:40": 10,"10:41 - 10:50": 11,"10:51 - 11:00": 12,
    "15:06 - 15:10": 1, "15:11 - 15:20": 2, "15:21 - 15:30": 3, "15:31 - 15:40": 4, "15:41 - 15:50": 5, "15:51 - 16:00": 6, "16:00 - 16:10": 7, "16:11 - 16:20": 8, "16:21 - 16:30": 9, "16:31 - 16:40": 10, "16:41 - 16:50": 11, "16:51 - 17:00": 12,
    # ... puedes completar los rangos hasta el 6 como en tu script
}

def obtener_valor_retardo(entrada_str):
    """
    Extrae el número de un string tipo 'R1', 'R2' o '3'.
    Si el selector de Momias guarda 'R2', esto devuelve 2.
    """
    if not entrada_str: return 0
    try:
        # Si guardas 'R1', 'R2', quitamos la R y convertimos a int
        solo_numero = str(entrada_str).upper().replace('R', '').strip()
        return int(solo_numero)
    except ValueError:
        return 0

def calcular_descuento_retardos(puntos, sueldo_diario):
    """
    Implementación de tu escala:
    1 punto: 0
    2-3 puntos: 0.5 turnos
    4-5 puntos: 1.0 turno
    6-7 puntos: 1.5 turnos
    8-9 puntos: 2.0 turnos
    10+ puntos: 2.5 turnos
    """
    if puntos <= 1:
        factor = 0
    elif puntos <= 3:
        factor = 0.5
    elif puntos <= 5:
        factor = 1.0
    elif puntos <= 7:
        factor = 1.5
    elif puntos <= 9:
        factor = 2.0
    elif puntos <= 10:
        factor = 2.5
    elif puntos <= 11:
        factor = 2.5
    elif puntos <= 12:
        factor = 3.0
    else: # 10 o más
        factor = 3.5
        
    return round(factor * sueldo_diario, 2)

def Login_View(request):
    if request.user.is_authenticated and request.method == 'GET':
        logout(request) 
    
    if request.method == 'POST':
        usuario_input = request.POST.get('username')
        clave_input = request.POST.get('password')
        
        user = authenticate(request, username=usuario_input, password=clave_input)
        
        if user is not None:
            login(request, user)
            # CAMBIO VITAL: Usa redirect en lugar de render
            # Asegúrate de que 'main' sea el name que tienes en urls.py para Main_Content
            return redirect('main') 
        else:
            messages.error(request, "¡SANTO CIELO! Usuario o contraseña incorrectos.")
            
    return render(request, 'Login_View.html')

from django.http import HttpResponse # Asegúrate de tener esta importación arriba

@login_required(login_url='login')
def Main_Content(request):
    try:
        # 1. Intento de asegurar el perfil
        Perfil.objects.get_or_create(usuario=request.user)
        
        # 2. Intento de obtener usuarios
        todos_los_usuarios = User.objects.all().order_by('username')
        
        context = {
            'todos_los_usuarios': todos_los_usuarios,
        }
        
        # 3. Intento de renderizar el HTML
        return render(request, 'Main_Content.html', context)

    except Exception as e:
        # Si algo falla, el error aparecerá en texto plano en tu navegador
        import traceback
        error_detalle = traceback.format_exc()
        return HttpResponse(f"<h1>Error detectado en Main_Content</h1><pre>{error_detalle}</pre>")
    
def actualizar_permisos_masivo(request):
    if request.method == 'POST':
        usuarios = User.objects.all()
        for u in usuarios:
            # Los superusuarios no se tocan, siempre tienen poder total
            if u.is_superuser:
                continue
                
            perfil, created = Perfil.objects.get_or_create(usuario=u)
            
            # Leemos los checkboxes. Si el nombre existe en el POST, es True.
            # Los nombres coinciden con lo que pondremos en el HTML abajo
            perfil.can_ver_empleados = f'p_{u.id}_emp' in request.POST
            perfil.can_ver_asistencias = f'p_{u.id}_asi' in request.POST
            perfil.can_ver_nomina = f'p_{u.id}_nom' in request.POST
            perfil.can_ver_reportes = f'p_{u.id}_rep' in request.POST
            perfil.can_ver_sueldos = f'p_{u.id}_sue' in request.POST
            perfil.save()
            
        messages.success(request, "¡Permisos actualizados correctamente!")
        return redirect('main') # Cambia 'main' por el nombre de tu URL principal

def Logout_view(request):
    logout(request) # Esto borra la sesión del servidor y la cookie del navegador
    messages.success(request, "Sesión cerrada. ¡Vuelve pronto!")
    return redirect('login') # Te manda de regreso al login

def Emp(request):
    if request.method == 'POST':
        accion = request.POST.get('accion')
        id_emp = request.POST.get('empleado_id')

        try:
            # --- ACCIÓN: ELIMINAR, BAJA, ALTA (Se mantienen igual) ---
            if accion == 'eliminar' and id_emp:
                empleado = get_object_or_404(Empleado, id=id_emp)
                nombre_borrado = empleado.nombre
                empleado.delete()
                messages.success(request, f"¡KABOOM! {nombre_borrado} eliminado permanentemente.")

            elif accion == 'baja' and id_emp:
                empleado = get_object_or_404(Empleado, id=id_emp)
                empleado.estatus = 'Inactivo'
                if hasattr(empleado, 'fecha_baja'):
                    empleado.fecha_baja = date.today()
                empleado.save()
                messages.warning(request, f"¡ZAS! {empleado.nombre} ha sido dado de baja.")

            elif accion == 'alta' and id_emp:
                empleado = get_object_or_404(Empleado, id=id_emp)
                empleado.estatus = 'Activo'
                if hasattr(empleado, 'fecha_baja'):
                    empleado.fecha_baja = None 
                empleado.save()
                messages.success(request, f"¡BOOM! {empleado.nombre} ha regresado al servicio activo.")

            # --- ACCIÓN: GUARDAR / MODIFICAR (Aquí agregamos la fecha) ---
            elif accion == 'guardar':
                nombre = request.POST.get('nombre', '').upper()
                ap_paterno = request.POST.get('apellido_paterno', '').upper()
                ap_materno = request.POST.get('apellido_materno', '').upper()
                puesto = request.POST.get('puesto')
                sueldo_base = request.POST.get('sueldo_base')
                
                # --- CAPTURA DE FECHA DE INGRESO ---
                fecha_ingreso_str = request.POST.get('fecha_ingreso')
                # Django/HTML suelen enviar yyyy-mm-dd, pero si necesitas dd/mm/aaaa 
                # lo validamos aquí:
                fecha_ingreso = None
                if fecha_ingreso_str:
                    try:
                        # Si viene de un <input type="date"> es YYYY-MM-DD
                        fecha_ingreso = datetime.strptime(fecha_ingreso_str, '%Y-%m-%d').date()
                    except ValueError:
                        # Por si acaso viene en formato manual DD/MM/YYYY
                        fecha_ingreso = datetime.strptime(fecha_ingreso_str, '%d/%m/%Y').date()

                sueldo = float(sueldo_base) if sueldo_base else 0.0

                if id_emp: # MODIFICAR
                    emp = get_object_or_404(Empleado, id=id_emp)
                    emp.nombre = nombre
                    emp.apellido_paterno = ap_paterno
                    emp.apellido_materno = ap_materno
                    emp.puesto = puesto
                    emp.sueldo_base = sueldo
                    # Actualizamos la fecha de ingreso si se proporcionó
                    if fecha_ingreso:
                        emp.fecha_ingreso = fecha_ingreso
                    emp.save()
                    messages.success(request, "¡POW! Datos actualizados.")
                
                else: # CREAR NUEVO
                    ultimo = Empleado.objects.all().order_by('id').last()
                    nuevo_id = (ultimo.id + 1) if ultimo else 1
                    codigo_gen = f"EMP-{nuevo_id:05d}"
                    while Empleado.objects.filter(codigo_empleado=codigo_gen).exists():
                        nuevo_id += 1
                        codigo_gen = f"EMP-{nuevo_id:05d}"
                    
                    Empleado.objects.create(
                        codigo_empleado=codigo_gen,
                        nombre=nombre,
                        apellido_paterno=ap_paterno,
                        apellido_materno=ap_materno,
                        puesto=puesto,
                        sueldo_base=sueldo,
                        fecha_ingreso=fecha_ingreso, # <--- GUARDAMOS LA FECHA
                        estatus='Activo'
                    )
                    messages.success(request, f"¡CRASH! Empleado {codigo_gen} registrado.")

        except Exception as e:
            messages.error(request, f"¡RAYOS! Error: {e}")
        
        return redirect('main') 

    # --- LÓGICA GET (BÚSQUEDA Y FILTROS) ---
    query = request.GET.get('q')
    filtro_estatus = request.GET.get('estatus') # Nuevo parámetro para filtrar
    
    empleados = Empleado.objects.all().order_by('-id')
    
    # Aplicar Filtro de Estatus (Activo/Inactivo)
    if filtro_estatus in ['Activo', 'Inactivo']:
        empleados = empleados.filter(estatus=filtro_estatus)

    # Aplicar Búsqueda de texto
    if query:
        empleados = empleados.filter(
            nombre__icontains=query
        ) | empleados.filter(
            codigo_empleado__icontains=query
        ) | empleados.filter(
            apellido_paterno__icontains=query
        )

    return render(request, 'Employe.html', {'empleados': empleados})
# --- AJAX PARA EL MODAL ---
def gestionar_documentos_ajax(request, emp_id):
    empleado = get_object_or_404(Empleado, id=emp_id)
    
    # --- SUBIR FOTO O PDF ---
    if request.method == 'POST':
        if request.FILES.get('foto'):
            empleado.foto = request.FILES['foto']
            empleado.save()
            return JsonResponse({'status': 'ok', 'url': empleado.foto.url})

        if request.FILES.get('pdf'):
            pdf = request.FILES['pdf']
            Documento.objects.create(
                empleado=empleado, 
                nombre_archivo=pdf.name, 
                archivo=pdf,
                fecha_subida=date.today() # Asegúrate de asignar la fecha
            )
            return JsonResponse({'status': 'ok'})

    # --- ELIMINAR ---
    if request.method == 'DELETE':
        doc_id = request.GET.get('doc_id')
        if doc_id:
            doc = get_object_or_404(Documento, id=doc_id, empleado=empleado)
            doc.delete()
            return JsonResponse({'status': 'ok'})
        return JsonResponse({'status': 'error', 'message': 'Falta ID'}, status=400)

    # --- LISTAR ---
    docs = []
    # Usamos filter para obtener solo los de este empleado
    documentos_db = Documento.objects.filter(empleado=empleado)
    for d in documentos_db:
        docs.append({
            'id': d.id,
            'nombre': d.nombre_archivo,
            'url': d.archivo.url if d.archivo else "#",
            'fecha': d.fecha_subida.strftime("%d/%m/%Y") if d.fecha_subida else "S/F"
        })

    return JsonResponse({
        # Verificación de seguridad para la foto
        'foto_url': empleado.foto.url if (empleado.foto and hasattr(empleado.foto, 'url')) else None,
        'documentos': docs
    })

def lista_empleados(request):
    estatus_filtro = request.GET.get('estatus')
    query = request.GET.get('q')
    
    empleados = Empleado.objects.all()
    
    if estatus_filtro:
        empleados = empleados.filter(estatus=estatus_filtro)
    
    if query:
        empleados = empleados.filter(nombre__icontains=query) # O tu lógica de búsqueda
        
    return render(request, 'Employe.html', {'empleados': empleados})

def Asistencias_view(request):
    # 1. CARGA DINÁMICA: Reemplaza el diccionario manual por esto
    puestos_db = ConfigSueldo.objects.all()
    # Creamos el diccionario al vuelo para no romper tu lógica de 'obtener_monto_bloque'
    puestos_salarios = {p.puesto: float(p.monto) for p in puestos_db}
    
    hoy_dt = date.today()
    # Obtenemos el número de semana actual (ISO) y el año
    semana_actual = hoy_dt.isocalendar()[1]
    anio_actual = hoy_dt.isocalendar()[0]

    def obtener_monto_bloque(base_puesto, entrada, salida):
        if not entrada or not salida:
            return 0.0
        
        ent_str = entrada.strip().upper()
        sal_str = salida.strip().upper()

        # Si es un código de retardo (R1, R2...) pagamos el bloque completo
        if 'R' in ent_str or ':' not in ent_str or 'R' in sal_str or ':' not in sal_str:
            return float(base_puesto)

        try:
            fmt = '%H:%M'
            inicio = datetime.strptime(ent_str[:5], fmt)
            fin = datetime.strptime(sal_str[:5], fmt)
            
            diferencia = fin - inicio
            hrs = diferencia.total_seconds() / 3600
            if hrs < 0: hrs += 24 # Soporte para cruce de medianoche
            
            # Cálculo proporcional basado en bloque estándar de 6 horas
            return (float(base_puesto) / 6) * hrs
        except (ValueError, ZeroDivisionError):
            return float(base_puesto)


    # --- LÓGICA DE ELIMINACIÓN ---
    if request.method == 'POST' and 'eliminar_id' in request.POST:
        CLAVE_SEGURIDAD = "1234"  # <--- Cambia aquí tu contraseña de borrado
        
        # 1. Obtener datos del POST
        asistencia_id = request.POST.get('eliminar_id')
        clave_ingresada = request.POST.get('clave_borrado') # Viene del prompt de JS
        
        # 2. Validar Clave
        if clave_ingresada != CLAVE_SEGURIDAD:
            messages.error(request, "❌ Clave de seguridad incorrecta. No se pudo eliminar.")
            return redirect('asistencias')

        # 3. Validar existencia y semana
        asistencia = get_object_or_404(Asistencia, id=asistencia_id)
        fecha_reg = asistencia.fecha
        
        if fecha_reg.isocalendar()[1] != semana_actual or fecha_reg.isocalendar()[0] != anio_actual:
            messages.error(request, "🔒 No puedes eliminar registros de semanas anteriores.")
            return redirect('asistencias')
            
        # 4. Proceder al borrado
        asistencia.delete()
        messages.success(request, "✅ Registro eliminado correctamente.")
        return redirect('asistencias')

    # --- LÓGICA DE GUARDADO / MODIFICACIÓN ---
    if request.method == 'POST':
        try:
            # 0. VALIDACIÓN DE SEGURIDAD: Bloqueo por semana actual
            fecha_captura_str = request.POST.get('fecha')
            fecha_dt = datetime.strptime(fecha_captura_str, '%Y-%m-%d').date()
            
            hoy_dt = date.today()
            semana_actual = hoy_dt.isocalendar()[1]
            anio_actual = hoy_dt.isocalendar()[0]
            
            semana_registro = fecha_dt.isocalendar()[1]
            anio_registro = fecha_dt.isocalendar()[0]

            if semana_registro != semana_actual or anio_registro != anio_actual:
                messages.error(request, "⚠️ Error: Solo se permite gestionar asistencias de la semana actual.")
                return redirect('asistencias')

            # --- LÓGICA DINÁMICA DE SUELDOS ---
            # Obtenemos el sueldo directamente de la base de datos según el puesto
            asistencia_id = request.POST.get('asistencia_id')
            empleado_id = request.POST.get('empleado')
            puesto_seleccionado = (request.POST.get('puesto') or "").strip()
            estatus = request.POST.get('estatus_jornada')
            
            ent_m = (request.POST.get('entrada_matutina') or "").strip()
            sal_m = (request.POST.get('salida_matutina') or "").strip()
            ent_v = (request.POST.get('entrada_vespertina') or "").strip()
            sal_v = (request.POST.get('salida_vespertina') or "").strip()

            # 1. Cálculo de monto final
            monto_final = 0.0
            DESCANSO_DESTAJO = 138.00

            if estatus in ["Falta", "Permiso", "Vacaciones"]:
                monto_final = 0.0
            
            elif estatus == "Descanso":
                if puesto_seleccionado in ["Tuppers"]:
                    monto_final = DESCANSO_DESTAJO
                else:
                    monto_final = 0.0        
            
            elif puesto_seleccionado == "Tuppers":
                cargas = float(request.POST.get('cantidad_cargas') or 0)
                monto_final = cargas * 46.50

            else:
                # BUSQUEDA DINÁMICA: Intentamos traer el sueldo de la DB
                config_obj = ConfigSueldo.objects.filter(puesto=puesto_seleccionado).first()
                salario_base_db = float(config_obj.monto) if config_obj else 0.0
                
                base_6h = salario_base_db
                
                # 2. Ajuste de base según la duración del puesto
                if "(9 horas)" in puesto_seleccionado or "(9 Horas)" in puesto_seleccionado:
                    base_6h = salario_base_db / 1.5
                elif "(12 Horas)" in puesto_seleccionado:
                    base_6h = salario_base_db / 2

                # 3. Calcular lo devengado por cada turno (Mañana y Tarde)
                pago_m = obtener_monto_bloque(base_6h, ent_m, sal_m)
                pago_v = obtener_monto_bloque(base_6h, ent_v, sal_v)
                
                # 4. Sumar el total trabajado en el día
                total_trabajado_dia = pago_m + pago_v
                
                # 5. Aplicar multiplicador por Estatus Especial
                multiplicador = 1.0
                if estatus in ["Descanso trabajado", "Festivo"]:
                    multiplicador = 2.0
                
                # 6. Asignar resultado final a monto_final
                monto_final = total_trabajado_dia * multiplicador

            # [Aquí continuaría el resto de tu lógica: calcular_puntos, validación de duplicados y .save()]

            # 2. Puntos de Retardo (Referencia en campo horas)
            def calcular_puntos(valor):
                if not valor or ":" in valor or "R1" in valor: return 0
                mapping = {"R2": 1, "R3": 2, "R4": 3, "R5": 4, "R6": 5, "R7": 6, "R8": 7, "R9": 8, "R10": 9, "R11": 10, "R12": 11}
                for clave, pts in mapping.items():
                    if clave in valor.upper(): return pts
                return 0

            total_puntos = calcular_puntos(ent_m) + calcular_puntos(ent_v)

            # 3. Guardado en Base de Datos con Lógica de Doble Turno
            fecha_captura = request.POST.get('fecha')
            empleado_obj = Empleado.objects.get(id=empleado_id)
            
            # Determinamos si el registro actual tiene datos matutinos o vespertinos
            es_matutino = bool(ent_m and sal_m)
            es_vespertino = bool(ent_v and sal_v)

            # Buscamos duplicados específicos por turno
            registros_dia = Asistencia.objects.filter(empleado=empleado_obj, fecha=fecha_captura).exclude(id=asistencia_id or -1)

            # Validamos si ya existe registro para el turno que intenta guardar
            if es_matutino and registros_dia.filter(entrada_matutina__isnull=False).exclude(entrada_matutina='').exists():
                messages.error(request, "¡ERROR! Ya existe un registro para el TURNO MATUTINO de este empleado en esta fecha.")
                return redirect('asistencias')
            
            if es_vespertino and registros_dia.filter(entrada_vespertina__isnull=False).exclude(entrada_vespertina='').exists():
                messages.error(request, "¡ERROR! Ya existe un registro para el TURNO VESPERTINO de este empleado en esta fecha.")
                return redirect('asistencias')

            # Si no hay conflicto de turno, procedemos a crear o actualizar
            if asistencia_id and asistencia_id.strip():
                asistencia = get_object_or_404(Asistencia, id=asistencia_id)
            else:
                asistencia = Asistencia()
                asistencia.empleado = empleado_obj
                
            asistencia.fecha = fecha_captura

            # Asignación de campos
            asistencia.estatus = estatus
            asistencia.puesto = puesto_seleccionado
            asistencia.sucursal = request.POST.get('sucursal', 'Victoria')
            asistencia.pago_dia = round(monto_final, 2)
            asistencia.horas = float(total_puntos)
            
            asistencia.entrada_matutina = ent_m
            asistencia.salida_matutina = sal_m
            asistencia.entrada_vespertina = ent_v
            asistencia.salida_vespertina = sal_v

            asistencia.bonificacion = float(request.POST.get('bonificacion') or 0)
            asistencia.descuento = float(request.POST.get('descuento') or 0)
            asistencia.motivo_bonificacion = request.POST.get('motivo_bonificacion')
            asistencia.motivo_descuento = request.POST.get('motivo_descuento')
            asistencia.tipo_uniforme = request.POST.get('tipo_uniforme')
            asistencia.observaciones = request.POST.get('observaciones')
            
            asistencia.save()
            messages.success(request, "¡Registro guardado con éxito!")
            return redirect('asistencias')
        except Exception as e:
            messages.error(request, f"Error al procesar: {e}")
            return redirect('asistencias')

    # --- LÓGICA GET (MOMIAS) ---
    fecha_filtro = request.GET.get('fecha_filtro')
    query = request.GET.get('q', '').strip() 
        
    # Registro base
    registros_qs = Asistencia.objects.exclude(sucursal="FastFood").order_by('-fecha', '-id')
        
    # Filtro por Fecha (Independiente)
    fecha_filtro = request.GET.get('fecha_filtro')
    query = request.GET.get('q', '').strip() 
        
    registros_qs = Asistencia.objects.exclude(sucursal="FastFood").order_by('-fecha', '-id')
        
    if fecha_filtro:
        registros_qs = registros_qs.filter(fecha=fecha_filtro)
        
    if query:
        # 1. Dividimos la búsqueda en palabras (ej: "Juan Perez" -> ["Juan", "Perez"])
        palabras = query.split()
        
        # 2. Creamos un objeto Q base
        q_busqueda = Q()

        for palabra in palabras:
            # Para cada palabra, buscamos que coincida en nombre OR apellido OR código
            # Esto permite que "Perez Juan" también funcione
            q_busqueda &= (
                Q(empleado__nombre__icontains=palabra) | 
                Q(empleado__apellido_paterno__icontains=palabra) |
                Q(empleado__apellido_materno__icontains=palabra) |
                Q(empleado__codigo_empleado__icontains=palabra)
            )
        
        registros_qs = registros_qs.filter(q_busqueda).distinct()
        
    # Paginación
    paginator = Paginator(registros_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # Renderizado con los datos de Momias
    puestos_db = ConfigSueldo.objects.all()
    puestos_salarios_dinamico = {p.puesto: float(p.monto) for p in puestos_db}

    return render(request, 'Attendance.html', {
        'lista_puestos': sorted(puestos_salarios_dinamico.keys()), 
        'empleados': Empleado.objects.filter(estatus='Activo'),
        'registros': page_obj,
        'hoy': datetime.now().strftime('%Y-%m-%d'),
        'puestos_json': json.dumps(puestos_salarios_dinamico),
        'fecha_filtro': fecha_filtro or '', 
        'query': query or '',
        'semana_actual': semana_actual,
        'anio_actual': anio_actual,
    })

def Asistencias_FF_view(request):
    # 1. CARGA DE DATOS INICIALES
    puestos_db = ConfigSueldo.objects.all()
    puestos_salarios_ff = {p.puesto: float(p.monto) for p in puestos_db}
    
    hoy_dt = date.today()
    semana_actual = hoy_dt.isocalendar()[1]
    anio_actual = hoy_dt.isocalendar()[0]

    # --- FUNCIÓN AUXILIAR DE CÁLCULO ---
    def obtener_monto_bloque(base_puesto, entrada, salida):
        if not entrada or not salida:
            return 0.0
        
        ent_str = entrada.strip().upper()
        sal_str = salida.strip().upper()

        # Si es un código de retardo (R1, R2...) o no tiene formato de hora
        if 'R' in ent_str or ':' not in ent_str or 'R' in sal_str or ':' not in sal_str:
            return float(base_puesto)

        try:
            fmt = '%H:%M'
            inicio = datetime.strptime(ent_str[:5], fmt)
            fin = datetime.strptime(sal_str[:5], fmt)
            
            diferencia = fin - inicio
            hrs = diferencia.total_seconds() / 3600
            if hrs < 0: hrs += 24 
            
            return (float(base_puesto) / 6) * hrs
        except (ValueError, ZeroDivisionError):
            return float(base_puesto)

    # --- PROCESAMIENTO DE POST (UNIFICADO) ---
    if request.method == 'POST':
        # A. LÓGICA DE ELIMINACIÓN
        # A. LÓGICA DE ELIMINACIÓN
        if 'eliminar_id' in request.POST:
            CLAVE_BORRADO = "1234"
            asistencia_id = request.POST.get('eliminar_id')
            clave_ingresada = request.POST.get('clave_borrado')

            if clave_ingresada != CLAVE_BORRADO:
                messages.error(request, "❌ Clave incorrecta.")
                return redirect('asistenciasff')

            asistencia = get_object_or_404(Asistencia, id=asistencia_id)
            sem_reg = asistencia.fecha.isocalendar()[1]
            anio_reg = asistencia.fecha.isocalendar()[0]
            
            # CORRECCIÓN: Solo bloquea si el año es anterior O si es el mismo año pero semana anterior
            if anio_reg < anio_actual or (anio_reg == anio_actual and sem_reg < semana_actual):
                messages.error(request, "🔒 No puedes eliminar registros de semanas PASADAS.")
            else:
                asistencia.delete()
                messages.success(request, "✅ Registro eliminado.")
            return redirect('asistenciasff')

        # B. LÓGICA DE GUARDADO / MODIFICACIÓN
        try:
            asistencia_id = request.POST.get('asistencia_id')
            empleado_id = request.POST.get('empleado')
            empleado_obj = get_object_or_404(Empleado, id=empleado_id)
            fecha_captura = request.POST.get('fecha')
            fecha_dt = datetime.strptime(fecha_captura, '%Y-%m-%d').date()
            sem_f = fecha_dt.isocalendar()[1]
            anio_f = fecha_dt.isocalendar()[0]
            
            # CORRECCIÓN: Permitir la semana actual y cualquier semana futura
            if anio_f < anio_actual or (anio_f == anio_actual and sem_f < semana_actual):
                messages.error(request, "🔒 Error: No se pueden gestionar registros de semanas pasadas.")
                return redirect('asistenciasff')

            # Captura de campos del formulario
            puesto_sel = (request.POST.get('puesto') or "").strip()
            estatus_jornada = request.POST.get('estatus_jornada')
            ent_m = (request.POST.get('entrada_matutina') or "").strip()
            sal_m = (request.POST.get('salida_matutina') or "").strip()
            ent_v = (request.POST.get('entrada_vespertina') or "").strip()
            sal_v = (request.POST.get('salida_vespertina') or "").strip()

            # Validación de duplicados (Excluyendo el ID actual si es edición)
            id_excluir = int(asistencia_id) if (asistencia_id and asistencia_id.isdigit()) else -1
            registros_dia = Asistencia.objects.filter(empleado=empleado_obj, fecha=fecha_captura).exclude(id=id_excluir)
            
            if ent_m and sal_m and registros_dia.filter(entrada_matutina__isnull=False).exclude(entrada_matutina='').exists():
                messages.error(request, "¡ERROR! Ya existe un registro matutino hoy.")
                return redirect('asistenciasff')

            # Lógica de Retardos R1 (Descuento)
            inicio_sem = fecha_dt - timedelta(days=fecha_dt.weekday())
            reg_semana = Asistencia.objects.filter(empleado=empleado_obj, fecha__range=[inicio_sem, fecha_dt]).exclude(id=id_excluir)
            
            r_acum = sum((1 if reg.entrada_matutina and 'R1' in reg.entrada_matutina.upper() else 0) + 
                         (1 if reg.entrada_vespertina and 'R1' in reg.entrada_vespertina.upper() else 0) for reg in reg_semana)
            
            r_hoy = (1 if 'R1' in ent_m.upper() else 0) + (1 if 'R1' in ent_v.upper() else 0)
            total_r = r_acum + r_hoy
            
            base_puesto = float(puestos_salarios_ff.get(puesto_sel, 0.0))
            desc_retardo = (base_puesto / 2) if (total_r > 0 and total_r % 2 == 0) else 0.0

            # Cálculo de Monto Base
            monto_calc = 0.0
            puesto_up = puesto_sel.upper()

            if estatus_jornada in ["Falta", "Permiso", "Vacaciones"]:
                monto_calc = 0.0
            elif estatus_jornada == "Descanso":
                monto_calc = 138.00 if puesto_sel in ["Hamburguesas FF", "Tuppers"] else 0.0
            elif puesto_sel == "Hamburguesas FF":
                c_ff = float(request.POST.get('cantidad_cargas') or 0)
                c_mom = float(request.POST.get('cantidad_cargas_momias') or 0)
                monto_calc = (c_ff * 62.00) + (c_mom * 51.50)
            elif puesto_sel == "Tuppers":
                monto_calc = float(request.POST.get('cantidad_cargas') or 0) * 46.50
            else:
                # Determinación de divisor
                if any(x in puesto_up for x in ["9 HORAS", "9HRS", "CREPAS", "LIMPIEZA"]): divisor = 9.0
                elif any(x in puesto_up for x in ["12 HORAS", "GERENTE"]): divisor = 12.0
                else: divisor = 6.0

                base_6h = (base_puesto / divisor) * 6
                es_bloque_u = any(x in puesto_up for x in ["INTERMEDIO", "CREPAS", "FIN DE SEMANA", "GERENTE"])
                
                if es_bloque_u:
                    ini = ent_m if (ent_m and ":" in ent_m) else ent_v
                    fin = sal_v if (sal_v and ":" in sal_v) else sal_m
                    monto_calc = obtener_monto_bloque(base_6h, ini, fin)
                else:
                    monto_calc = obtener_monto_bloque(base_6h, ent_m, sal_m) + obtener_monto_bloque(base_6h, ent_v, sal_v)

            # Aplicar multiplicador si es festivo o descanso trabajado
            if estatus_jornada in ["Descanso trabajado", "Festivo"]:
                monto_calc *= 2.0

            # GUARDADO
            bono = float(request.POST.get('bonificacion') or 0)
            desc_man = float(request.POST.get('descuento') or 0)

            # Recuperar o Crear
            if id_excluir != -1:
                asistencia = get_object_or_404(Asistencia, id=id_excluir)
            else:
                asistencia = Asistencia(sucursal="FastFood")

            asistencia.empleado = empleado_obj
            asistencia.fecha = fecha_dt
            asistencia.estatus = estatus_jornada
            asistencia.puesto = puesto_sel
            asistencia.entrada_matutina, asistencia.salida_matutina = ent_m, sal_m
            asistencia.entrada_vespertina, asistencia.salida_vespertina = ent_v, sal_v
            asistencia.bonificacion = bono
            asistencia.descuento = desc_man + desc_retardo
            asistencia.pago_dia = round(monto_calc + bono - asistencia.descuento, 2)
            asistencia.horas = float(total_r) # Guardamos R1 acumulados
            
            # Observaciones automáticas por retardo
            obs = (request.POST.get('observaciones') or "").strip()
            if desc_retardo > 0:
                asistencia.observaciones = f"{obs} | Desc. por {total_r} retardos R1.".strip(" |")
            else:
                asistencia.observaciones = obs

            asistencia.save()
            messages.success(request, f"✅ Guardado. R1 en la semana: {total_r}")
            return redirect('asistenciasff')

        except Exception as e:
            messages.error(request, f"❌ Error: {e}")
            return redirect('asistenciasff')

    # --- LÓGICA GET (FILTROS Y RENDER) ---
    fecha_filtro = request.GET.get('fecha_filtro', '').strip()
    query = request.GET.get('q', '').strip()
    registros_qs = Asistencia.objects.filter(sucursal="FastFood")

    if fecha_filtro:
        registros_qs = registros_qs.filter(fecha=fecha_filtro)
    if query:
        palabras = query.split()
        q_bus = Q()
        for p in palabras:
            q_bus &= (Q(empleado__nombre__icontains=p) | Q(empleado__apellido_paterno__icontains=p) | 
                      Q(empleado__apellido_materno__icontains=p) | Q(empleado__codigo_empleado__icontains=p))
        registros_qs = registros_qs.filter(q_bus).distinct()

    return render(request, 'AttendanceFF.html', {
        'lista_puestos': sorted(puestos_salarios_ff.keys()),
        'empleados': Empleado.objects.filter(estatus='Activo'),
        'registros': registros_qs.order_by('-fecha', '-id')[:30],
        'hoy': hoy_dt.strftime('%Y-%m-%d'),
        'puestos_json': json.dumps(puestos_salarios_ff),
        'semana_actual': semana_actual,
        'fecha_filtro': fecha_filtro,
        'query': query,
    })


@login_required
def registrar_usuario(request):
    # SEGURIDAD: Solo el jefe (superuser) entra aquí
    if not request.user.is_superuser:
        messages.error(request, "¡SANTO CIELO! No tienes permisos de administrador.")
        return redirect('main')

    if request.method == 'POST':
        nombre = request.POST.get('username')
        clave = request.POST.get('password')
        clave_confirm = request.POST.get('password_confirm')

        # Validaciones rápidas
        if clave != clave_confirm:
            messages.error(request, "¡LAS CONTRASEÑAS NO COINCIDEN!")
        elif User.objects.filter(username=nombre).exists():
            messages.error(request, "ESE NOMBRE YA ESTÁ OCUPADO.")
        else:
            # Crear el usuario oficial en Django
            nuevo_usuario = User.objects.create_user(username=nombre, password=clave)
            nuevo_usuario.save()
            messages.success(request, f"¡Usuario {nombre} registrado con éxito!")
            return redirect('main')

    return render(request, 'Register.html')

@login_required
def Lista_Usuarios_View(request):
    # Seguridad: solo el superusuario puede ver la lista
    if not request.user.is_superuser:
        return redirect('main')
    
    # CAMBIO: Quitamos el exclude para que TÚ también aparezcas en la tabla
    usuarios = User.objects.all().order_by('username')
    
    return render(request, 'Lista_Usuarios.html', {'usuarios': usuarios})
    
    # Obtenemos todos los usuarios excepto al superusuario logueado (para que no se borre a sí mismo por error)
    usuarios = User.objects.exclude(id=request.user.id)
    return render(request, 'Lista_Usuarios.html', {'usuarios': usuarios})

@login_required
def Borrar_Usuario_View(request, usuario_id):
    if not request.user.is_superuser:
        return redirect('main')
    
    usuario = User.objects.get(id=usuario_id)
    nombre = usuario.username
    usuario.delete()
    
    messages.success(request, f"El usuario '{nombre}' ha sido eliminado.")
    return redirect('lista_usuarios')

@login_required
def calcular_nomina_web(request):
    from django.db.models import Q
    from collections import Counter
    from datetime import datetime, timedelta
    from .models import Asistencia, Empleado
    from django.shortcuts import render

    fecha_inicio = request.GET.get('inicio')
    fecha_fin = request.GET.get('fin')
    sucursal_filtro = request.GET.get('sucursal')
    nombre_filtro = request.GET.get('nombre')
    
    resultados_nomina = []

    puestos_salarios = {
        "Caja (6 horas)": 248.00,  "Caja (9 horas)": 354.50,
        "Gerente (12 Horas)": 600.00, "Chef de Línea (9 horas)": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00,
        "Encargado Cocina (Matutino 9 horas)": 378.00,
        "Encargado Cocina (Matutino 12 horas)": 519.00,
        "Encargado de Cocina (12 horas)": 519.00,
        "Cocina y Barra (6 hrs)": 236.50,
        "Cocina y Barra (9 hrs)": 354.50,
        "Barra (6 horas) Entregas": 236.50,
        "Barra (9 horas) Entregas": 354.50,
        "Fin de Semana": 473.00,
        "Aux Produccion": 177.00,
        "Produccion": 370.00,
        "Encargado Victoria (6 Horas)": 316.00,
        "Encargado Sucursales (6 Horas)": 262.00,
        "Encargado Sucursales (9 Horas)": 393.00, 
        "Freidor (6 horas)": 248.00,
        "Despacho (6 horas)": 236.50,
        "Aderezos": 236.50,
        "Cocina": 248.00,
        "Fabrica": 236.50,
        "Perrioni": 236.50,
        "PP": 236.50,
        "Yommy": 236.50,
        "PM": 236.50,
        "Rappi": 354.75,
        "Fabrica Crystal": 262.00,
        "Hamburguesas Momias": 0.00,
        "Tuppers": 0.00,
        "Benny": 171.00,
        "Caja Capacitacion": 236.50,
        "Freidor Capacitacion": 236.50,
        "Encargado Capacitacion": 248.00,
        "Caja Matutina (6 horas)": 236.50, 
        "Caja Vespertina (6 horas)": 236.50,
        "Caja Matutina (9 horas)": 354.50,
        "Caja Vespertina (9 horas)": 354.50,
        "Cocina Matutina (6 horas)": 236.50,
        "Cocina Vespertina (6 horas)": 236.50,
        "Cocina Matutina (9 horas)": 354.50,
        "Cocina Vespertina (9 horas)": 354.50,
        "Crepas Intermedio (9 horas)": 354.50,
        "Barra y Cocina Fin De Semana (12 horas)": 473.00,
        "Limpieza Fin De Semana (9 horas)": 408.00,
        "Limpieza 1 Matutino (6 horas L)": 272.00,
        "Limpieza 2 Matutino (6 horas)": 236.50,
        "Limpieza 3 Vespertino (6 horas A)": 272.00,
        "Limpieza 4 Vespertino (6 horas)": 236.50,
        "TURNO MATUTINO (6 horas)": 236.50, 
        "TURNO VESPERTINO (6 horas)": 236.50,
        "TURNO MATUTINO (9 horas)": 354.50,
        "TURNO VESPERTINO (9 horas)": 354.50,
        "TURNO FIN DE SEMANA": 473.00,
        "Gerente (12 horas)": 600.00, 
        "Chef de Línea (9 horas)": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00,
        "Crepas": 354.50,
        "Limpieza Fin De Semana (9 horas)": 408.00,
        "Limpieza 1 Matutino (6 horas L)": 272.00,
        "Limpieza 2 Matutino (6 horas)": 236.50,
        "Limpieza 3 Vespertino (6 horas A)": 272.00,
        "Limpieza 4 Vespertino (6 horas)": 236.50,
        "Fin de Semana": 473.00,
        "Aux Produccion": 177.00,
        "Produccion": 370.00,
        "Hamburguesas FF": 0.0,
    }

    DESCUENTO_UNIFORME_SEMANAL = 181.00

    def procesar_dato_hibrido(valor, es_entrada, bloque):
        if not valor: return None, 0
        v = str(valor).strip().upper()
        if ':' in v:
            try:
                partes = v.split(':')
                h = int(partes[0])
                m = int(partes[1][:2])
                min_reloj = h * 60 + m
                retardo = 0
                if es_entrada:
                    hora_base = 9 * 60 if bloque == 'M' else 15 * 60
                    if min_reloj > hora_base:
                        retardo = (min_reloj - hora_base) / 60 
                return min_reloj, retardo
            except: pass
        if v.isdigit():
            retardo_num = int(v)
            if es_entrada:
                hora_ficticia = (9 + retardo_num) * 60 if bloque == 'M' else (15 + retardo_num) * 60
            else:
                hora_ficticia = (15 - retardo_num) * 60 if bloque == 'M' else (21 - retardo_num) * 60
            return hora_ficticia, retardo_num
        if "NORMAL" in v:
            hora_base = (9*60 if es_entrada else 15*60) if bloque == 'M' else (15*60 if es_entrada else 21*60)
            return hora_base, 0
        min_default = (9*60 if es_entrada else 15*60) if bloque == 'M' else (15*60 if es_entrada else 21*60)
        return min_default, 0

    def calcular_pago_dia_final(base_6h, reg):
        minutos_trabajados = 0
        m_ent_m, r_ent_m = procesar_dato_hibrido(reg.entrada_matutina, True, 'M')
        m_sal_m, r_sal_m = procesar_dato_hibrido(reg.salida_matutina, False, 'M')
        m_ent_v, r_ent_v = procesar_dato_hibrido(reg.entrada_vespertina, True, 'V')
        m_sal_v, r_sal_v = procesar_dato_hibrido(reg.salida_vespertina, False, 'V')
        retardo_acumulado = r_ent_m + r_sal_m + r_ent_v + r_sal_v
        if m_ent_m and m_sal_v and not m_sal_m and not m_ent_v:
            diff = m_sal_v - m_ent_m
            minutos_trabajados = diff + 1440 if diff < 0 else diff
        else:
            if m_ent_m and m_sal_m:
                diff = m_sal_m - m_ent_m
                if diff < 0: diff += 720
                minutos_trabajados += max(0, diff)
            elif m_ent_m or m_sal_m: minutos_trabajados += 360
            if m_ent_v and m_sal_v:
                diff = m_sal_v - m_ent_v
                if diff < 0: diff += 720
                minutos_trabajados += max(0, diff)
            elif m_ent_v or m_sal_v: minutos_trabajados += 360
        pago = (float(base_6h) / 360) * minutos_trabajados
        return pago, int(retardo_acumulado)

    if fecha_inicio and fecha_fin:
        f_ini_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        f_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        intervalos_semanas = []
        current_start = f_ini_dt
        while current_start <= f_fin_dt:
            dias_al_domingo = 6 - current_start.weekday()
            current_end = min(current_start + timedelta(days=dias_al_domingo), f_fin_dt)
            intervalos_semanas.append((current_start, current_end))
            current_start = current_end + timedelta(days=1)

        # Obtenemos la lista de sucursales seleccionadas
        sucursales_seleccionadas = request.GET.getlist('sucursal')

        for sem_inicio, sem_fin in intervalos_semanas:
            filtros_asistencia = Q(fecha__range=[sem_inicio, sem_fin])
            
            # Filtro para selección múltiple de sucursales
            if sucursal_filtro and "TODAS" not in sucursales_seleccionadas:
                filtros_asistencia &= Q(sucursal__in=sucursales_seleccionadas)
            
            # --- NUEVA LÓGICA DE FILTRADO POR NOMBRE COMPLETO ---
            asistencias_query = Asistencia.objects.filter(filtros_asistencia)
        
            if nombre_filtro:
                # Creamos el campo virtual 'full_name' igual que en tu vista_reporte
                asistencias_query = asistencias_query.annotate(
                    full_name=Concat(
                        'empleado__nombre', Value(' '), 
                        'empleado__apellido_paterno', Value(' '), 
                        'empleado__apellido_materno',
                        output_field=CharField()
                    )
                ).filter(
                    Q(full_name__icontains=nombre_filtro) |
                    Q(empleado__nombre__icontains=nombre_filtro) |
                    Q(empleado__apellido_paterno__icontains=nombre_filtro) |
                    Q(empleado__codigo_empleado__icontains=nombre_filtro)
                )
        
            # Obtenemos los IDs de los empleados que cumplen con los filtros
            empleados_ids = asistencias_query.values_list('empleado_id', flat=True).distinct()
            
            # ... resto de tu lógica para procesar empleados_ids

            for emp_id in empleados_ids:
                empleado = Empleado.objects.get(id=emp_id)
                asistencias = Asistencia.objects.filter(filtros_asistencia, empleado=empleado).order_by('fecha')
                puestos_semana = [a.puesto for a in asistencias if a.puesto and "DESCANSO" not in (a.estatus or "").upper()]
                
                # --- LÓGICA DE DESCANSO AJUSTADA ---
                asistencias_trabajadas = [a for a in asistencias if a.puesto and "DESCANSO" not in (a.estatus or "").upper()]
                
                if asistencias_trabajadas:
                    total_dias_trabajados = len(asistencias_trabajadas)
                    conteo_puestos = Counter([a.puesto for a in asistencias_trabajadas])
                    
                    # 1. Identificar si cumple la regla de jornada completa
                    es_jornada_completa = any(
                        (a.entrada_matutina == "09:00" and a.salida_vespertina == "21:00") 
                        for a in asistencias_trabajadas
                    )

                    # 2. Calcular salario de descanso
                    if es_jornada_completa:
                        puesto_frecuente = conteo_puestos.most_common(1)[0][0]
                        salario_descanso = puestos_salarios.get(puesto_frecuente, 0) * 2
                        puesto_principal = f"{puesto_frecuente} (Doble)"
                    else:
                        salario_descanso = sum((puestos_salarios.get(p, 0) * (c / total_dias_trabajados)) 
                                               for p, c in conteo_puestos.items())
                        puesto_principal = conteo_puestos.most_common(1)[0][0]
                    
                    # 3. Regla especial para turnos de 12 horas
                    dias_dobles = sum(1 for a in asistencias_trabajadas if "(12 Horas)" in (a.puesto or ""))
                    if dias_dobles > 6:
                        salario_descanso *= 2
                        
                else:
                    salario_descanso = float(empleado.sueldo_base or 0)
                    puesto_principal = "Sin Puesto"
    
                # --- PRE-CALCULO DE RETARDOS Y LÓGICA DE PAGO ÚNICO ---
                lista_detalles_asistencia = []
                total_retardos_semanales = 0
                descanso_pagado = False  # Bandera para pago único
                
                for reg in asistencias:
                    estatus_limpio = (reg.estatus or "").upper()
                    salario_base_puesto = puestos_salarios.get(reg.puesto, empleado.sueldo_base or 0)
                    base_calc = float(salario_base_puesto)
                    
                    if "(9 horas)" in (reg.puesto or ""): base_calc /= 1.5
                    elif "(12 Horas)" in (reg.puesto or ""): base_calc /= 2

                    # Lógica de pago de descanso (Solo el primero se paga)
                    if "DESCANSO" in estatus_limpio and "TRABAJADO" not in estatus_limpio:
                        retardo_dia = 0
                        if not descanso_pagado:
                            salario_dia = salario_descanso
                            descanso_pagado = True
                        else:
                            salario_dia = 0.0
                    elif float(reg.pago_dia or 0.0) > 0:
                        retardo_dia = int(reg.horas or 0)
                        salario_dia = float(reg.pago_dia)
                    else:
                        salario_dia, retardo_aut = calcular_pago_dia_final(base_calc, reg)
                        retardo_dia = int(reg.horas) if reg.horas else retardo_aut
                    
                    if "DESCANSO TRABAJADO" in estatus_limpio or "FESTIVO TRABAJADO" in estatus_limpio:
                        salario_dia *= 2
                    
                    if retardo_dia > 0: total_retardos_semanales += 1
                    
                    lista_detalles_asistencia.append({
                        'reg': reg, 'retardo_dia': retardo_dia, 'salario_dia': salario_dia,
                        'salario_puesto_full': base_calc, 'estatus': estatus_limpio
                    })


                pago_base_total = total_retardos = total_bonos = total_descuentos_manuales = 0
                total_desc_retardos_semanal = 0.0
                total_retardos_acumulados = 0 
                aplica_uniforme_semanal = False 
                dias_semana_esp = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                dias_map = {d: [] for d in dias_semana_esp}
                
                # Definimos los factores por nivel de acumulado
                FACTORES = {0: 0.0, 1: 0.0, 2: 0.5, 3: 0.5, 4: 1.0, 5: 1.0, 6: 1.5, 7: 1.5, 8: 2.0, 9: 2.0, 10: 2.5, 11: 2.5, 12: 3.0}
                
                for item in lista_detalles_asistencia:
                    reg = item['reg']
                    retardo_dia = item['retardo_dia']
                    salario_dia = item['salario_dia'] # Valor total del día
                    
                    desc_retardo_dia = 0.0
                    
                    # 1. Determinamos si es jornada física completa
                    es_jornada_completa = (
                        (reg.entrada_matutina and reg.salida_vespertina and not reg.salida_matutina) or 
                        (reg.entrada_matutina and reg.salida_matutina and reg.entrada_vespertina and reg.salida_vespertina)
                    )
                    
                    if retardo_dia > 0:
                        factor_anterior = FACTORES.get(min(total_retardos_acumulados, 12), 3.0)
                        total_retardos_acumulados += retardo_dia
                        factor_actual = FACTORES.get(min(total_retardos_acumulados, 12), 3.0)
                        
                        diferencia_factor = factor_actual - factor_anterior
                        
                        # 2. Aplicamos el descuento:
                        # Si es jornada completa, queremos 1/4 de un turno de 236.50
                        # 0.5 (diferencia) * 473.0 (salario total) * 0.25 = 59.125 (Esto no es 118)
                        # Para obtener 118.25 directamente:
                        if es_jornada_completa:
                            # 0.5 * 236.50 = 118.25
                            # Usamos la base de un solo turno (236.50) si es jornada completa
                            base_turno = float(salario_dia) / 2
                            desc_retardo_dia = diferencia_factor * base_turno
                        else:
                            # Jornada sencilla: diferencia factor * salario total
                            desc_retardo_dia = diferencia_factor * float(salario_dia)
                        
                    val_bono = float(reg.bonificacion or 0.0)
                    val_desc = float(reg.descuento or 0.0)
                    if reg.tipo_uniforme and len(str(reg.tipo_uniforme).strip()) > 0:
                        aplica_uniforme_semanal = True
                    
                    pago_base_total += salario_dia
                    total_retardos += retardo_dia
                    total_desc_retardos_semanal += desc_retardo_dia
                    total_bonos += val_bono
                    total_descuentos_manuales += val_desc

                    nombre_dia = dias_semana_esp[reg.fecha.weekday()]
                    fecha_str = reg.fecha.strftime('%d/%m/%y')
                    
                    cantidad_turnos = 2 if es_jornada_completa else 1
                    
                    dias_map[nombre_dia].append({
                        'fecha_dia': fecha_str,
                        'puesto': reg.puesto or '---',
                        'sucursal': reg.sucursal or '---',
                        'pago_dia': round(salario_dia, 2),
                        'descuento_retardo': round(desc_retardo_dia, 2),
                        'monto_bono': float(reg.bonificacion or 0),
                        'motivo_bono': reg.motivo_bonificacion,
                        'monto_descuento': float(reg.descuento or 0),     # Pasamos el monto
                        'motivo_descuento': reg.motivo_descuento,
                        'estatus': item['estatus'],
                        'cantidad_turnos': cantidad_turnos
                    })
                # --- FUERA DEL FOR REG, DENTRO DEL FOR EMP_ID ---
                total_uniforme = DESCUENTO_UNIFORME_SEMANAL if aplica_uniforme_semanal else 0.0
                total_neto = (pago_base_total + total_bonos) - (total_descuentos_manuales + total_desc_retardos_semanal + total_uniforme)

                motivos_bonos_semana = [
                    reg.motivo_bonificacion 
                    for reg in asistencias 
                    if reg.motivo_bonificacion and reg.motivo_bonificacion.strip()
                ]
                
                # Unimos los motivos con comas para que se vea como un solo texto
                motivo_bono_texto = ", ".join(motivos_bonos_semana) if motivos_bonos_semana else ""
                
                # --- EN TU BUCLE DE RESULTADOS_NOMINA.APPEND ---
                resultados_nomina.append({
                    'nombre': f"{empleado.nombre} {empleado.apellido_paterno}",
                    'puesto_principal': puesto_principal,
                    'periodo_info': f"{sem_inicio.strftime('%d/%m')} al {sem_fin.strftime('%d/%m')}",
                    'dias': [dias_map[d] for d in dias_semana_esp],
                    'pago_base': round(pago_base_total, 2),
                    'retardos': total_retardos,
                    # CORRECCIÓN: Usa la variable acumulada semanal, no la del último día
                    'monto_bono': float(reg.bonificacion or 0),
                    'motivo_bono': reg.motivo_bonificacion,
                    'motivo_bonificacion': motivo_bono_texto,
                    'desc_retardos': round(total_desc_retardos_semanal, 2), 
                    'bonos': round(total_bonos, 2),
                    'descuentos': round(total_descuentos_manuales, 2),
                    'uniforme': round(total_uniforme, 2),
                    'total_neto': round(total_neto, 2),
                })

    lista_sucursales = [
        "Momias 1", "Momias 2", "Momias 3", "Momias 4", "Momias 5", "Momias 6",
        "PP", "PM", "Yommy", "Perrioni", "Fabrica", "Benny", "Cocina", "Area Seca", "FastFood"
    ]

    return render(request, 'Paysheet.html', { 
        'nominas': resultados_nomina,
        'inicio': fecha_inicio,
        'fin': fecha_fin,
        'sucursal_seleccionada': sucursal_filtro, # Esto sigue funcionando
        'nombre_busqueda': nombre_filtro,
        # AGREGADOS:
        'todas_sucursales': lista_sucursales,
        'sucursales_seleccionadas': request.GET.getlist('sucursal') # Recibimos la lista de los checkboxes
    })
def obtener_datos_nomina_total(inicio, fin, nombre_busqueda=None, sucursal_sel=None):
    from collections import Counter
    from django.db.models import Q

    puestos_salarios = {
        "Gerente (12 Horas)": 600.00, "Chef de Línea (9 horas)": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00, "Encargado Cocina (Matutino 9 horas)": 378.00,
        "Encargado Cocina (Matutino 12 horas)": 504.00, "Encargado de Cocina (12 horas)": 519.00,
        "Cocina y Barra (6 hrs)": 236.50, "Cocina y Barra (9 hrs)": 354.50,
        "Caja (6 horas)": 248.00,  "Caja (9 horas)": 354.50,
        "Barra (6 horas) Entregas": 236.50, "Barra (9 horas) Entregas": 354.50,
        "Fin de Semana": 473.00, "Encargado Victoria (6 Horas)": 316.00,
        "Encargado Sucursales (6 Horas)": 262.00,
        "Encargado Sucursales (9 Horas)": 393.00, "Freidor (6 horas)": 248.00,
        "Freidor (9 horas)": 372.00, "Despacho (6 horas)": 236.50,
        "Despacho (9 horas)": 354.75, "Benny": 171.00,
        "Aderezos": 236.50, "Cocina": 248.00, "Fabrica": 236.50,
        "Perrioni": 236.50, "PP": 236.50, "Yommy": 236.50,
        "Rappi": 354.75, "Fabrica Crystal": 262.00,
        "Hamburguesas Momias": 0.00, "Tuppers": 0.00, 
        "PM": 236.50, "Caja Capacitacion": 236.50,
        "Freidor Capacitacion": 236.50,
        "Encargado Capacitacion": 248.00,
        "Caja Matutina (6 horas)": 236.50, 
        "Caja Vespertina (6 horas)": 236.50,
        "Caja Matutina (9 horas)": 354.50,
        "Caja Vespertina (9 horas)": 354.50,
        "Cocina Matutina (6 horas)": 236.50,
        "Cocina Vespertina (6 horas)": 236.50,
        "Cocina Matutina (9 horas)": 354.50,
        "Cocina Vespertina (9 horas)": 354.50,
        "Crepas Intermedio (9 horas)": 354.50,
        "Barra y Cocina Fin De Semana (12 horas)": 473.00,
        "Limpieza Fin De Semana (9 horas)": 408.00,
        "Limpieza 1 Matutino (6 horas L)": 272.00,
        "Limpieza 2 Matutino (6 horas)": 236.50,
        "Limpieza 3 Vespertino (6 horas A)": 272.00,
        "Limpieza 4 Vespertino (6 horas)": 236.50,
        "Aux Produccion": 177.00,
        "Produccion": 370.00,
        "TURNO MATUTINO (6 horas)": 236.50, 
        "TURNO VESPERTINO (6 horas)": 236.50,
        "TURNO MATUTINO (9 horas)": 354.50,
        "TURNO VESPERTINO (9 horas)": 354.50,
        "TURNO FIN DE SEMANA": 473.00,
        "Gerente (12 horas)": 600.00, 
        "Chef de Línea (9 horas)": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00,
        "Crepas": 354.50,
        "Limpieza Fin De Semana (9 horas)": 408.00,
        "Limpieza 1 Matutino (6 horas L)": 272.00,
        "Limpieza 2 Matutino (6 horas)": 236.50,
        "Limpieza 3 Vespertino (6 horas A)": 272.00,
        "Limpieza 4 Vespertino (6 horas)": 236.50,
        "Fin de Semana": 473.00,
        "Aux Produccion": 177.00,
        "Produccion": 370.00,
        "Hamburguesas FF": 0.0,
    }

    datos_completos = []
    filtros_base = Q(fecha__range=[inicio, fin])
    
    if sucursal_sel and sucursal_sel != "TODAS":
        filtros_base &= Q(sucursal__iexact=sucursal_sel)
    if nombre_busqueda:
        filtros_base &= (Q(empleado__nombre__icontains=nombre_busqueda) | 
                         Q(empleado__apellido_paterno__icontains=nombre_busqueda))

    empleados_ids = Asistencia.objects.filter(filtros_base).values_list('empleado_id', flat=True).distinct()

    for emp_id in empleados_ids:
        empleado = Empleado.objects.get(id=emp_id)
        asistencias = Asistencia.objects.filter(filtros_base, empleado=empleado).order_by('fecha')

        puestos_lista = [a.puesto for a in asistencias if a.puesto]
        puesto_principal = Counter(puestos_lista).most_common(1)[0][0] if puestos_lista else "Sin Puesto"

        pago_base_acumulado = 0
        total_retardos = 0
        total_bonos = 0
        total_descuentos_manuales = 0
        total_descuento_retardos_acumulado = 0 
        
        dias_semana_esp = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dias_map = {d: {
            'horas': 0, 'estatus': '---', 'sucursal': '', 'puesto': '', 
            'pago_dia': 0, 'descuento_aplicado': 0, 'descuento_retardo': 0
        } for d in dias_semana_esp}

        for reg in asistencias:
            sueldo_base_puesto_dia = float(puestos_salarios.get(reg.puesto, empleado.sueldo_base or 0))
            
            if reg.pago_dia and float(reg.pago_dia) > 0:
                salario_dia_calculado = float(reg.pago_dia)
            elif reg.entrada_matutina and reg.salida_vespertina:
                salario_dia_calculado = sueldo_base_puesto_dia * 2
            else:
                salario_dia_calculado = sueldo_base_puesto_dia

            estatus_limpio = reg.estatus.upper() if reg.estatus else ""
            
            if any(x in estatus_limpio for x in ["ACTIVO", "NORMAL"]):
                pago_final_dia = salario_dia_calculado
            elif "DESCANSO TRABAJADO" in estatus_limpio or "FESTIVO TRABAJADO" in estatus_limpio:
                pago_final_dia = (salario_dia_calculado * 2)
            elif "DESCANSO" in estatus_limpio:
                pago_final_dia = sueldo_base_puesto_dia
            else:
                pago_final_dia = 0

            horas_retardo = int(reg.horas or 0)
            desc_retardo_dia = (sueldo_base_puesto_dia / 6) * horas_retardo if "DESCANSO" not in estatus_limpio else 0
            desc_manual_dia = float(reg.descuento or 0)
            
            sueldo_neto_diario = pago_final_dia - desc_manual_dia - desc_retardo_dia

            pago_base_acumulado += pago_final_dia
            total_retardos += horas_retardo
            total_bonos += float(reg.bonificacion or 0)
            total_descuentos_manuales += desc_manual_dia
            total_descuento_retardos_acumulado += desc_retardo_dia

            nombre_dia = dias_semana_esp[reg.fecha.weekday()]
            dias_map[nombre_dia] = {
                'horas': horas_retardo,
                'estatus': estatus_limpio,
                'sucursal': reg.sucursal,
                'puesto': reg.puesto,
                'pago_dia': round(sueldo_neto_diario, 2),
                'descuento_aplicado': round(desc_manual_dia, 2),
                'descuento_retardo': round(desc_retardo_dia, 2)
            }

        cuota_uniforme = float(getattr(empleado, 'cuota_uniforme', 0) or 0)
        total_neto = (pago_base_acumulado + total_bonos) - (total_descuentos_manuales + total_descuento_retardos_acumulado + cuota_uniforme)

        datos_completos.append({
            'nombre': f"{empleado.nombre} {empleado.apellido_paterno}",
            'puesto_principal': puesto_principal,
            'periodo_info': f"{inicio} al {fin}",
            'dias': [dias_map[d] for d in dias_semana_esp],
            'pago_base': round(pago_base_acumulado, 2),
            'retardos': total_retardos,
            'desc_retardos': round(total_descuento_retardos_acumulado, 2),
            'bonos': round(total_bonos, 2),
            'descuentos': round(total_descuentos_manuales, 2),
            'uniforme': round(cuota_uniforme, 2),
            'total_neto': round(total_neto, 2)
        })

    # ORDENAR POR NOMBRE ALFABÉTICAMENTE ANTES DE RETORNAR
    datos_completos = sorted(datos_completos, key=lambda x: x['nombre'].lower())

    return datos_completos

def exportar_excel_nomina(request):
    inicio = request.GET.get('inicio')
    fin = request.GET.get('fin')
    nombre = request.GET.get('nombre')
    sucursal = request.GET.get('sucursal')

    datos_calculados = obtener_datos_nomina_total(inicio, fin, nombre, sucursal)
    
    formato_excel = []
    for n in datos_calculados:
        formato_excel.append({
            'EMPLEADO': n['nombre'],
            'PUESTO': n['puesto_principal'],
            'PAGO BASE': n['pago_base'],
            'BONOS': n['bonos'],
            'DESCUENTOS': n['descuentos'],
            'UNIFORME': n['uniforme'],
            'TOTAL NETO': n['total_neto']
        })

    df = pd.DataFrame(formato_excel)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Nomina_{inicio}_al_{fin}.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Nomina')
    return response

def exportar_pdf_nomina(request):
    inicio = request.GET.get('inicio')
    fin = request.GET.get('fin')
    nombre = request.GET.get('nombre')
    sucursal = request.GET.get('sucursal')
    
    datos = obtener_datos_nomina_total(inicio, fin, nombre, sucursal)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Nomina_{inicio}_al_{fin}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter))
    elements = []
    tabla_datos = [["EMPLEADO", "PAGO BASE", "BONOS", "DESC.", "UNIFORME", "TOTAL NETO"]]
    
    for d in datos:
        tabla_datos.append([
            d['nombre'], 
            f"$ {d['pago_base']:,.2f}",
            f"$ {d['bonos']:,.2f}", 
            f"$ {d['descuentos']:,.2f}", 
            f"$ {d['uniforme']:,.2f}", 
            f"$ {d['total_neto']:,.2f}"
        ])

    t = Table(tabla_datos, colWidths=[200, 80, 80, 80, 80, 100])
    # ... aplica aquí tu TableStyle ...
    elements.append(t)
    doc.build(elements)
    return response


@login_required
def vista_reportes(request):
    # Enviamos todos los empleados activos para alimentar el "combo" (datalist)
    empleados_qs = Empleado.objects.filter(estatus='Activo').order_by('nombre')
    
    # Captura de filtros
    query_nombre = request.GET.get('q', '').strip() 
    sucursal_filtro = request.GET.get('sucursal')
    f_inicio = request.GET.get('fecha_inicio')
    f_fin = request.GET.get('fecha_fin')

    # Diccionario de salarios (Mantenemos tu versión extendida)
    puestos_salarios = {
        "Gerente (12 Horas)": 600.00, "Chef de Línea (9 horas)": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00, "Encargado Cocina (Matutino 9 horas)": 378.00,
        "Encargado Cocina (Matutino 12 horas)": 504.00, "Encargado de Cocina (12 horas)": 519.00,
        "Cocina y Barra (6 hrs)": 236.50, "Cocina y Barra (9 hrs)": 354.50,
        "Caja (6 horas)": 248.00,  "Caja (9 horas)": 354.50,
        "Barra (6 horas) Entregas": 236.50, "Barra (9 horas) Entregas": 354.50,
        "Fin de Semana": 473.00, "Encargado Victoria (6 Horas)": 316.00,
        "Encargado Sucursales (6 Horas)": 262.00,
        "Encargado Sucursales (9 Horas)": 393.00, "Freidor (6 horas)": 248.00,
        "Freidor (9 horas)": 372.00, "Despacho (6 horas)": 236.50,
        "Despacho (9 horas)": 354.75, "Benny": 171.00,
        "Aderezos": 236.50, "Cocina": 248.00, "Fabrica": 236.50,
        "Perrioni": 236.50, "PP": 236.50, "Yommy": 236.50,
        "Rappi": 354.75, "Fabrica Crystal": 262.00,
        "PM": 236.50, "Caja Capacitacion": 236.50,
        "Freidor Capacitacion": 236.50, "Encargado Capacitacion": 248.00,
        "Caja Matutina (6 horas)": 236.50, "Caja Vespertina (6 horas)": 236.50,
        "Caja Matutina (9 horas)": 354.50, "Caja Vespertina (9 horas)": 354.50,
        "Cocina Matutina (6 horas)": 236.50, "Cocina Vespertina (6 horas)": 236.50,
        "Cocina Matutina (9 horas)": 354.50, "Cocina Vespertina (9 horas)": 354.50,
        "Crepas Intermedio (9 horas)": 354.50,
        "Barra y Cocina Fin De Semana (12 horas)": 473.00,
        "Limpieza Fin De Semana (9 horas)": 408.00,
        "Limpieza 1 Matutino (6 horas L)": 272.00,
        "Limpieza 2 Matutino (6 horas)": 236.50,
        "Limpieza 3 Vespertino (6 horas A)": 272.00,
        "Limpieza 4 Vespertino (6 horas)": 236.50,
        "Aux Produccion": 177.00, "Produccion": 370.00,
        "TURNO MATUTINO (6 horas)": 236.50, 
        "TURNO VESPERTINO (6 horas)": 236.50,
        "TURNO MATUTINO (9 horas)": 354.50,
        "TURNO VESPERTINO (9 horas)": 354.50,
        "TURNO FIN DE SEMANA": 473.00,
        "Gerente (12 horas)": 600.00, 
        "Chef de Línea (9 horas)": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00,
        "Crepas": 354.50,
        "Limpieza Fin De Semana (9 horas)": 408.00,
        "Limpieza 1 Matutino (6 horas L)": 272.00,
        "Limpieza 2 Matutino (6 horas)": 236.50,
        "Limpieza 3 Vespertino (6 horas A)": 272.00,
        "Limpieza 4 Vespertino (6 horas)": 236.50,
        "Fin de Semana": 473.00,
        "Aux Produccion": 177.00,
        "Produccion": 370.00,
        "Hamburguesas FF": 0.0,
    }

    agrupados_dict = {}
    resumen_global = {'total_pagar': 0, 'total_retardos': 0, 'total_bonif': 0, 'total_turnos': 0, 'total_descuentos': 0}

    if f_inicio and f_fin:
        asistencias_query = Asistencia.objects.filter(fecha__range=[f_inicio, f_fin])
        
        if sucursal_filtro and sucursal_filtro != "TODAS": 
            asistencias_query = asistencias_query.filter(sucursal=sucursal_filtro)
        
        if query_nombre:
            # CORRECCIÓN: Búsqueda por nombre completo concatenado para soportar "Nombre Apellido"
            asistencias_query = asistencias_query.annotate(
                full_name=Concat(
                    'empleado__nombre', Value(' '), 
                    'empleado__apellido_paterno', Value(' '), 
                    'empleado__apellido_materno',
                    output_field=CharField()
                )
            ).filter(
                Q(full_name__icontains=query_nombre) |
                Q(empleado__nombre__icontains=query_nombre) |
                Q(empleado__apellido_paterno__icontains=query_nombre) |
                Q(empleado__codigo_empleado__icontains=query_nombre)
            )

        for asis in asistencias_query:
            emp = asis.empleado
            estatus_limpio = (asis.estatus or "").strip().upper()
            
            es_descanso = "DESCANSO" in estatus_limpio
            pue_original = asis.puesto or emp.puesto or "GENERAL"
            pue_display = "DESCANSO" if es_descanso else pue_original
            suc = asis.sucursal or "Victoria"

            # Detección de turnos
            cantidad_turnos = 2 if (asis.entrada_matutina and asis.salida_vespertina) else 1
            
            pago_dia = float(asis.pago_dia or 0)
            bono_dia = float(asis.bonificacion or 0)
            desc_manual = float(asis.descuento or 0)
            
            puntos_retardo = int(float(asis.horas or 0))
            salario_ref = float(puestos_salarios.get(pue_original, emp.sueldo_base or 0))
            
            # Cálculo de descuento por retardo (Si aplica)
            desc_retardo_inf = (salario_ref / 6) * puntos_retardo if (not es_descanso and puntos_retardo > 0) else 0

            # Llave única por empleado, sucursal y puesto para agrupar
            key = (emp.id, suc, pue_display)
            if key not in agrupados_dict:
                agrupados_dict[key] = {
                    'empleado': f"{emp.nombre} {emp.apellido_paterno} {emp.apellido_materno or ''}".strip(),
                    'sucursal': suc, 
                    'puesto': pue_display,
                    'total_turnos': 0, 
                    'total_retardos': 0,
                    'monto_descuentos': 0.0, 
                    'motivos_descuentos': [],
                    'total_bonos': 0.0, 
                    'total_fila': 0.0
                }
            
            fila = agrupados_dict[key]
            
            # Gestión de motivos de descuento únicos
            if asis.motivo_descuento:
                m_txt = str(asis.motivo_descuento).strip()
                if m_txt and m_txt not in fila['motivos_descuentos']:
                    fila['motivos_descuentos'].append(m_txt)

            fila['total_turnos'] += cantidad_turnos
            fila['total_retardos'] += puntos_retardo
            fila['total_bonos'] += bono_dia
            fila['monto_descuentos'] += (desc_manual + desc_retardo_inf)
            
            # Pago Neto = (Pago del día + Bonos) - Descuentos
            pago_neto_dia = (pago_dia + bono_dia) - desc_manual
            fila['total_fila'] += pago_neto_dia

            # Acumuladores Globales
            resumen_global['total_pagar'] += pago_neto_dia
            resumen_global['total_retardos'] += puntos_retardo
            resumen_global['total_bonif'] += bono_dia
            resumen_global['total_descuentos'] += (desc_manual + desc_retardo_inf)
            resumen_global['total_turnos'] += cantidad_turnos

    # Ordenar resultados por nombre de empleado
    lista_agrupada = sorted(agrupados_dict.values(), key=lambda x: x['empleado'])

    context = {
        'empleados': empleados_qs,
        'agrupados': lista_agrupada,
        'lista_sucursales': ["Momias 1", "Momias 2", "Momias 3", "Momias 4", "Momias 5", "Momias 6", "Fabrica", "Fabrica Crystal","PP","PM","Area Seca","Perrioni", "FastFood"],
        'fecha_inicio': f_inicio,
        'fecha_fin': f_fin,
        'query': query_nombre,
        'gran_total_pagar': round(resumen_global['total_pagar'], 2),
        'gran_total_retardos': resumen_global['total_retardos'],
        'gran_total_bonos': round(resumen_global['total_bonif'], 2),
        'gran_total_descuentos': round(resumen_global['total_descuentos'], 2),
        'gran_total_turnos': resumen_global['total_turnos']
    }
    return render(request, 'Reports.html', context)
    
from django.contrib.auth import update_session_auth_hash # <--- IMPORTANTE: No olvides esta importación

@staff_member_required
def admin_cambiar_password(request, user_id):
    usuario_objetivo = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = AdminPasswordChangeForm(usuario_objetivo, request.POST)
        if form.is_valid():
            user = form.save() # Guardamos el usuario con la nueva clave
            
            # --- EL TRUCO ESTÁ AQUÍ ---
            # Si el usuario que estamos editando es el mismo que tiene la sesión iniciada...
            if request.user == usuario_objetivo:
                update_session_auth_hash(request, user) # Mantiene la sesión activa
                messages.success(request, '¡Tu contraseña ha sido actualizada y tu sesión sigue activa!')
            else:
                messages.success(request, f'¡Contraseña de {usuario_objetivo.username} actualizada!')
            
            return redirect('lista_usuarios') # Asegúrate de que este nombre de URL sea el correcto
    else:
        form = AdminPasswordChangeForm(usuario_objetivo)
    
    return render(request, 'Lista_Usuarios.html', {
        'form': form,
        'usuario_objetivo': usuario_objetivo
    })

@staff_member_required
def gestion_usuario_admin(request, user_id=None):
    edit_mode = False
    usuario_objetivo = None

    # Si hay un ID, estamos en modo "Cambiar Password"
    if user_id:
        edit_mode = True
        usuario_objetivo = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        pass1 = request.POST.get('password')
        pass2 = request.POST.get('password_confirm')

        if not pass1 or pass1 != pass2:
            messages.error(request, "¡Las contraseñas no coinciden o están vacías!")
        else:
            if edit_mode:
                # Actualizar contraseña existente
                usuario_objetivo.set_password(pass1)
                usuario_objetivo.save()
                
                # Si me estoy editando a mí mismo, mantengo la sesión
                if request.user.id == usuario_objetivo.id:
                    update_session_auth_hash(request, usuario_objetivo)
                    messages.success(request, "¡Tu contraseña ha sido actualizada con éxito!")
                else:
                    messages.success(request, f"¡Contraseña de {usuario_objetivo.username} actualizada!")
            else:
                # Crear nuevo usuario
                username = request.POST.get('username')
                if User.objects.filter(username=username).exists():
                    messages.error(request, "Ese nombre ya está en las filas.")
                    return render(request, 'Register.html', {'edit_mode': edit_mode})
                
                User.objects.create_user(username=username, password=pass1)
                messages.success(request, f"¡Recluta {username} registrado!")
            
            # EL REDIRECT CORRECTO según tu urls.py
            return redirect('lista_usuarios') 

    return render(request, 'Register.html', {
        'edit_mode': edit_mode,
        'usuario_objetivo': usuario_objetivo
    })

@staff_member_required
def borrar_usuario(request, user_id):
    # Nota: Tu url usa 'usuario_id', asegúrate que el parámetro coincida
    if request.user.id == user_id:
        messages.error(request, "¡No puedes borrarte a ti mismo!")
        return redirect('lista_usuarios')
    
    usuario = get_object_or_404(User, id=user_id)
    usuario.delete()
    messages.success(request, "Recluta eliminado correctamente.")
    return redirect('lista_usuarios')

def gestion_sueldos(request):
    try:
        if request.method == 'POST':
            puesto_editar = request.POST.get('puesto_nombre')
            puesto_nuevo = request.POST.get('nuevo_puesto_nombre')
            monto_raw = request.POST.get('nuevo_monto')
            
            # Validamos que el monto sea un número válido
            try:
                monto = float(monto_raw) if monto_raw else 0.0
            except ValueError:
                monto = 0.0

            if puesto_editar:
                puesto_obj = ConfigSueldo.objects.filter(puesto=puesto_editar).first()
                if puesto_obj:
                    puesto_obj.monto = monto
                    puesto_obj.save()
                    messages.success(request, f"¡ZAP! {puesto_editar} actualizado.")
            
            elif puesto_nuevo:
                if ConfigSueldo.objects.filter(puesto=puesto_nuevo).exists():
                    messages.error(request, "¡RAYOS! Ese puesto ya existe.")
                else:
                    ConfigSueldo.objects.create(puesto=puesto_nuevo, monto=monto)
                    messages.success(request, f"¡BOOM! {puesto_nuevo} creado.")

            return redirect('gestion_sueldos')

        # Si es GET, cargamos la lista
        sueldos = ConfigSueldo.objects.all().order_by('puesto')
        return render(request, 'Wages.html', {'sueldos': sueldos})

    except Exception as e:
        # Esto evitará el 500 genérico y te dirá qué pasa realmente
        from django.http import HttpResponse
        return HttpResponse(f"Error crítico en la vista: {e}", status=500)
