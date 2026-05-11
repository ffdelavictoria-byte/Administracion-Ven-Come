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
    # 1. Limpieza de sesión al entrar por GET
    if request.user.is_authenticated and request.method == 'GET':
        logout(request) 
    
    if request.method == 'POST':
        # 2. BORRAR mensajes previos encolados para que no se "junten" con el login
        storage = messages.get_messages(request)
        storage.used = True # Esto marca los mensajes viejos como leídos para que no se muestren

        usuario_input = request.POST.get('username')
        clave_input = request.POST.get('password')
        
        user = authenticate(request, username=usuario_input, password=clave_input)
        
        if user is not None:
            login(request, user)
            return redirect('main') 
        else:
            # 3. ÚNICO mensaje permitido: Error de credenciales
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
    
    ahora = datetime.now()
    hoy_dt = ahora.date()
    dia_semana = hoy_dt.isocalendar()[2] # Lunes=1

    # Lunes de esta semana a las 00:00
    lunes_esta_semana = hoy_dt - timedelta(days=dia_semana - 1)
    
    # Si es lunes (1), el límite retrocede a la semana pasada.
    # Si es martes a domingo, el límite es el lunes de esta semana.
    if dia_semana == 1:
        limite_bloqueo = lunes_esta_semana - timedelta(days=7)
    else:
        limite_bloqueo = lunes_esta_semana

    # Datos para el template
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
        CLAVE_SEGURIDAD = "1234"
        asistencia_id = request.POST.get('eliminar_id')
        clave_ingresada = request.POST.get('clave_borrado')
        
        if clave_ingresada != CLAVE_SEGURIDAD:
            messages.error(request, "❌ Clave incorrecta.")
            return redirect('asistencias')

        asistencia = get_object_or_404(Asistencia, id=asistencia_id)
        
        # NUEVA VALIDACIÓN LUNES 11:59 PM
        #if asistencia.fecha < limite_bloqueo:
            #messages.error(request, "🔒 Registro cerrado. El plazo venció el lunes a las 11:59 PM.")
            #return redirect('asistencias')
            
        asistencia.delete()
        messages.success(request, "Registro eliminado correctamente.")
        return redirect('asistencias')

    # --- LÓGICA DE GUARDADO / MODIFICACIÓN ---
    if request.method == 'POST':
        try:
            # 1. Definición temprana de variables para evitar errores de Scope
            asistencia_id = request.POST.get('asistencia_id')
            empleado_id = request.POST.get('empleado')
            fecha_captura = request.POST.get('fecha')
            puesto_seleccionado = (request.POST.get('puesto') or "").strip()
            estatus = request.POST.get('estatus_jornada')
            
            ent_m = (request.POST.get('entrada_matutina') or "").strip()
            sal_m = (request.POST.get('salida_matutina') or "").strip()
            ent_v = (request.POST.get('entrada_vespertina') or "").strip()
            sal_v = (request.POST.get('salida_vespertina') or "").strip()

            # Convertir fecha y obtener objeto empleado
            fecha_dt = datetime.strptime(fecha_captura, '%Y-%m-%d').date()
            empleado_obj = Empleado.objects.get(id=empleado_id)

            # --- APLICACIÓN DEL BLOQUEO ---
            #if fecha_dt < limite_bloqueo:
                #messages.error(request, "⚠️ Error: No puedes modificar registros anteriores al cierre del lunes.")
                #return redirect('asistencias')

            
            # --- LÓGICA DE CÁLCULO DE MONTO ---
            monto_final = 0.0
            DESCANSO_DESTAJO = 138.00

            if estatus in ["Falta", "Permiso", "Vacaciones"]:
                monto_final = 0.0
            
            elif estatus == "Descanso":
                # 1. Definir el rango completo de la semana (Lunes a Domingo)
                inicio_semana = fecha_dt - timedelta(days=fecha_dt.weekday())
                fin_semana = inicio_semana + timedelta(days=6)

                # 2. VALIDACIÓN CRÍTICA: Si tiene alguna falta en la semana, el descanso no se paga
                tiene_faltas_en_semana = Asistencia.objects.filter(
                    empleado=empleado_obj,
                    fecha__range=[inicio_semana, fin_semana],
                    estatus="Falta"
                ).exists()

                if tiene_faltas_en_semana:
                    monto_final = 0.0
                
                # 3. Si no hay faltas, procedemos con la lógica habitual
                elif puesto_seleccionado == "Tuppers":
                    monto_final = DESCANSO_DESTAJO
                else:
                    # Obtenemos asistencias previas para el cálculo de turnos
                    asistencias_semana = Asistencia.objects.filter(
                        empleado=empleado_obj, 
                        fecha__range=[inicio_semana, fecha_dt - timedelta(days=1)]
                    ).exclude(estatus__in=["Descanso", "Falta"])

                    if not asistencias_semana.exists():
                        config_p = ConfigSueldo.objects.filter(puesto=puesto_seleccionado).first()
                        monto_final = float(config_p.monto) if config_p else 0.0
                    else:
                        conteo_turnos_por_puesto = {}
                        dias_doble_turno = 0
                        
                        for asis in asistencias_semana:
                            p = asis.puesto
                            if p not in conteo_turnos_por_puesto:
                                conteo_turnos_por_puesto[p] = 0
                            
                            turnos_hoy = 0
                            if asis.entrada_matutina and asis.salida_matutina:
                                conteo_turnos_por_puesto[p] += 1
                                turnos_hoy += 1
                            if asis.entrada_vespertina and asis.salida_vespertina:
                                conteo_turnos_por_puesto[p] += 1
                                turnos_hoy += 1
                            
                            if turnos_hoy == 2:
                                dias_doble_turno += 1

                        puestos_ordenados = sorted(conteo_turnos_por_puesto.items(), key=lambda x: x[1], reverse=True)
                        monto_base_descanso = 0.0
                        
                        if len(puestos_ordenados) > 1 and puestos_ordenados[0][1] == puestos_ordenados[1][1]:
                            p1_n, p2_n = puestos_ordenados[0][0], puestos_ordenados[1][0]
                            s1 = float(ConfigSueldo.objects.filter(puesto=p1_n).first().monto or 0)
                            s2 = float(ConfigSueldo.objects.filter(puesto=p2_n).first().monto or 0)
                            monto_base_descanso = (s1 / 2) + (s2 / 2)
                        else:
                            p_top = puestos_ordenados[0][0]
                            config_p = ConfigSueldo.objects.filter(puesto=p_top).first()
                            monto_base_descanso = float(config_p.monto) if config_p else 0.0

                        # Aplicar multiplicador si trabajó 6 o más días dobles
                        if dias_doble_turno >= 6:
                            monto_final = monto_base_descanso * 2
                        else:
                            monto_final = monto_base_descanso
                                
            elif puesto_seleccionado == "Tuppers":
                cargas = float(request.POST.get('cantidad_cargas') or 0)
                monto_final = cargas * 46.50

            elif puesto_seleccionado == "Benny":
                config_obj = ConfigSueldo.objects.filter(puesto=puesto_seleccionado).first()
                monto_final = float(config_obj.monto) if config_obj else 0.0

            else:
                # Lógica para turnos normales (Cálculo por horas/bloques)
                config_obj = ConfigSueldo.objects.filter(puesto=puesto_seleccionado).first()
                salario_base_db = float(config_obj.monto) if config_obj else 0.0
                base_6h = salario_base_db
                
                if "(9 horas)" in puesto_seleccionado or "(9 Horas)" in puesto_seleccionado:
                    base_6h = salario_base_db / 1.5
                elif "(12 Horas)" in puesto_seleccionado:
                    base_6h = salario_base_db / 2

                pago_m = obtener_monto_bloque(base_6h, ent_m, sal_m)
                pago_v = obtener_monto_bloque(base_6h, ent_v, sal_v)
                
                multiplicador = 2.0 if estatus in ["Descanso trabajado", "Festivo"] else 1.0
                monto_final = (pago_m + pago_v) * multiplicador

            # --- CONTINUAR CON EL GUARDADO ---
            # (Aquí sigue tu lógica de puntos de retardo y el save() que ya tenías)

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
            if puesto_seleccionado != "Benny":
                if (ent_m and sal_m) and registros_dia.filter(entrada_matutina__isnull=False).exclude(entrada_matutina='').exists():
                    messages.error(request, "¡ERROR! Turno Matutino ya registrado.")
                    return redirect('asistencias')
                if (ent_v and sal_v) and registros_dia.filter(entrada_vespertina__isnull=False).exclude(entrada_vespertina='').exists():
                    messages.error(request, "¡ERROR! Turno Vespertino ya registrado.")
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
            asistencia.cantidad_cargas = float(cargas) # <--- AÑADE ESTA LÍNEA
            
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
        'hoy': hoy_dt.strftime('%Y-%m-%d'),
        'limite_bloqueo': limite_bloqueo, # <--- AGREGA ESTO
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

    # --- LÓGICA DE BLOQUEO (GRACIA DEL LUNES) ---
    dia_semana = hoy_dt.weekday()  # 0=Lunes

    if dia_semana == 0:
        limite_bloqueo = hoy_dt - timedelta(days=7)
    else:
        limite_bloqueo = hoy_dt - timedelta(days=dia_semana)

    semana_actual = hoy_dt.isocalendar()[1]
    anio_actual = hoy_dt.isocalendar()[0]

    # --- FUNCIÓN AUXILIAR ---
    def obtener_monto_bloque(base_puesto, entrada, salida, divisor_puesto):
        if not entrada or not salida: return 0.0
        ent_str = entrada.strip().upper()
        sal_str = salida.strip().upper()
        
        # Si es etiqueta (NORMAL, R1, R2), el pago base es el 100% (el castigo va aparte)
        if any(x in ent_str for x in ['R1', 'R2', 'NORMAL']):
            return float(base_puesto)
    
        # Si es hora manual (ej. 10:30)
        if ':' in ent_str and ':' in sal_str:
            try:
                fmt = '%H:%M'
                t1 = datetime.strptime(ent_str, fmt)
                t2 = datetime.strptime(sal_str, fmt)
                delta = t2 - t1
                hrs = delta.total_seconds() / 3600.0
                # Regla de tres: (Base / Horas que debería trabajar) * Horas que trabajó
                return round((float(base_puesto) / divisor_puesto) * hrs, 2)
            except:
                return float(base_puesto)
        
        return float(base_puesto)

    # --- POST ---
    if request.method == 'POST':

        # A. ELIMINAR
        if 'eliminar_id' in request.POST:
            CLAVE_BORRADO = "1234"

            asistencia_id = request.POST.get('eliminar_id')
            clave_ingresada = request.POST.get('clave_borrado')

            if clave_ingresada != CLAVE_BORRADO:
                messages.error(request, "Clave incorrecta.")
                return redirect('asistenciasff')

            asistencia = get_object_or_404(Asistencia, id=asistencia_id)

            #if asistencia.fecha < limite_bloqueo:
                #messages.error(request, "El periodo de edición para este registro ha vencido.")
            #else:
            asistencia.delete()
            messages.success(request, "Registro eliminado.")

            return redirect('asistenciasff')

        # B. GUARDAR / EDITAR
        try:
            asistencia_id = request.POST.get('asistencia_id')
            empleado_id = request.POST.get('empleado')
            empleado_obj = get_object_or_404(Empleado, id=empleado_id)
            fecha_captura = request.POST.get('fecha')
            fecha_dt = datetime.strptime(fecha_captura, '%Y-%m-%d').date()

            #if fecha_dt < limite_bloqueo:
                #messages.error(request, "Periodo cerrado.")
                #return redirect('asistenciasff')

            puesto_sel = (request.POST.get('puesto') or "").strip()
            puesto_up = puesto_sel.upper()
            estatus_jornada = request.POST.get('estatus_jornada')
            ent_m = (request.POST.get('entrada_matutina') or "").strip().upper()
            sal_m = (request.POST.get('salida_matutina') or "").strip().upper()
            ent_v = (request.POST.get('entrada_vespertina') or "").strip().upper()
            sal_v = (request.POST.get('salida_vespertina') or "").strip().upper()

            id_excluir = int(asistencia_id) if (asistencia_id and asistencia_id.isdigit()) else -1
            base_puesto = float(puestos_salarios_ff.get(puesto_sel, 0.0))

            # 1. DETERMINAR DIVISOR DE JORNADA
            if any(x in puesto_up for x in ["12 HORAS", "GERENTE", "FIN DE SEMANA"]):
                divisor = 12.0
            elif any(x in puesto_up for x in ["9 HORAS", "9HRS", "CREPAS", "INTERMEDIO", "CHEF"]):
                divisor = 9.0
            else:
                divisor = 6.0

            if "LIMPIEZA" in puesto_up and "9" in puesto_up:
                divisor = 9.0

            # 2. LÓGICA DE RETARDOS Y ASISTENCIAS SEMANALES
            inicio_sem = fecha_dt - timedelta(days=fecha_dt.weekday())
            fin_sem = inicio_sem + timedelta(days=6)
            asistencias_semana = Asistencia.objects.filter(
                empleado=empleado_obj, 
                fecha__range=[inicio_sem, fin_sem]
            ).exclude(id=id_excluir)
            
            # --- NUEVA LÓGICA DE PESOS ---
            puntos_previos = 0
            for reg in asistencias_semana:
                # Sumamos lo que ya estaba guardado en 'horas' de los días anteriores
                puntos_previos += int(reg.horas or 0)
            
            # Calculamos los puntos de HOY
            # R1 = 1 punto, R2 = 2 puntos
            puntos_hoy = 0
            for marca in [ent_m, ent_v]:
                if 'R1' in marca: puntos_hoy += 1
                if 'R2' in marca: puntos_hoy += 2
            
            total_puntos_semana = puntos_previos + puntos_hoy
            desc_retardo = 0.0
            
            # Cálculo del descuento de HOY basado en los puntos que aporta hoy
            # Si hoy entró un R2, sumamos (base/2) * 1 (o *2 si hubo R2 en ambas vueltas)
            r2_hoy_count = (1 if 'R2' in ent_m else 0) + (1 if 'R2' in ent_v else 0)
            if r2_hoy_count > 0:
                desc_retardo += (base_puesto / 2) * r2_hoy_count
            
            # Lógica de pares para R1 (Solo descuenta si se completa un nuevo par)
            r1_hoy_count = (1 if 'R1' in ent_m else 0) + (1 if 'R1' in ent_v else 0)
            if r1_hoy_count > 0:
                # Contamos cuántos R1 había antes (esto requiere filtrar los previos)
                r1_previos = 0
                for reg in asistencias_semana:
                    # Buscamos físicamente la cadena R1 en registros pasados
                    if reg.entrada_matutina and 'R1' in reg.entrada_matutina.upper(): r1_previos += 1
                    if reg.entrada_vespertina and 'R1' in reg.entrada_vespertina.upper(): r1_previos += 1
                
                total_r1_solo_semana = r1_previos + r1_hoy_count
                pares_viejos = r1_previos // 2
                pares_nuevos = total_r1_solo_semana // 2
                if pares_nuevos > pares_viejos:
                    desc_retardo += (base_puesto / 2) * (pares_nuevos - pares_viejos)

            # 3. LÓGICA DE MONTO CALC (PAGO BASE)
            monto_calc = 0.0
            
            if estatus_jornada in ["Falta", "Permiso", "Vacaciones"]:
                monto_calc = 0.0
                
            # --- BUSCA ESTA PARTE ---
            elif estatus_jornada == "Descanso":
                # Simplemente lo dejamos en 0.0
                # La lógica de pago (faltas, puesto recurrente, etc.) 
                # se ejecutará en la sección de nómina.
                monto_calc = 0.0


            # --- NUEVA CORRECCIÓN: Puestos de Monto Fijo ---
            elif any(x in puesto_up for x in ["PRODUCCION", "AUX PRODUCCION"]):
                monto_calc = base_puesto # Se toma directo de la DB sin validar horas

            elif "HAMBURGUESAS FF" in puesto_up:
                # Pago por producción (Cargas)
                c_ff = float(request.POST.get('cantidad_cargas') or 0)
                c_mom = float(request.POST.get('cantidad_cargas_momias') or 0)
                monto_calc = (c_ff * 62.00) + (c_mom * 51.50)

            else:
                # Lógica normal por tiempo
                entrada_final = ent_m if ent_m else ent_v
                salida_final = sal_v if sal_v else sal_m

                if entrada_final and salida_final:
                    monto_calc = obtener_monto_bloque(base_puesto, entrada_final, salida_final, divisor)
                else:
                    # Si el puesto tiene sueldo base pero no hay marcas, se puede pagar el base 
                    # o dejar en 0 según tu política. Aquí se mantiene 0 si no hay marcas.
                    monto_calc = 0.0

            # Aplicar pago doble si corresponde
            if estatus_jornada in ["Descanso trabajado", "Festivo"]:
                monto_calc *= 2.0

            # 4. GUARDAR REGISTRO
            bono = float(request.POST.get('bonificacion') or 0)
            desc_man = float(request.POST.get('descuento') or 0)

            asistencia = get_object_or_404(Asistencia, id=id_excluir) if id_excluir != -1 else Asistencia(sucursal="FastFood")
            asistencia.empleado, asistencia.fecha, asistencia.estatus, asistencia.puesto = empleado_obj, fecha_dt, estatus_jornada, puesto_sel
            asistencia.entrada_matutina, asistencia.salida_matutina = ent_m, sal_m
            asistencia.entrada_vespertina, asistencia.salida_vespertina = ent_v, sal_v
            asistencia.cantidad_cargas = float(request.POST.get('cantidad_cargas') or 0)
            asistencia.cantidad_cargas_momias = float(request.POST.get('cantidad_cargas_momias') or 0)
            
            # Guardamos bono y descuento en sus campos, pero NO los restamos de pago_dia
            asistencia.bonificacion = bono
            asistencia.descuento = desc_man

            # PAGO FINAL: Ahora solo guarda el monto calculado por el tiempo/puesto (sueldo bruto base)
            # El sistema de nómina sumará los pago_dia y luego aplicará bonos/descuentos una sola vez.
            asistencia.pago_dia = round(max(0, monto_calc), 2)
            
            # Guardamos el total de puntos de retardo (R1/R2) en 'horas' para auditoría
            asistencia.horas = float(puntos_hoy)
            asistencia.observaciones = request.POST.get('observaciones', '').strip()
            asistencia.save()
            
            messages.success(request, "Registro guardado correctamente.")
            return redirect('asistenciasff')

        except Exception as e:
            messages.error(request, f"❌ Error: {e}")
            return redirect('asistenciasff')

    # --- GET ---
    fecha_filtro = request.GET.get('fecha_filtro', '').strip()
    query = request.GET.get('q', '').strip()

    registros_qs = Asistencia.objects.filter(sucursal="FastFood")

    if fecha_filtro:
        registros_qs = registros_qs.filter(fecha=fecha_filtro)

    if query:
        palabras = query.split()
        q_bus = Q()

        for p in palabras:
            q_bus &= (
                Q(empleado__nombre__icontains=p) |
                Q(empleado__apellido_paterno__icontains=p) |
                Q(empleado__apellido_materno__icontains=p) |
                Q(empleado__codigo_empleado__icontains=p)
            )

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
        'anio_actual': anio_actual,
        'limite_bloqueo': limite_bloqueo,
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
def actualizar_pago_manual(request):
    if request.method == "POST":
        asistencia_id = request.POST.get('id')
        
        # Obtenemos los 3 valores que enviamos desde el JS
        nuevos_turnos = request.POST.get('turnos')
        nuevas_horas = request.POST.get('horas')
        nuevo_pago = request.POST.get('monto') # Cambiado de 'pago' a 'monto' para coincidir con el JS
        
        asistencia = get_object_or_404(Asistencia, id=asistencia_id)
        
        try:
            # Actualizamos todos los campos
            if nuevos_turnos is not None:
                asistencia.cantidad_turnos = float(nuevos_turnos)
            
            if nuevas_horas is not None:
                asistencia.total_horas = float(nuevas_horas)
                
            if nuevo_pago is not None:
                asistencia.pago_dia = float(nuevo_pago)
            
            asistencia.save()
            
            return JsonResponse({'status': 'ok', 'message': 'Datos actualizados correctamente'})
        
        except (ValueError, TypeError) as e:
            return JsonResponse({'status': 'error', 'message': 'Datos inválidos'}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

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
        "TURNO INTERMEDIO": 354.50,
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

        # ... (dentro de calcular_nomina_web, después de obtener intervalos_semanas)

        for sem_inicio, sem_fin in intervalos_semanas:
            # 1. Filtro base por fechas
            filtros_asistencia = Q(fecha__range=[sem_inicio, sem_fin])
        
            # 2. Filtro de Sucursales (Múltiple)
            sucursales_seleccionadas = request.GET.getlist('sucursal')
            if sucursales_seleccionadas and "TODAS" not in sucursales_seleccionadas:
                filtros_asistencia &= Q(sucursal__in=sucursales_seleccionadas)
        
            # 3. Inicializar el QuerySet
            asistencias_query = Asistencia.objects.filter(filtros_asistencia)
        
            # 4. Aplicar Filtro de Nombre si existe
            if nombre_filtro:
                # Creamos una anotación para poder buscar por nombre completo (Nombre + Apellidos)
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
        
            # 5. Obtener los IDs únicos de empleados que tuvieron asistencia bajo esos filtros
            empleados_ids = asistencias_query.values_list('empleado_id', flat=True).distinct()

            # ... resto de tu lógica para procesar empleados_ids
            for emp_id in empleados_ids:

                empleado = Empleado.objects.get(id=emp_id)

                asistencias = Asistencia.objects.filter(filtros_asistencia, empleado=empleado).order_by('fecha')

                # --- LÓGICA DE DESCANSO CORREGIDA: DETECCIÓN DE 6 DÍAS DOBLES ---

                asistencias_trabajadas = [

                    a for a in asistencias 

                    if a.puesto and "DESCANSO" not in (a.estatus or "").upper() and "FALTA" not in (a.estatus or "").upper()

                ]

                if asistencias_trabajadas:

                    total_dias_trabajados = len(asistencias_trabajadas)

                    conteo_puestos = Counter([a.puesto for a in asistencias_trabajadas])
                    

                    dias_completos = 0

                    # 1. Contar cuántos días trabajó REALMENTE jornada doble

                    for a in asistencias_trabajadas:

                        puesto_str = (a.puesto or "").upper()

                        # --- NUEVA LÓGICA DE EXCEPCIONES ---

                        puestos_turno_unico = ["TURNO INTERMEDIO", "FIN DE SEMANA", "CREPAS", "PRODUCCION","BENNY"]

                        es_excepcion_turno = any(x in puesto_str for x in puestos_turno_unico) or "GERENTE" in puesto_str

                        # ----------------------------------

                        tiene_m = a.entrada_matutina and str(a.entrada_matutina).strip() != ""

                        tiene_sv = a.salida_vespertina and str(a.salida_vespertina).strip() != ""

                        tiene_ev = a.entrada_vespertina and str(a.entrada_vespertina).strip() != ""

                        es_12h_gerente = "12 HORAS" in puesto_str or "GERENTE" in puesto_str

                        # Agregamos "and not es_excepcion_turno" al final de la condición

                        if ((tiene_m and (tiene_sv or tiene_ev)) or es_12h_gerente) and not es_excepcion_turno:

                            dias_completos += 1

                    # 2. Determinar el salario de un solo turno (promedio de lo que trabajó)

                    salario_un_turno_promedio = sum((puestos_salarios.get(p, 0) * (c / total_dias_trabajados)) 

                                               for p, c in conteo_puestos.items())

                    # 2. Determinar el salario del descanso según recurrencia o proporción
                    puestos_ordenados = conteo_puestos.most_common()
                    
                    es_dual = False
                    datos_duales = {}
                    
                    if len(puestos_ordenados) == 2 and puestos_ordenados[0][1] == 3 and puestos_ordenados[1][1] == 3:
                        puesto_a, cant_a = puestos_ordenados[0]
                        puesto_b, cant_b = puestos_ordenados[1]
                        salario_a = float(puestos_salarios.get(puesto_a, 0))
                        salario_b = float(puestos_salarios.get(puesto_b, 0))
                        
                        salario_un_turno_promedio = (salario_a / 2) + (salario_b / 2)
                        puesto_frecuente = f"{puesto_a}/{puesto_b}"
                        
                        # Guardamos los datos para el desglose de turnos
                        es_dual = True
                        datos_duales = {
                            'puesto_a': puesto_a,
                            'puesto_b': puesto_b,
                            'valor_turno': 0.5
                        }
                    
                    else:
                        # Regla General: El puesto más recurrente
                        puesto_frecuente = puestos_ordenados[0][0]
                        salario_un_turno_promedio = float(puestos_salarios.get(puesto_frecuente, 0))

                    # 3. Aplicar multiplicador si cumplió los 6 días dobles
                    if dias_completos >= 6:
                        salario_descanso = salario_un_turno_promedio * 2
                        puesto_principal = f"{puesto_frecuente} (Doble)"
                    else:
                        salario_descanso = salario_un_turno_promedio
                        puesto_principal = puesto_frecuente

                    # --- AGREGAR ESTA CORRECCIÓN FINAL ---
                    if "GERENTE" in puesto_principal.upper():
                        salario_descanso = float(puestos_salarios.get(puesto_frecuente, 600.00))
                        puesto_principal = puesto_frecuente # Quitamos el label "(Doble)" si existiera

                else:

                    salario_descanso = float(empleado.sueldo_base or 0)

                    puesto_principal = "Sin Puesto"

                # --- PRE-CALCULO DE RETARDOS Y LÓGICA DE PAGO ÚNICO ---

                lista_detalles_asistencia = []

                total_retardos_semanales = 0

                descanso_pagado = False  # Bandera para pago único

                # Verificar si el empleado tiene CUALQUIER falta en esta semana

                tiene_falta_en_semana = asistencias.filter(estatus__icontains="FALTA").exists()

                for reg in asistencias:

                    estatus_limpio = (reg.estatus or "").upper()

                    salario_base_puesto = puestos_salarios.get(reg.puesto, empleado.sueldo_base or 0)

                    base_calc = float(salario_base_puesto)

                    # Ajuste de base_calc para cálculos de retardo según jornada

                    if "(9 horas)" in (reg.puesto or ""): 

                        base_calc /= 1.5

                    elif "(12 Horas)" in (reg.puesto or "") or "GERENTE" in (reg.puesto or "").upper(): 

                        base_calc /= 2

                    # Lógica de pago de descanso

                    # ... dentro del for reg in asistencias ...

                    # 1. Detectar si es una excepción de pago fijo
                    pue_up = (reg.puesto or "").upper()
                    puestos_pago_fijo = ["TURNO INTERMEDIO", "FIN DE SEMANA", "CREPAS", "RAPPI", "9 HORAS","BENNY"]
                    es_pago_fijo = any(x in pue_up for x in puestos_pago_fijo)
                    
                    if "DESCANSO" in estatus_limpio and "TRABAJADO" not in estatus_limpio:
                        # (Tu lógica de descanso se queda igual...)
                        if not tiene_falta_en_semana and not descanso_pagado:
                            salario_dia = salario_descanso
                            descanso_pagado = True
                        else:
                            salario_dia = 0.0
                    
                    # --- BUSCA ESTE BLOQUE Y REEMPLÁZALO ---
                    elif es_pago_fijo:
                        retardo_dia = int(reg.horas or 0)
                        # PRIORIDAD: Si hay un pago_dia manual en la DB, lo usamos sin recalcular
                        if reg.pago_dia and float(reg.pago_dia) > 0:
                            salario_dia = float(reg.pago_dia)
                        else:
                            salario_dia = base_calc
                            
                    elif reg.pago_dia and float(reg.pago_dia) > 0:
                        # Si el usuario editó el campo, respetamos ese valor manual
                        retardo_dia = int(reg.horas or 0)
                        salario_dia = float(reg.pago_dia)
                    else:
                        # Solo si no hay valor manual, calculamos por tiempo
                        salario_dia, retardo_aut = calcular_pago_dia_final(base_calc, reg)
                        retardo_dia = int(reg.horas) if reg.horas else retardo_aut

                    if "DESCANSO TRABAJADO" in estatus_limpio or "FESTIVO" in estatus_limpio:
                        # Usamos la base del puesto original (base_calc) para evitar 
                        # arrastrar el multiplicador de la lógica de "6 días dobles"
                        salario_dia = base_calc * 2

                    if retardo_dia > 0: 

                        total_retardos_semanales += 1

                    lista_detalles_asistencia.append({

                        'reg': reg, 

                        'retardo_dia': retardo_dia, 

                        'salario_dia': salario_dia,

                        'salario_puesto_full': base_calc, 

                        'estatus': estatus_limpio
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

                    # --- BLOQUE DE RETARDOS UNIFICADO ---
                    if retardo_dia > 0:
                        # Obtenemos el factor de la tabla FACTORES (0.5, 1.0, 1.5, etc.)
                        factor_anterior = FACTORES.get(min(total_retardos_acumulados, 12), 3.0)
                        total_retardos_acumulados += retardo_dia
                        factor_actual = FACTORES.get(min(total_retardos_acumulados, 12), 3.0)
                        
                        diferencia_factor = factor_actual - factor_anterior
                        
                        # IMPORTANTE: base_descuento debe ser el salario de una jornada completa del empleado
                        # Si un Gerente gana 600, el descuento de 0.5 debe ser 300.
                        base_descuento = float(salario_base_puesto) 
                        
                        desc_retardo_dia = diferencia_factor * base_descuento
                    
                    # --- AQUÍ TERMINA EL BLOQUE DE RETARDOS ---
                    # (Asegúrate de haber borrado el "if es_jornada_completa" que tenías abajo)

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

                    # --- LÓGICA DE TURNOS PROPORCIONALES (CORREGIDA PARA PUESTOS ÚNICOS) ---
                    pue_up = (reg.puesto or "").upper()
                    puestos_turno_unico = ["TURNO INTERMEDIO", "FIN DE SEMANA", "CREPAS", "RAPPI", "9 HORAS", "PRODUCCION", "GERENTE","BENNY"]
                    es_excepcion_turno = any(x in pue_up for x in puestos_turno_unico)
                    
                    # 1. Obtenemos marcas de tiempo
                    m_ent_m, _ = procesar_dato_hibrido(reg.entrada_matutina, True, 'M')
                    m_sal_m, _ = procesar_dato_hibrido(reg.salida_matutina, False, 'M')
                    m_ent_v, _ = procesar_dato_hibrido(reg.entrada_vespertina, True, 'V')
                    m_sal_v, _ = procesar_dato_hibrido(reg.salida_vespertina, False, 'V')
                    
                    # Recolectamos todas las marcas válidas para calcular el rango total del día
                    todas_las_marcas = [m for m in [m_ent_m, m_sal_m, m_ent_v, m_sal_v] if m is not None]
                    turnos_acumulados = 0.0
                    
                    # 2. Definimos el divisor de horas según el puesto (El "1.0")
                    # Por defecto son 6 horas (360 min)
                    divisor_puesto = 360.0 
                    
                    if "FIN DE SEMANA" in pue_up or "GERENTE" in pue_up or "12 HORAS" in pue_up:
                        divisor_puesto = 720.0  # Su 100% son 12 horas
                    elif "9 HORAS" in pue_up or "INTERMEDIO" in pue_up:
                        divisor_puesto = 540.0  # Su 100% son 9 horas
                    
                    # 3. Cálculo de la proporción
                    if todas_las_marcas:
                        # Si es un puesto de turno único, no sumamos bloques, medimos el TIEMPO TOTAL transcurrido
                        if es_excepcion_turno:
                            if len(todas_las_marcas) >= 2:
                                # Diferencia entre la salida más tarde y la entrada más temprana
                                minutos_totales = max(todas_las_marcas) - min(todas_las_marcas)
                                if minutos_totales < 0: minutos_totales += 1440
                                
                                # Esto forzará que 9:30am a 9:30pm (720 min) / 720 = 1.0
                                # Y que 9:30am a 3:30pm (360 min) / 720 = 0.5
                                turnos_acumulados = minutos_totales / divisor_puesto
                            else:
                                # Si solo hay una marca (ej. "NORMAL" o solo entrada), contamos el turno completo
                                turnos_acumulados = 1.0
                        else:
                            # Lógica para puestos normales (6 horas) que sí pueden sumar bloques separados
                            # Mantenemos tu lógica anterior o usamos el proporcional simple
                            if m_ent_m and m_sal_m:
                                turnos_acumulados += (m_sal_m - m_ent_m) / 360.0
                            elif m_ent_m or m_sal_m:
                                turnos_acumulados += 0.5 # Media jornada si solo hay una marca en matutino
                                
                            if m_ent_v and m_sal_v:
                                turnos_acumulados += (m_sal_v - m_ent_v) / 360.0
                            elif m_ent_v or m_sal_v:
                                turnos_acumulados += 0.5
                    
                    elif es_excepcion_turno:
                        # Si no hay marcas pero tiene el puesto, le damos 1 por defecto (si el estatus es correcto)
                        turnos_acumulados = 1.0
                    
                    # --- MULTIPLICADOR POR DÍA ESPECIAL ---
                    if "TRABAJADO" in estatus_limpio or "FESTIVO" in estatus_limpio:
                        turnos_acumulados *= 2
                    
                    # Limitar a máximo 1 turno si no es descanso trabajado/festivo en excepciones
                    if es_excepcion_turno and not ("DESCANSO TRABAJADO" in estatus_limpio or "FESTIVO" in estatus_limpio):
                        turnos_acumulados = min(turnos_acumulados, 1.0)
                    
                    # Formateo final
                    valor_num = round(turnos_acumulados, 2)
                    cantidad_turnos = int(valor_num) if valor_num % 1 == 0 else valor_num

                    # ... (dentro de tu lógica de turnos proporcionales)
                    minutos_para_mostrar = 0
                    if todas_las_marcas:
                        if es_excepcion_turno:
                            if len(todas_las_marcas) >= 2:
                                minutos_para_mostrar = max(todas_las_marcas) - min(todas_las_marcas)
                                if minutos_para_mostrar < 0: minutos_para_mostrar += 1440
                            else:
                                # Si es normal o solo una marca, asumimos las horas base del puesto
                                minutos_para_mostrar = int(divisor_puesto)
                        else:
                            # Puestos de 6 horas sumando bloques
                            m_calc = 0
                            if m_ent_m and m_sal_m: m_calc += (m_sal_m - m_ent_m)
                            elif m_ent_m or m_sal_m: m_calc += 180 # 3h por marca única
                            if m_ent_v and m_sal_v: m_calc += (m_sal_v - m_ent_v)
                            elif m_ent_v or m_sal_v: m_calc += 180
                            minutos_para_mostrar = m_calc
                    
                    # Convertir minutos a formato HH:MM
                    horas_display = f"{int(minutos_para_mostrar // 60)}h {int(minutos_para_mostrar % 60)}m"

                    dias_map[nombre_dia].append({

                        'total_horas': horas_display, # NUEVO CAMPO

                        'fecha_dia': fecha_str,

                        'puesto': reg.puesto or '---',

                        'sucursal': reg.sucursal or '---',

                        'pago_dia': round(salario_dia, 2),

                        'descuento_retardo': round(desc_retardo_dia, 2),

                        'monto_bono': float(reg.bonificacion or 0),

                        'motivo_bono': reg.motivo_bonificacion,

                        'monto_descuento': float(reg.descuento or 0),

                        'motivo_descuento': reg.motivo_descuento,

                        'estatus': item['estatus'],

                        'cantidad_turnos': cantidad_turnos # Ahora usará el valor corregido

                    })

                # --- FUERA DEL FOR REG, DENTRO DEL FOR EMP_ID ---
                total_uniforme = DESCUENTO_UNIFORME_SEMANAL if aplica_uniforme_semanal else 0.0

                # El total neto debe ser: (Base + Bonos) - (Manuales + Retardos + Uniforme)

                total_neto = (pago_base_total + total_bonos) - (total_descuentos_manuales + total_desc_retardos_semanal + total_uniforme)

                motivos_bonos_semana = [

                    reg.motivo_bonificacion 

                    for reg in asistencias 

                    if reg.motivo_bonificacion and reg.motivo_bonificacion.strip()

                ]

                motivo_bono_texto = ", ".join(motivos_bonos_semana) if motivos_bonos_semana else ""

                # Corregimos también los motivos de descuentos manuales para que no se pierdan

                motivos_desc_semana = [

                    reg.motivo_descuento 

                    for reg in asistencias 

                    if reg.motivo_descuento and reg.motivo_descuento.strip()

                ]

                motivo_desc_texto = ", ".join(motivos_desc_semana) if motivos_desc_semana else ""

                resultados_nomina.append({

                    'nombre': f"{empleado.nombre} {empleado.apellido_paterno}",

                    'puesto_principal': puesto_principal,

                    'periodo_info': f"{sem_inicio.strftime('%d/%m')} al {sem_fin.strftime('%d/%m')}",

                    'dias': [dias_map[d] for d in dias_semana_esp],

                    'pago_base': round(pago_base_total, 2),

                    'retardos': total_retardos,

                    'desc_retardos': round(total_desc_retardos_semanal, 2), 

                    'bonos': round(total_bonos, 2),

                    'motivo_bonificacion': motivo_bono_texto,

                    # IMPORTANTE: Aquí solo mandamos el acumulado manual, 

                    # ya no referenciamos a 'reg.descuento' que causaba confusión

                    'descuentos': round(total_descuentos_manuales, 2),

                    'motivo_descuento': motivo_desc_texto,

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

    from django.db.models import Q, Value, CharField

    from django.db.models.functions import Concat, Coalesce



    puestos_salarios = {

        "Gerente (12 Horas)": 600.00, "Chef de Línea (9 horas)": 531.57,

        "Encargado Cocina (Matutino 6 horas)": 252.00, "Encargado Cocina (Matutino 9 horas)": 378.00,

        "Encargado Cocina (Matutino 12 horas)": 504.00, "Encargado de Cocina (12 horas)": 519.00,

        "Cocina y Barra (6 hrs)": 236.50, "Cocina y Barra (9 hrs)": 354.50,

        "Caja (6 horas)": 248.00, "Caja (9 horas)": 354.50,

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

        "TURNO INTERMEDIO": 354.50,

        "Gerente (12 horas)": 600.00,

        "Chef de Línea (9 horas)": 531.57,

        "Encargado Cocina (Matutino 6 horas)": 252.00,

        "Crepas": 354.50,

        "Hamburguesas FF": 0.0,

    }



    datos_completos = []

    filtros_base = Q(fecha__range=[inicio, fin])



    # 1. Filtro de Sucursal (mejorado para soportar lista o string único)

    if sucursal_sel and sucursal_sel != "TODAS":

        if isinstance(sucursal_sel, list):

            filtros_base &= Q(sucursal__in=sucursal_sel)

        else:

            filtros_base &= Q(sucursal__iexact=sucursal_sel)



    # 2. Lógica de filtrado por nombre idéntica a Reportes

    asistencias_query = Asistencia.objects.filter(filtros_base)



    if nombre_busqueda:

        # 1. Primero anotamos el nombre completo para poder buscar en él

        asistencias_query = asistencias_query.annotate(

            full_name=Concat(

                'empleado__nombre', Value(' '), 

                Coalesce('empleado__apellido_paterno', Value('')), Value(' '), 

                Coalesce('empleado__apellido_materno', Value('')),

                output_field=CharField()

            )

        )

        

        # 2. Dividimos la búsqueda en palabras (igual que en Asistencias)

        palabras = nombre_busqueda.split()

        q_bus = Q()



        for p in palabras:

            # Cada palabra debe coincidir en alguno de estos campos (AND lógico entre palabras)

            q_bus &= (

                Q(full_name__icontains=p) | 

                Q(empleado__nombre__icontains=p) | 

                Q(empleado__apellido_paterno__icontains=p) | 

                Q(empleado__codigo_empleado__icontains=p)

            )

        

        asistencias_query = asistencias_query.filter(q_bus).distinct()



    # Obtenemos los IDs basados en el QuerySet ya filtrado

    empleados_ids = asistencias_query.values_list('empleado_id', flat=True).distinct()



    # Optimizamos la consulta de empleados usando select_related en el bucle

    for emp_id in empleados_ids:

        # Usamos select_related para evitar consultas extra por cada registro de asistencia

        asistencias = (

            Asistencia.objects

            .filter(filtros_base, empleado_id=emp_id)

            .select_related('empleado')

            .order_by('fecha')

        )

        

        if not asistencias.exists():

            continue

            

        empleado = asistencias[0].empleado # Obtenemos el objeto empleado del primer registro



        puestos_lista = [a.puesto for a in asistencias if a.puesto]



        puesto_principal = (

            Counter(puestos_lista).most_common(1)[0][0]

            if puestos_lista else "Sin Puesto"

        )



        # --- LÓGICA DE APOYO: CONTEO DE DÍAS DOBLES EN LA SEMANA ---

        dias_completos_semana = 0

        for a in asistencias:

            p_str = (a.puesto or "").upper()

            est = (a.estatus or "").upper()

            

            # Saltamos descansos y faltas para el conteo de días trabajados

            if "DESCANSO" in est or "FALTA" in est:

                continue

            

            # Verificación robusta de celdas con datos

            tiene_m = a.entrada_matutina and str(a.entrada_matutina).strip() != ""

            tiene_v = a.entrada_vespertina and str(a.entrada_vespertina).strip() != ""

            

            # Se considera día doble si tiene ambos bloques o es puesto de 12h/Gerente

            if (tiene_m and tiene_v) or "12 HORAS" in p_str or "GERENTE" in p_str:

                dias_completos_semana += 1



        pago_base_acumulado = 0

        total_retardos = 0

        total_bonos = 0

        total_descuentos_manuales = 0

        total_descuento_retardos_acumulado = 0



        dias_semana_esp = [

            "Lunes", "Martes", "Miércoles",

            "Jueves", "Viernes", "Sábado", "Domingo"

        ]



        dias_map = {

            d: {

                'horas': 0,

                'estatus': '---',

                'sucursal': '',

                'puesto': '',

                'pago_dia': 0,

                'descuento_aplicado': 0,

                'descuento_retardo': 0

            }

            for d in dias_semana_esp

        }

        for reg in asistencias:

            sueldo_base_puesto_dia = float(

                puestos_salarios.get(reg.puesto, empleado.sueldo_base or 0)

            )



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

                pago_final_dia = salario_dia_calculado * 2

            elif "DESCANSO" in estatus_limpio:

                # El descanso se paga según el puesto que más hizo en la semana

                sueldo_puesto_top = float(puestos_salarios.get(puesto_principal, empleado.sueldo_base or 0))

                

                if dias_completos_semana >= 6:

                    pago_final_dia = sueldo_puesto_top * 2

                else:

                    pago_final_dia = sueldo_puesto_top



            horas_retardo = int(reg.horas or 0)



            desc_retardo_dia = (

                (sueldo_base_puesto_dia / 6) * horas_retardo

                if "DESCANSO" not in estatus_limpio else 0

            )



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



        total_neto = (

            (pago_base_acumulado + total_bonos) -

            (total_descuentos_manuales + total_descuento_retardos_acumulado + cuota_uniforme)

        )



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

# --- Función Auxiliar (Asegúrate de tenerla definida o pégala antes de la vista) ---
def procesar_dato_hibrido(dato, es_entrada=True, turno='M'):
    if not dato or str(dato).strip() == "":
        return None, None
    try:
        # Si ya es un objeto time o datetime
        import datetime
        if isinstance(dato, (datetime.time, datetime.datetime)):
            return dato.hour * 60 + dato.minute, dato
        
        # Si es un string (ej: "08:00")
        h, m = map(int, str(dato).split(':'))
        return h * 60 + m, dato
    except:
        return None, None
        
@login_required
def vista_reportes(request):
    empleados_qs = Empleado.objects.filter(estatus='Activo').order_by('nombre')

    query_nombre = request.GET.get('q', '').strip()
    
    # --- CAMBIO: Captura de múltiples sucursales ---
    sucursales_seleccionadas = request.GET.getlist('sucursal')
    # -----------------------------------------------
    
    f_inicio = request.GET.get('fecha_inicio')
    f_fin = request.GET.get('fecha_fin')

    puestos_salarios = {
        "Gerente (12 Horas)": 600.00,
        "Chef de Línea (9 horas)": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00,
        "Encargado Cocina (Matutino 9 horas)": 378.00,
        "Encargado Cocina (Matutino 12 horas)": 504.00,
        "Encargado de Cocina (12 horas)": 519.00,
        "Cocina y Barra (6 hrs)": 236.50,
        "Cocina y Barra (9 hrs)": 354.50,
        "Caja (6 horas)": 248.00,
        "Caja (9 horas)": 354.50,
        "Barra (6 horas) Entregas": 236.50,
        "Barra (9 horas) Entregas": 354.50,
        "Fin de Semana": 473.00,
        "Encargado Victoria (6 Horas)": 316.00,
        "Encargado Sucursales (6 Horas)": 262.00,
        "Encargado Sucursales (9 Horas)": 393.00,
        "Freidor (6 horas)": 248.00,
        "Freidor (9 horas)": 372.00,
        "Despacho (6 horas)": 236.50,
        "Despacho (9 horas)": 354.75,
        "Benny": 171.00,
        "Aderezos": 236.50,
        "Cocina": 248.00,
        "Fabrica": 236.50,
        "Perrioni": 236.50,
        "PP": 236.50,
        "Yommy": 236.50,
        "Rappi": 354.75,
        "Fabrica Crystal": 262.00,
        "PM": 236.50,
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
        "Aux Produccion": 177.00,
        "Produccion": 370.00,
        "TURNO MATUTINO (6 horas)": 236.50,
        "TURNO VESPERTINO (6 horas)": 236.50,
        "TURNO MATUTINO (9 horas)": 354.50,
        "TURNO VESPERTINO (9 horas)": 354.50,
        "TURNO FIN DE SEMANA": 473.00,
        "TURNO INTERMEDIO": 354.50,
        "Gerente (12 horas)": 600.00,
        "Chef de Línea (9 horas)": 531.57,
        "Crepas": 354.50,
        "Hamburguesas FF": 0.0,
    }
    agrupados_dict = {}
    resumen_sucursales_dict = {}
    resumen_global = {
        'total_pagar': 0, 
        'total_retardos': 0, 
        'total_bonif': 0, 
        'total_turnos': 0, 
        'total_descuentos': 0
    }

    if f_inicio and f_fin:
        asistencias_query = Asistencia.objects.filter(fecha__range=[f_inicio, f_fin]).order_by('fecha')

        # --- CAMBIO: Lógica de filtrado múltiple ---
        if sucursales_seleccionadas and "TODAS" not in sucursales_seleccionadas:
            asistencias_query = asistencias_query.filter(sucursal__in=sucursales_seleccionadas)
        # -------------------------------------------

        if query_nombre:
            asistencias_query = asistencias_query.annotate(
                full_name=Concat('empleado__nombre', Value(' '), 'empleado__apellido_paterno', Value(' '), 'empleado__apellido_materno', output_field=CharField())
            ).filter(
                Q(full_name__icontains=query_nombre) | 
                Q(empleado__nombre__icontains=query_nombre) | 
                Q(empleado__apellido_paterno__icontains=query_nombre) | 
                Q(empleado__codigo_empleado__icontains=query_nombre)
            )

        # 3. Agrupación inicial por empleado
        asistencias_por_emp = {}
        for a in asistencias_query:
            if a.empleado_id not in asistencias_por_emp:
                asistencias_por_emp[a.empleado_id] = []
            asistencias_por_emp[a.empleado_id].append(a)

        ids_con_falta = set(asistencias_query.filter(estatus__icontains="FALTA").values_list('empleado_id', flat=True))

        # 4. Procesamiento por empleado
        for emp_id, lista_asis in asistencias_por_emp.items():
            conteo_puestos = Counter()
            dias_dobles_count = 0
            
            # 1. Determinamos puestos trabajados
            for a in lista_asis:
                estatus_up = (a.estatus or "").strip().upper()
                if "DESCANSO" not in estatus_up and "FALTA" not in estatus_up:
                    pue = a.puesto or a.empleado.puesto or "GENERAL"
                    conteo_puestos[pue] += 1
                    
                    puesto_str = pue.upper()
                    es_excepcion_gerente = "GERENTE" in puesto_str
                    if (a.entrada_matutina and a.salida_matutina) and (a.entrada_vespertina and a.salida_vespertina) and not es_excepcion_gerente:
                        dias_dobles_count += 1

            # --- NUEVA LÓGICA DE DUALIDAD ---
            puestos_ordenados = conteo_puestos.most_common(2)
            es_dual = False
            puesto_a, puesto_b = None, None

            if len(puestos_ordenados) == 2 and puestos_ordenados[0][1] == 3 and puestos_ordenados[1][1] == 3:
                es_dual = True
                puesto_a = puestos_ordenados[0][0]
                puesto_b = puestos_ordenados[1][0]
                puesto_principal = f"{puesto_a}/{puesto_b}" # Referencia visual
            else:
                puesto_principal = puestos_ordenados[0][0] if puestos_ordenados else "GENERAL"
            # --------------------------------

            contador_retardos_emp = 0  
            FACTORES_NOMINA = {0: 0.0, 1: 0.0, 2: 0.5, 3: 0.5, 4: 1.0, 5: 1.0, 6: 1.5, 7: 1.5, 8: 2.0, 9: 2.0, 10: 2.5, 11: 2.5, 12: 3.0}

            for asis in lista_asis:
                emp = asis.empleado
                estatus_limpio = (asis.estatus or "").strip().upper()
                if "PERMISO" in estatus_limpio: continue
                
                es_descanso = "DESCANSO" in estatus_limpio
                es_falta = "FALTA" in estatus_limpio
                suc = asis.sucursal or "Victoria"

                # Si es descanso y es DUAL, procesamos dos "mini-filas" virtuales
                if es_descanso and es_dual and emp.id not in ids_con_falta:
                    # El multiplicador (por si es doble pago de descanso)
                    mult = 1.0 if dias_dobles_count < 6 else 2.0
                    
                    # Dividimos el descanso entre los dos puestos
                    for p_dual in [puesto_a, puesto_b]:
                        salario_dual = float(puestos_salarios.get(p_dual, emp.sueldo_base or 0))
                        # Si es gerente en esa dualidad, forzamos que el descanso no sea doble
                        turnos_dual = 0.5 * (1.0 if "GERENTE" in p_dual.upper() else mult)
                        
                        key_dual = (emp.id, suc, p_dual)
                        if key_dual not in agrupados_dict:
                            agrupados_dict[key_dual] = {
                                'empleado': f"{emp.nombre} {emp.apellido_paterno}".strip(),
                                'sucursal': suc, 'puesto': p_dual, 'total_turnos': 0.0,
                                'total_retardos': 0, 'minutos_totales': 0, 'monto_descuentos': 0.0,
                                'total_bonos': 0.0, 'total_fila': 0.0, 'motivos_descuentos': [], 'motivos_bonos': []
                            }
                        
                        fila_d = agrupados_dict[key_dual]
                        fila_d['total_turnos'] += turnos_dual
                        fila_d['total_fila'] += (salario_dual * turnos_dual)
                        
                        # Totales globales
                        resumen_global['total_turnos'] += turnos_dual
                        resumen_global['total_pagar'] += (salario_dual * turnos_dual)
                    
                    continue # Saltamos el proceso normal para este registro de descanso

                # --- PROCESO NORMAL PARA DÍAS TRABAJADOS O DESCANSOS NO DUALES ---
                if es_falta:
                    puesto_para_fila = "FALTA"
                else:
                    puesto_para_fila = puesto_principal if es_descanso else (asis.puesto or emp.puesto or "GENERAL")

                # (Aquí sigue tu lógica de salario_ref, valor_turno_base, etc...)
                salario_ref = float(puestos_salarios.get(puesto_para_fila, emp.sueldo_base or 0)) if not es_falta else 0.0
                pue_up = puesto_para_fila.upper()
                es_destajo = "TUPPERS" in pue_up or "HAMBURGUESAS FF" in pue_up
                valor_turno_base = salario_ref

                # ... (resto de tu lógica de turnos_a_sumar, pago_base_dia, retardos, etc.)

                # --- LÓGICA DE CONTEO DE TURNOS Y PAGO (CORREGIDA PARA REPORTES) ---
                turnos_a_sumar = 0.0
                pago_base_dia = 0.0

                if es_destajo and not es_descanso and not es_falta:
                    # Sumamos ambos tipos de cargas para el total de la columna 'Turnos'
                    cargas_ff = float(asis.cantidad_cargas or 0)
                    cargas_mom = float(asis.cantidad_cargas_momias or 0)
                    
                    turnos_a_sumar = cargas_ff + cargas_mom
                    
                    # El pago ya viene calculado de la DB o lo recalculas aquí:
                    if "HAMBURGUESAS FF" in pue_up:
                        pago_base_dia = (cargas_ff * 62.00) + (cargas_mom * 51.50)
                    else:
                        # Lógica para Tuppers u otros si aplica
                        pago_base_dia = turnos_a_sumar * 46.50

                elif es_descanso and "TRABAJADO" not in estatus_limpio:
                    if emp.id not in ids_con_falta:
                        # 1. CASO ESPECIAL: Tuppers y Hamburguesas (Descanso de Destajo)
                        if "TUPPERS" in pue_up or "HAMBURGUESAS FF" in pue_up:
                            turnos_a_sumar = 1.0  # Se registra como 1 unidad de descanso
                            # Pago fijo por descanso para personal de destajo
                            pago_base_dia = 138.00 if "TUPPERS" in pue_up else valor_turno_base
                        
                        # 2. CASO GERENTE
                        elif "GERENTE" in pue_up:
                            turnos_a_sumar = 1.0
                            pago_base_dia = valor_turno_base * turnos_a_sumar
                            
                        # 3. LÓGICA ESTÁNDAR (Puestos por tiempo)
                        else:
                            turnos_a_sumar = 1.0 if dias_dobles_count < 6 else 2.0
                            pago_base_dia = valor_turno_base * turnos_a_sumar
                    else:
                        # Si tiene falta en la semana, no se paga el descanso
                        turnos_a_sumar = 0.0
                        pago_base_dia = 0.0

                elif not es_falta:
                    puestos_especiales = ["TURNO INTERMEDIO", "FIN DE SEMANA", "CREPAS", "RAPPI", "9 HORAS", "GERENTE", "PRODUCCION","BENNY"]
                    es_especial = any(x in pue_up for x in puestos_especiales)
                    
                    # --- CONFIGURACIÓN DE DIVISOR ---
                    divisor_puesto = 360.0  # Base 6 horas
                    if "FIN DE SEMANA" in pue_up or "GERENTE" in pue_up or "12 HORAS" in pue_up:
                        divisor_puesto = 720.0
                    elif "9 HORAS" in pue_up or "INTERMEDIO" in pue_up:
                        divisor_puesto = 540.0

                    # Obtención de marcas
                    m_ent_m, _ = procesar_dato_hibrido(asis.entrada_matutina, True, 'M')
                    m_sal_m, _ = procesar_dato_hibrido(asis.salida_matutina, False, 'M')
                    m_ent_v, _ = procesar_dato_hibrido(asis.entrada_vespertina, True, 'V')
                    m_sal_v, _ = procesar_dato_hibrido(asis.salida_vespertina, False, 'V')
                    
                    todas_marcas = [m for m in [m_ent_m, m_sal_m, m_ent_v, m_sal_v] if m is not None]

                    # --- LÓGICA DE CONTEO DE TURNOS Y PAGO CORREGIDA ---
                    if todas_marcas:
                        if es_especial:
                            # Lógica de RANGO UNIFICADO (Evita el "2" en jornadas de 12h)
                            if len(todas_marcas) >= 2:
                                diff = max(todas_marcas) - min(todas_marcas)
                                if diff < 0: diff += 1440
                                turnos_a_sumar = diff / divisor_puesto
                                minutos_asistencia = diff # Actualiza minutos para el display
                            else:
                                turnos_a_sumar = 1.0  # Una sola marca se toma como turno completo
                                minutos_asistencia = int(divisor_puesto)
                        else:
                            # Lógica estándar para turnos de 6h (sumar bloques independientes)
                            t_acum = 0.0
                            minutos_bloques = 0
                            if m_ent_m and m_sal_m: 
                                t_acum += (m_sal_m - m_ent_m) / 360.0
                                minutos_bloques += (m_sal_m - m_ent_m)
                            elif m_ent_m or m_sal_m: 
                                t_acum += 1.0 
                                minutos_bloques += 180 # 3h por marca única
                            
                            if m_ent_v and m_sal_v: 
                                t_acum += (m_sal_v - m_ent_v) / 360.0
                                minutos_bloques += (m_sal_v - m_ent_v)
                            elif m_ent_v or m_sal_v: 
                                t_acum += 1.0
                                minutos_bloques += 180
                            
                            turnos_a_sumar = t_acum
                            minutos_asistencia = minutos_bloques
                    else:
                        # --- CASO ESPECIAL: Benny o puestos sin marcas manuales ---
                        if es_especial:
                            turnos_a_sumar = 1.0
                            minutos_asistencia = int(divisor_puesto)
                        else:
                            turnos_a_sumar = 0.0
                            minutos_asistencia = 0

                    # --- LIMITAR A MÁXIMO 1 TURNO SI NO ES DÍA ESPECIAL ---
                    if es_especial and "TRABAJADO" not in estatus_limpio and "FESTIVO" not in estatus_limpio:
                        turnos_a_sumar = min(turnos_a_sumar, 1.0)

                    # Doble pago por laborar en día de descanso o festivo
                    if "TRABAJADO" in estatus_limpio or "FESTIVO" in estatus_limpio:
                        turnos_a_sumar *= 2
                    
                    pago_base_dia = (valor_turno_base * turnos_a_sumar)

                # Otros conceptos
                bono_dia = float(asis.bonificacion or 0)
                desc_manual = float(asis.descuento or 0)

                # Retardos
                puntos_retardo = int(float(asis.horas or 0))
                desc_retardo_monto = 0.0
                if puntos_retardo > 0 and not es_descanso and not es_falta:
                    f_ant = FACTORES_NOMINA.get(min(contador_retardos_emp, 12), 3.0)
                    contador_retardos_emp += puntos_retardo
                    f_act = FACTORES_NOMINA.get(min(contador_retardos_emp, 12), 3.0)
                    desc_retardo_monto = (f_act - f_ant) * valor_turno_base

                monto_desc_total = desc_manual + desc_retardo_monto
                pago_neto_dia = (pago_base_dia + bono_dia) - monto_desc_total

                # 1. --- NUEVO: CÁLCULO DE MINUTOS PARA ESTA ASISTENCIA ---
                minutos_asistencia = 0
                m_ent_m, _ = procesar_dato_hibrido(asis.entrada_matutina, True, 'M')
                m_sal_m, _ = procesar_dato_hibrido(asis.salida_matutina, False, 'M')
                m_ent_v, _ = procesar_dato_hibrido(asis.entrada_vespertina, True, 'V')
                m_sal_v, _ = procesar_dato_hibrido(asis.salida_vespertina, False, 'V')
                
                todas_marcas = [m for m in [m_ent_m, m_sal_m, m_ent_v, m_sal_v] if m is not None]

                if todas_marcas and not es_descanso and not es_falta:
                    pue_up = puesto_para_fila.upper()
                    # Puestos especiales (Rango unificado)
                    if any(x in pue_up for x in ["FIN DE SEMANA", "GERENTE", "12 HORAS", "9 HORAS", "INTERMEDIO"]):
                        if len(todas_marcas) >= 2:
                            diff = max(todas_marcas) - min(todas_marcas)
                            if diff < 0: diff += 1440
                            minutos_asistencia = diff
                        else:
                            minutos_asistencia = int(divisor_puesto) # Si hay 1 marca, asume jornada completa
                    else:
                        # Puestos estándar (Suma de bloques)
                        if m_ent_m and m_sal_m: minutos_asistencia += (m_sal_m - m_ent_m)
                        elif m_ent_m or m_sal_m: minutos_asistencia += 180 # 3h por marca única
                        if m_ent_v and m_sal_v: minutos_asistencia += (m_sal_v - m_ent_v)
                        elif m_ent_v or m_sal_v: minutos_asistencia += 180

                # Guardado en el diccionario agrupado
                key = (emp.id, suc, puesto_para_fila)
                if key not in agrupados_dict:
                    agrupados_dict[key] = {
                        'empleado': f"{emp.nombre} {emp.apellido_paterno}".strip(),
                        'sucursal': suc, 
                        'puesto': puesto_para_fila, 
                        'total_turnos': 0.0,
                        'total_retardos': 0,
                        'minutos_totales': 0, # <--- ACUMULADOR DE MINUTOS
                        'monto_descuentos': 0.0, 
                        'total_bonos': 0.0,
                        'total_fila': 0.0, 
                        'motivos_descuentos': [],
                        'motivos_bonos': []  # <--- NUEVO
                    }

                fila = agrupados_dict[key]
                fila['total_turnos'] += turnos_a_sumar
                fila['minutos_totales'] += minutos_asistencia # <--- SUMAR MINUTOS
                fila['total_retardos'] += puntos_retardo
                fila['total_bonos'] += bono_dia
                fila['monto_descuentos'] += monto_desc_total
                fila['total_fila'] += pago_neto_dia
                
                # --- Lógica de recolección de motivos ---
                # 1. Para Descuentos (ya lo tienes)
                if asis.motivo_descuento:
                    m_desc = str(asis.motivo_descuento).strip()
                    if m_desc and m_desc not in fila['motivos_descuentos']: 
                        fila['motivos_descuentos'].append(m_desc)
                
                # 2. Para Bonificaciones (ESTE ES EL QUE FALTA AGREGAR)
                if asis.motivo_bonificacion:
                    m_bono = str(asis.motivo_bonificacion).strip()
                    if m_bono and m_bono not in fila['motivos_bonos']: 
                        fila['motivos_bonos'].append(m_bono)

                # Totales Globales
                resumen_global['total_pagar'] += pago_neto_dia
                resumen_global['total_turnos'] += turnos_a_sumar
                resumen_global['total_retardos'] += puntos_retardo
                resumen_global['total_bonif'] += bono_dia
                resumen_global['total_descuentos'] += monto_desc_total
                resumen_sucursales_dict[suc] = resumen_sucursales_dict.get(suc, 0) + pago_neto_dia

    # 3. --- NUEVO: CONVERTIR MINUTOS A FORMATO HH:MM ANTES DE ENVIAR AL TEMPLATE ---
    for fila in agrupados_dict.values():
        m = fila['minutos_totales']
        fila['total_horas_display'] = f"{int(m // 60)}h {int(m % 60)}m"

    # Preparación de datos finales
    resumen_sucursales = [
        {'nombre': s, 'periodo': f"{f_inicio} al {f_fin}", 'total': round(t, 2)}
        for s, t in resumen_sucursales_dict.items()
    ]

    lista_agrupada = sorted(agrupados_dict.values(), key=lambda x: x['empleado'])
    

    context = {
        'empleados': empleados_qs,
        'agrupados': lista_agrupada,
        'resumen_sucursales': resumen_sucursales,
        'lista_sucursales': ["Momias 1", "Momias 2", "Momias 3", "Momias 4", "Momias 5", "Momias 6", "Fabrica", "Fabrica Crystal", "PP", "PM", "Area Seca", "Perrioni", "FastFood","Yommy","Cocina","Benny"],
        'fecha_inicio': f_inicio, 
        'fecha_fin': f_fin, 
        'query': query_nombre,
        # --- CAMBIO: Mandar las seleccionadas para que el template las marque ---
        'sucursales_seleccionadas': sucursales_seleccionadas,
        # -----------------------------------------------------------------------
        'gran_total_pagar': round(resumen_global['total_pagar'], 2),
        'gran_total_retardos': resumen_global['total_retardos'],
        'gran_total_bonos': round(resumen_global['total_bonif'], 2),
        'gran_total_descuentos': round(resumen_global['total_descuentos'], 2),
        'gran_total_turnos': round(resumen_global['total_turnos'], 2)
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
            # 1. LÓGICA DE ELIMINACIÓN
            puesto_a_borrar = request.POST.get('eliminar_puesto')
            if puesto_a_borrar:
                ConfigSueldo.objects.filter(puesto=puesto_a_borrar).delete()
                return redirect('gestion_sueldos')

            # 2. LÓGICA DE EDICIÓN / CREACIÓN
            puesto_editar = request.POST.get('puesto_nombre')
            puesto_nuevo = request.POST.get('nuevo_puesto_nombre')
            monto_raw = request.POST.get('nuevo_monto')
            
            try:
                monto = float(monto_raw) if monto_raw else 0.0
            except ValueError:
                monto = 0.0

            if puesto_editar:
                puesto_obj = ConfigSueldo.objects.filter(puesto=puesto_editar).first()
                if puesto_obj:
                    puesto_obj.monto = monto
                    puesto_obj.save()
                    # NUEVO: Guardar en Historial al editar
                    HistorialSueldo.objects.create(
                        puesto=puesto_editar,
                        monto=monto,
                        usuario=request.user # Registra quién cambió
                    )
            
            elif puesto_nuevo:
                if not ConfigSueldo.objects.filter(puesto=puesto_nuevo).exists():
                    ConfigSueldo.objects.create(puesto=puesto_nuevo, monto=monto)
                    # NUEVO: Guardar en Historial al crear nuevo
                    HistorialSueldo.objects.create(
                        puesto=puesto_nuevo,
                        monto=monto,
                        usuario=request.user
                    )

            return redirect('gestion_sueldos')

        # 3. LÓGICA GET (Carga de lista y Filtro Histórico)
        fecha_consulta = request.GET.get('fecha_consulta')
        
        if fecha_consulta:
            # LÓGICA DE "VIAJE EN EL TIEMPO":
            # Buscamos los registros en el historial hasta esa fecha.
            # Usamos distinct('puesto') para traer solo el último cambio de cada puesto.
            sueldos = HistorialSueldo.objects.filter(
                fecha_modificacion__date__lte=fecha_consulta
            ).order_by('puesto', '-fecha_modificacion').distinct('puesto')
        else:
            # Si no hay fecha, mostramos los sueldos actuales
            sueldos = ConfigSueldo.objects.all().order_by('puesto')

        return render(request, 'Wages.html', {
            'sueldos': sueldos,
            'fecha_consulta': fecha_consulta
        })

    except Exception as e:
        return HttpResponse(f"Error crítico en la vista: {e}", status=500)
