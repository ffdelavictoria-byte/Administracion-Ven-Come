from django.shortcuts import render, redirect, get_object_or_404
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
    # Si el usuario ya está logueado y entra al login, lo deslogueamos 
    # para forzar que use credenciales nuevas si quiere volver a entrar.
    if request.user.is_authenticated and request.method == 'GET':
        logout(request) 
    
    if request.method == 'POST':
        usuario_input = request.POST.get('username')
        clave_input = request.POST.get('password')
        
        # Esto busca en la tabla auth_user (donde está tu superusuario)
        user = authenticate(request, username=usuario_input, password=clave_input)
        
        if user is not None:
            login(request, user)
            return render(request,"Main_Content.html") # Redirige al name='main' de tus urls.py
        else:
            messages.error(request, "¡SANTO CIELO! Usuario o contraseña incorrectos.")
            
    return render(request, 'Login_View.html')

@login_required(login_url='login')
def Main_Content(request):
    # Solo entran usuarios autenticados
    return render(request, 'Main_Content.html')

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
    # ... [Tu diccionario puestos_salarios y funciones internas permanecen igual] ...
    puestos_salarios = {
        "Caja (6 horas)": 248.00, 
        "Caja Capacitacion": 236.50,
        "Freidor Capacitacion": 236.50,
        "Encargado Capacitacion": 248.00,
        "Encargado Victoria (6 Horas)": 316.00,
        "Encargado Sucursales (6 Horas)": 262.00,
        "Freidor (6 horas)": 248.00,
        "Despacho (6 horas)": 236.50,
        "Aderezos": 236.50,
        "Cocina": 248.00,
        "Fabrica": 236.50,
        "Perrioni": 236.50,
        "PP": 236.50,
        "PM": 236.50,
        "Yommy": 236.50,
        "Benny": 171.00,
        "Rappi": 354.75,
        "Fabrica Crystal": 262.00,
        "Hamburguesas Momias": 0.00, # Dinámico por cargas
        "Tuppers": 0.00,             # Dinámico por cargas
    }

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
        asistencia = get_object_or_404(Asistencia, id=request.POST.get('eliminar_id'))
        asistencia.delete()
        messages.success(request, "¡Registro eliminado!")
        return redirect('asistencias')

    # --- LÓGICA DE GUARDADO / MODIFICACIÓN ---
    if request.method == 'POST':
        try:
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
                # Lógica específica para puestos de destajo
                if puesto_seleccionado in ["Hamburguesas Momias", "Tuppers"]:
                    monto_final = DESCANSO_DESTAJO
                else:
                    monto_final = 0.0

            elif puesto_seleccionado == "Hamburguesas Momias":
                cargas = float(request.POST.get('cantidad_cargas') or 0)
                monto_final = cargas * 51.50
            
            elif puesto_seleccionado == "Tuppers":
                cargas = float(request.POST.get('cantidad_cargas') or 0)
                monto_final = cargas * 46.50

            else:
                # Lógica proporcional para puestos con horario
                salario_real = float(puestos_salarios.get(puesto_seleccionado, 0))
                
                # Normalizar a base 6h según el nombre del puesto
                base_6h = salario_real
                if "(9 horas)" in puesto_seleccionado or "(9 Horas)" in puesto_seleccionado:
                    base_6h = salario_real / 1.5
                elif "(12 Horas)" in puesto_seleccionado:
                    base_6h = salario_real / 2

                pago_m = obtener_monto_bloque(base_6h, ent_m, sal_m)
                pago_v = obtener_monto_bloque(base_6h, ent_v, sal_v)
                monto_final = pago_m + pago_v

            # 2. Puntos de Retardo (Referencia en campo horas)
            def calcular_puntos(valor):
                if not valor or ":" in valor or "R1" in valor: return 0
                mapping = {"R2": 1, "R3": 2, "R4": 3, "R5": 4, "R6": 5, "R7": 6, "R8": 7, "R9": 8, "R10": 9, "R11": 10, "R12": 11}
                for clave, pts in mapping.items():
                    if clave in valor.upper(): return pts
                return 0

            total_puntos = calcular_puntos(ent_m) + calcular_puntos(ent_v)

            # 3. Guardado en Base de Datos con Validación Estricta
            # 3. Guardado en Base de Datos con Lógica de Doble Turno
            fecha_captura = request.POST.get('fecha')
            empleado_obj = Empleado.objects.get(id=empleado_id)
            
            # Determinamos si el registro actual tiene datos matutinos o vespertinos
            # Consideramos que tiene turno si los campos NO están vacíos
            es_matutino = bool(ent_m and sal_m)
            es_vespertino = bool(ent_v and sal_v)

            # Buscamos duplicados específicos por turno
            asistencia_existente = None
            
            # Filtramos registros del mismo empleado y fecha
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
        

            # --- 3. LÓGICA GET (MOMIAS) ---
        # --- LÓGICA GET (MOMIAS) ---
    fecha_filtro = request.GET.get('fecha_filtro')
    query = request.GET.get('q', '').strip() # Aseguramos limpiar espacios
        
    # Registro base
    registros_qs = Asistencia.objects.exclude(sucursal="FastFood").order_by('-fecha', '-id')
        
    # Filtro por Fecha (Independiente)
    if fecha_filtro:
        registros_qs = registros_qs.filter(fecha=fecha_filtro)
        
    # Filtro por Nombre o Código
    if query:
        # Usamos Q objects para ser más eficientes sin depender solo de la anotación
        registros_qs = registros_qs.filter(
            Q(empleado__nombre__icontains=query) | 
            Q(empleado__apellido_paterno__icontains=query) |
            Q(empleado__codigo_empleado__icontains=query)
        )
        
    # Paginación
    paginator = Paginator(registros_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # Renderizado con los datos de Momias
    return render(request, 'Attendance.html', { # Asegúrate de que este sea tu template de Momias
        'lista_puestos': puestos_salarios.keys(), # Diccionario general de Momias
        'empleados': Empleado.objects.filter(estatus='Activo'),
        'registros': page_obj,
        'hoy': datetime.now().strftime('%Y-%m-%d'),
        'puestos_json': json.dumps(puestos_salarios),
        'fecha_filtro': fecha_filtro or '', # Evita el "None" en el input
        'query': query or '',               # Evita el "None" en el input
    })


from datetime import datetime, timedelta

def Asistencias_FF_view(request):
    puestos_salarios_ff = {
        "Caja (6 horas)": 248.00,  
        "Caja (9 horas)": 354.50,
        "Gerente (12 Horas)": 600.00, 
        "Chef de Línea": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00,
        "Encargado Cocina (Matutino 9 horas)": 378.00,
        "Encargado Cocina (Matutino 12 horas)": 504.00,
        "Encargado de Cocina (JONH)": 519.00,
        "Cocina y Barra (6 hrs)": 236.50,
        "Cocina y Barra (9 hrs)": 354.50,
        "Barra (6 horas) Entregas": 236.50,
        "Barra (9 horas) Entregas": 354.50,
        "Fin de Semana": 473.00,
        "Aux Produccion": 177.00,
        "Produccion": 370.00,
        "Hamburguesas FF": 0.00,
        "Tuppers": 0.00,
    }

    def obtener_monto_bloque(base_puesto, entrada, salida):
        if not entrada or not salida: return 0.0
        ent_str, sal_str = entrada.strip().upper(), salida.strip().upper()
        if 'R' in ent_str or ':' not in ent_str or 'R' in sal_str or ':' not in sal_str:
            return float(base_puesto)
        try:
            fmt = '%H:%M'
            inicio = datetime.strptime(ent_str[:5], fmt)
            fin = datetime.strptime(sal_str[:5], fmt)
            hrs = (fin - inicio).total_seconds() / 3600
            if hrs < 0: hrs += 24
            return (float(base_puesto) / 6) * hrs
        except (ValueError, ZeroDivisionError):
            return float(base_puesto)

    # --- 1. LÓGICA DE ELIMINACIÓN ---
    if request.method == 'POST' and 'eliminar_id' in request.POST:
        asistencia = get_object_or_404(Asistencia, id=request.POST.get('eliminar_id'))
        asistencia.delete()
        messages.success(request, "¡Registro eliminado de FF!")
        return redirect('asistenciasff')

    # --- 2. LÓGICA DE GUARDADO / MODIFICACIÓN ---
    if request.method == 'POST':
        try:
            asistencia_id = request.POST.get('asistencia_id')
            empleado_id = request.POST.get('empleado')
            puesto_seleccionado = (request.POST.get('puesto') or "").strip()
            estatus_jornada = request.POST.get('estatus_jornada')
            ent_m, sal_m = (request.POST.get('entrada_matutina') or "").strip(), (request.POST.get('salida_matutina') or "").strip()
            ent_v, sal_v = (request.POST.get('entrada_vespertina') or "").strip(), (request.POST.get('salida_vespertina') or "").strip()

            monto_final = 0.0
            DESCANSO_ESPECIFICO = 138.00

            if estatus_jornada in ["Falta", "Permiso", "Vacaciones"]:
                monto_final = 0.0
            elif estatus_jornada == "Descanso":
                monto_final = DESCANSO_ESPECIFICO if puesto_seleccionado in ["Hamburguesas FF", "Tuppers"] else 0.0
            elif puesto_seleccionado == "Hamburguesas FF":
                monto_final = float(request.POST.get('cantidad_cargas') or 0) * 62.00
            elif puesto_seleccionado == "Tuppers":
                monto_final = float(request.POST.get('cantidad_cargas') or 0) * 46.50
            else:
                base_real = float(puestos_salarios_ff.get(puesto_seleccionado, 0))
                base_6h = base_real
                if "(9 horas)" in puesto_seleccionado or "(9 hrs)" in puesto_seleccionado:
                    base_6h = base_real / 1.5
                elif "(12 Horas)" in puesto_seleccionado:
                    base_6h = base_real / 2
                monto_final = obtener_monto_bloque(base_6h, ent_m, sal_m) + obtener_monto_bloque(base_6h, ent_v, sal_v)

            # Puntos de retardo y descuento
            def calcular_puntos(valor):
                if not valor or ":" in valor or "R1" in valor: return 0
                mapping = {"R2": 1, "R3": 2, "R4": 3, "R5": 4, "R6": 5, "R7": 6, "R8": 7, "R9": 8, "R10": 9, "R11": 10, "R12": 11}
                for clave, pts in mapping.items():
                    if clave in valor.upper(): return pts
                return 0

            total_puntos = calcular_puntos(ent_m) + calcular_puntos(ent_v)
            monto_final = max(0, monto_final - (total_puntos * 10.00)) # Ajusta 10.00 si es necesario

            # Guardado
            if asistencia_id and asistencia_id.strip():
                asistencia = get_object_or_404(Asistencia, id=asistencia_id)
            else:
                asistencia = Asistencia()
                asistencia.sucursal = "FastFood"

            asistencia.empleado = Empleado.objects.get(id=empleado_id)
            asistencia.fecha = request.POST.get('fecha')
            asistencia.estatus = estatus_jornada
            asistencia.puesto = puesto_seleccionado
            asistencia.pago_dia = round(monto_final, 2)
            asistencia.horas = float(total_puntos)
            asistencia.entrada_matutina, asistencia.salida_matutina = ent_m, sal_m
            asistencia.entrada_vespertina, asistencia.salida_vespertina = ent_v, sal_v
            asistencia.bonificacion = float(request.POST.get('bonificacion') or 0)
            asistencia.descuento = float(request.POST.get('descuento') or 0)
            asistencia.motivo_bonificacion = request.POST.get('motivo_bonificacion')
            asistencia.motivo_descuento = request.POST.get('motivo_descuento')
            asistencia.tipo_uniforme = request.POST.get('tipo_uniforme')
            asistencia.observaciones = request.POST.get('observaciones')
            asistencia.save()
            messages.success(request, "¡Registro FF procesado!")
            return redirect('asistenciasff')
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect('asistenciasff')

        # --- 3. LÓGICA GET ---
    fecha_filtro = request.GET.get('fecha_filtro')
    query = request.GET.get('q')
    
    # Filtrar SOLO por la sucursal de este módulo
    registros_qs = Asistencia.objects.filter(sucursal="FastFood").order_by('-fecha', '-id')
    
    # Filtro por Fecha (Independiente)
    if fecha_filtro:
        registros_qs = registros_qs.filter(fecha=fecha_filtro)
    
    # Filtro por Nombre/Código (Independiente)
    if query:
        registros_qs = registros_qs.filter(
            Q(empleado__nombre__icontains=query) | 
            Q(empleado__apellido_paterno__icontains=query) |
            Q(empleado__codigo_empleado__icontains=query)
        )
    
    paginator = Paginator(registros_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'AttendanceFF.html', {
        'lista_puestos': puestos_salarios_ff.keys(),
        'empleados': Empleado.objects.filter(estatus='Activo'),
        'registros': page_obj,
        'hoy': datetime.now().strftime('%Y-%m-%d'),
        'puestos_json': json.dumps(puestos_salarios_ff),
        'fecha_filtro': fecha_filtro or '', # Enviamos cadena vacía si es None
        'query': query or '',               # Enviamos cadena vacía si es None
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

    # ... (tus filtros de fecha y sucursal se mantienen igual) ...
    fecha_inicio = request.GET.get('inicio')
    fecha_fin = request.GET.get('fin')
    sucursal_filtro = request.GET.get('sucursal')
    nombre_filtro = request.GET.get('nombre')
    
    resultados_nomina = []

    puestos_salarios = {
        # ... (tu diccionario de puestos se mantiene igual) ...
        "Caja (6 horas)": 248.00,  "Caja (9 horas)": 354.50,
        "Gerente (12 Horas)": 600.00, "Chef de Línea": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00,
        "Encargado Cocina (Matutino 9 horas)": 378.00,
        "Encargado Cocina (Matutino 12 horas)": 504.00,
        "Encargado de Cocina (JONH)": 519.00,
        "Cocina y Barra (6 hrs)": 236.50,
        "Cocina y Barra (9 hrs)": 354.50,
        "Barra (6 horas) Entregas": 236.50,
        "Barra (9 horas) Entregas": 354.50,
        "Fin de Semana": 473.00,
        "Produccion": 0.00,
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
    }

    DESCUENTO_UNIFORME_SEMANAL = 181.00

    # ... (tus funciones procesar_dato_hibrido y calcular_pago_dia_final se mantienen igual) ...
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

    # --- INICIO DEL PROCESAMIENTO ---
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

            for sem_inicio, sem_fin in intervalos_semanas:
                filtros_asistencia = Q(fecha__range=[sem_inicio, sem_fin])
                if sucursal_filtro and sucursal_filtro != "TODAS":
                    filtros_asistencia &= Q(sucursal__iexact=sucursal_filtro)
                if nombre_filtro:
                    filtros_asistencia &= (Q(empleado__nombre__icontains=nombre_filtro) | 
                                           Q(empleado__apellido_paterno__icontains=nombre_filtro))
    
                empleados_ids = Asistencia.objects.filter(filtros_asistencia).values_list('empleado_id', flat=True).distinct()

                for emp_id in empleados_ids:
                    empleado = Empleado.objects.get(id=emp_id)
                    asistencias = Asistencia.objects.filter(filtros_asistencia, empleado=empleado).order_by('fecha')
                    puestos_semana = [a.puesto for a in asistencias if a.puesto and "DESCANSO" not in (a.estatus or "").upper()]
                    
                    if puestos_semana:
                        conteo = Counter(puestos_semana)
                        salario_descanso = sum((puestos_salarios.get(p, 0) * (c / len(puestos_semana))) for p, c in conteo.items())
                        puesto_principal = conteo.most_common(1)[0][0]
                    else:
                        salario_descanso = float(empleado.sueldo_base or 0)
                        puesto_principal = "Sin Puesto"
        
                    # Variables acumuladoras
                    pago_base_total = total_retardos = total_bonos = total_descuentos_manuales = 0
                    total_desc_retardos_semanal = 0.0 # <--- NUEVA VARIABLE
                    aplica_uniforme_semanal = False 
                    dias_semana_esp = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                    dias_map = {d: [] for d in dias_semana_esp}
        
                   for reg in asistencias:
                        val_pago_manual = float(reg.pago_dia or 0.0)
                        val_bono = float(reg.bonificacion or 0.0)
                        val_desc = float(reg.descuento or 0.0)
                        if reg.tipo_uniforme and len(str(reg.tipo_uniforme).strip()) > 0:
                            aplica_uniforme_semanal = True
                        
                        estatus_limpio = (reg.estatus or "").upper()
                        salario_base_puesto = puestos_salarios.get(reg.puesto, empleado.sueldo_base or 0)
                        base_calc = float(salario_base_puesto)
                        
                        # Guardamos el salario base del puesto antes de normalizar a 6h para el descuento
                        salario_puesto_full = base_calc 
        
                        if "(9 horas)" in (reg.puesto or ""): base_calc /= 1.5
                        elif "(12 Horas)" in (reg.puesto or ""): base_calc /= 2
        
                        if "DESCANSO" in estatus_limpio and "TRABAJADO" not in estatus_limpio:
                            salario_dia = salario_descanso
                            retardo_dia = 0
                            descuento_retardo_dia = 0 
                        elif val_pago_manual > 0:
                            salario_dia = val_pago_manual
                            retardo_dia = int(reg.horas or 0)
                            descuento_retardo_dia = (val_pago_manual / 6) * retardo_dia
                        else:
                            salario_dia, retardo_aut = calcular_pago_dia_final(base_calc, reg)
                            retardo_dia = int(reg.horas) if reg.horas else retardo_aut
                            descuento_retardo_dia = (float(salario_puesto_full) / 6) * retardo_dia
        
                        if "DESCANSO TRABAJADO" in estatus_limpio or "FESTIVO TRABAJADO" in estatus_limpio:
                            salario_dia *= 2
        
                        pago_base_total += salario_dia
                        total_retardos += retardo_dia
                        total_desc_retardos_semanal += descuento_retardo_dia 
                        total_bonos += val_bono
                        total_descuentos_manuales += val_desc
                        
                        nombre_dia = dias_semana_esp[reg.fecha.weekday()]
                        
                        # AHORA AGREGAMOS EL TURNO A LA LISTA DEL DÍA
                        dias_map[nombre_dia].append({
                            'horas': retardo_dia,
                            'estatus': estatus_limpio,
                            'pago_dia': round(salario_dia, 2),
                            'sucursal': reg.sucursal or '---',
                            'puesto': reg.puesto or '---',
                            'descuento_retardo': round(descuento_retardo_dia, 2), 
                            'descuento_aplicado': round(val_desc, 2)
                        })
        
        return render(request, 'Paysheet.html', {                    
            'nominas': resultados_nomina,
            'inicio': fecha_inicio,
            'fin': fecha_fin,
            'sucursal_seleccionada': sucursal_filtro,
            'nombre_busqueda': nombre_filtro
        })

def obtener_datos_nomina_total(inicio, fin, nombre_busqueda=None, sucursal_sel=None):
    from collections import Counter
    from django.db.models import Q

    puestos_salarios = {
        "Gerente (12 Horas)": 600.00, "Chef de Línea": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00, "Encargado Cocina (Matutino 9 horas)": 378.00,
        "Encargado Cocina (Matutino 12 horas)": 504.00, "Encargado de Cocina (JONH)": 519.00,
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

def vista_reportes(request):
    empleados = Empleado.objects.filter(estatus='Activo').order_by('nombre')
    
    # Captura de parámetros
    emp_id = request.GET.get('empleado_id')
    nombre_texto = request.GET.get('nombre', '').strip()
    sucursal_filtro = request.GET.get('sucursal')
    f_inicio = request.GET.get('fecha_inicio')
    f_fin = request.GET.get('fecha_fin')

    # Diccionario de salarios
    puestos_salarios = {
        "Caja (6 horas)": 248.00,  "Caja (9 horas)": 354.50,
        "Gerente (12 Horas)": 600.00, "Chef de Línea": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00,
        "Encargado Cocina (Matutino 9 horas)": 378.00,
        "Encargado Cocina (Matutino 12 horas)": 504.00,
        "Encargado de Cocina (JONH)": 519.00,
        "Cocina y Barra (6 hrs)": 236.50,
        "Cocina y Barra (9 hrs)": 354.50,
        "Barra (6 horas) Entregas": 236.50,
        "Barra (9 horas) Entregas": 354.50,
        "Fin de Semana": 473.00,
        "Produccion": 0.00,
        "Encargado Victoria (6 Horas)": 316.00,
        "Encargado Sucursales (6 Horas)": 262.00,
        "Encargado Sucursales (9 Horas)": 393.00, 
        "Freidor (6 horas)": 248.00,
        "Freidor (9 horas)": 372.00, 
        "Despacho (6 horas)": 236.50,
        "Despacho (9 horas)": 354.75, 
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
    }

    # --- Funciones de apoyo ---
    def a_minutos(valor, es_entrada, bloque):
        if not valor: return None
        v = str(valor).strip().upper()
        if ':' in v:
            try:
                h, m = map(int, v[:5].split(':'))
                return h * 60 + m
            except: pass
        return (9*60 if es_entrada else 15*60) if bloque == 'M' else (15*60 if es_entrada else 21*60)

    def calcular_pago_dia_final(base_6h, ent_m, sal_m, ent_v, sal_v):
        minutos = 0
        if ent_m and sal_v and not sal_m and not ent_v: # Jornada continua
            m_i, m_f = a_minutos(ent_m, True, 'M'), a_minutos(sal_v, False, 'V')
            if m_i is not None and m_f is not None:
                diff = m_f - m_i
                minutos = diff + 1440 if diff < 0 else diff
        else: # Por bloques
            if ent_m and sal_m: minutos += max(0, a_minutos(sal_m, False, 'M') - a_minutos(ent_m, True, 'M'))
            elif ent_m or sal_m: minutos += 360
            if ent_v and sal_v: minutos += max(0, a_minutos(sal_v, False, 'V') - a_minutos(ent_v, True, 'V'))
            elif ent_v or sal_v: minutos += 360
        return (float(base_6h) / 360) * minutos

    asistencias_query = None
    resumen_global = {'total_pagar': 0, 'total_retardos': 0, 'total_bonif': 0}

    # Solo procesamos si hay rango de fechas (el reporte empieza vacío)
    if f_inicio and f_fin:
        asistencias_query = Asistencia.objects.filter(fecha__range=[f_inicio, f_fin])

        # 1. Filtro por Sucursal
        if sucursal_filtro:
            asistencias_query = asistencias_query.filter(sucursal=sucursal_filtro)

        # 2. Filtro por Persona (Doble opción)
        if emp_id:
            asistencias_query = asistencias_query.filter(empleado_id=emp_id)
        elif nombre_texto:
            asistencias_query = asistencias_query.filter(
                Q(empleado__nombre__icontains=nombre_texto) | 
                Q(empleado__apellido_paterno__icontains=nombre_texto)
            )

        # Ordenar para que el reporte sea legible
        asistencias_query = asistencias_query.order_by('empleado__nombre', 'fecha')

        # 3. Procesamiento de Cálculos para cada fila
        for asis in asistencias_query:
            emp = asis.empleado
            estatus = (asis.estatus or "").upper()
            sal_puesto = puestos_salarios.get(asis.puesto, emp.sueldo_base or 0)
            
            # Normalizar base a 6 horas
            base_calc = float(sal_puesto)
            if "(9 horas)" in (asis.puesto or ""): base_calc /= 1.5
            elif "(12 Horas)" in (asis.puesto or ""): base_calc /= 2

            # Lógica de pago por día
            if "DESCANSO" in estatus and "TRABAJADO" not in estatus:
                pago_dia = float(emp.sueldo_base or 0)
            elif asis.pago_dia and float(asis.pago_dia) > 0:
                pago_dia = float(asis.pago_dia)
            else:
                pago_dia = calcular_pago_dia_final(base_calc, asis.entrada_matutina, asis.salida_matutina, asis.entrada_vespertina, asis.salida_vespertina)
                if "DESCANSO TRABAJADO" in estatus or "FESTIVO TRABAJADO" in estatus:
                    pago_dia *= 2

            # Guardar valor calculado en el objeto para el template
            asis.pago_calculado = round(pago_dia, 2)
            
            # Acumular en el resumen global
            resumen_global['total_pagar'] += pago_dia
            resumen_global['total_retardos'] += int(asis.horas or 0)
            resumen_global['total_bonif'] += float(asis.bonificacion or 0)

    context = {
        'empleados': empleados,
        'asistencias': asistencias_query,
        'fecha_inicio': f_inicio,
        'fecha_fin': f_fin,
        'resumen': {
            'total_pagar': round(resumen_global['total_pagar'], 2),
            'total_retardos': resumen_global['total_retardos'],
            'total_bonif': round(resumen_global['total_bonif'], 2)
        }
    }

    return render(request, 'Reports.html', context)

@staff_member_required  # Solo usuarios con acceso al staff/admin
def admin_cambiar_password(request, user_id):
    # Obtenemos al empleado (usuario) específico
    usuario_objetivo = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = AdminPasswordChangeForm(usuario_objetivo, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'¡Contraseña de {usuario_objetivo.username} actualizada!')
            return redirect('gestion_usuarios') # Cambia esto a tu lista de usuarios
    else:
        form = AdminPasswordChangeForm(usuario_objetivo)
    
    return render(request, 'admin_cambiar_password.html', {
        'form': form,
        'usuario_objetivo': usuario_objetivo
    })

@staff_member_required
def gestion_usuario_admin(request, user_id=None):
    # Definimos el estado inicial
    edit_mode = False
    usuario_objetivo = None

    # Si hay un ID, cambiamos al estado "Actualización"
    if user_id:
        edit_mode = True
        usuario_objetivo = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        pass1 = request.POST.get('password')
        pass2 = request.POST.get('password_confirm')

        if pass1 != pass2:
            messages.error(request, "¡Las contraseñas no coinciden, recluta!")
        else:
            if edit_mode:
                # Estado: Actualizar
                usuario_objetivo.set_password(pass1)
                usuario_objetivo.save()
                messages.success(request, f"¡Contraseña de {usuario_objetivo.username} actualizada!")
            else:
                # Estado: Nuevo Registro
                username = request.POST.get('username')
                if User.objects.filter(username=username).exists():
                    messages.error(request, "Ese nombre ya está en las filas.")
                    return render(request, 'registro.html', {'edit_mode': edit_mode})
                User.objects.create_user(username=username, password=pass1)
                messages.success(request, f"¡Recluta {username} registrado!")
            
            return redirect('lista_usuarios')

    return render(request, 'Register.html', {
        'edit_mode': edit_mode,
        'usuario_objetivo': usuario_objetivo
    })

@staff_member_required
def borrar_usuario(request, user_id):
    if request.user.id == user_id:
        messages.error(request, "¡No puedes borrarte a ti mismo, eres el líder!")
        return redirect('lista_usuarios')
    
    usuario = get_object_or_404(User, id=user_id)
    usuario.delete()
    messages.success(request, "Recluta eliminado correctamente.")
    return redirect('lista_usuarios')
