from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
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
    puestos_salarios = {
        "Caja (6 horas)": 236.50, 
        "Caja (9 horas)": 354.50,
        "Encargado Victoria (6 Horas)": 316.00,
        "Encargado Victoria (12 Horas)": 632.00, 
        "Encargado Sucursales (6 Horas)": 262.00,
        "Encargado Sucursales (9 Horas)": 393.00, 
        "Freidor (6 horas)": 248.00,
        "Freidor (9 horas)": 372.00, 
        "Despacho (6 horas)": 236.50,
        "Despacho (9 horas)": 354.75, 
        "Benny": 171.00
    }
    
    # --- LÓGICA DE ELIMINACIÓN ---
    if request.method == 'POST' and 'eliminar_id' in request.POST:
        asistencia_id = request.POST.get('eliminar_id')
        asistencia = get_object_or_404(Asistencia, id=asistencia_id)
        asistencia.delete()
        messages.success(request, "¡Registro eliminado!")
        return redirect('asistencias')

    # --- LÓGICA DE GUARDADO / MODIFICACIÓN ---
    if request.method == 'POST':
        try:
            empleado_id = request.POST.get('empleado')
            asistencia_id = request.POST.get('asistencia_id')
            
            # 1. Calcular puntos de retardo
            def calcular_puntos(rango):
                if not rango or "R1" in rango: return 0
                mapping = {"R2": 1, "R3": 2, "R4": 3, "R5": 4, "R6": 5, "R7": 6, "R8": 7, "R9": 8, "R10": 9, "R11": 10, "R12": 11}
                for clave, valor in mapping.items():
                    if clave in rango: return valor
                return 0

            puntos_m = calcular_puntos(request.POST.get('entrada_matutina'))
            puntos_v = calcular_puntos(request.POST.get('entrada_vespertina'))
            total_puntos = puntos_m + puntos_v

            # 2. Obtener o Crear el objeto (Modo Tkinter: Modificar si existe ID)
            if asistencia_id:
                asistencia = get_object_or_404(Asistencia, id=asistencia_id)
                msg = "¡Registro actualizado con éxito!"
            else:
                asistencia = Asistencia()
                msg = "¡Nuevo registro capturado!"
                asistencia.sucursal = request.POST.get('sucursal')

            # 3. Asignar todos los campos del formulario
            asistencia.empleado = Empleado.objects.get(id=empleado_id)
            asistencia.fecha = request.POST.get('fecha')
            asistencia.estatus = request.POST.get('estatus_jornada')
            asistencia.horas = float(total_puntos) # Siguiendo tu lógica de guardar puntos aquí
            asistencia.puesto = request.POST.get('puesto')
            asistencia.observaciones = request.POST.get('observaciones')
            
            # Campos de dinero (con validación por si vienen vacíos)
            asistencia.bonificacion = float(request.POST.get('bonificacion') or 0)
            asistencia.descuento = float(request.POST.get('descuento') or 0)
            
            # Guardar
            asistencia.save()
            messages.success(request, msg)
            return redirect('asistencias')

        except Exception as e:
            messages.error(request, f"¡Rayos! Algo salió mal: {e}")

    # --- LÓGICA GET ---
    filtro = request.GET.get('filtro')
    hoy_str = datetime.now().strftime('%Y-%m-%d')
    
    if filtro == 'hoy':
        registros = Asistencia.objects.filter(fecha=hoy_str).order_by('-id')
    else:
        registros = Asistencia.objects.all().order_by('-fecha', '-id')[:20]

    context = {
        'lista_puestos': puestos_salarios.keys(),
        'empleados': Empleado.objects.filter(estatus='Activo'),
        'registros': Asistencia.objects.all().order_by('-id')[:20],
        'hoy': datetime.now().strftime('%Y-%m-%d'),
        # IMPORTANTE: Convertir a JSON aquí
        'puestos_json': json.dumps(puestos_salarios), 
    }
    return render(request, 'Attendance.html', context)


def Asistencias_FF_view(request):
    puestos_salarios_ff = {
        "Caja (6 horas)": 236.50, "Caja (9 horas)": 354.50,
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
    }
    
    # --- 1. LÓGICA POST (GUARDADO Y ELIMINACIÓN) ---
    if request.method == 'POST':
        # Caso A: Eliminar
        if 'eliminar_id' in request.POST:
            asistencia_id = request.POST.get('eliminar_id')
            asistencia = get_object_or_404(Asistencia, id=asistencia_id)
            asistencia.delete()
            messages.success(request, "¡Registro de FastFood eliminado!")
            return redirect('asistenciasff')

        # Caso B: Guardar/Actualizar
        try:
            empleado_id = request.POST.get('empleado')
            asistencia_id = request.POST.get('asistencia_id')
            
            def calcular_puntos(rango):
                if not rango or "R1" in rango: return 0
                mapping = {"R2": 1, "R3": 2, "R4": 3, "R5": 4, "R6": 5, "R7": 6, "R8": 7, "R9": 8, "R10": 9, "R11": 10, "R12": 11}
                for clave, valor in mapping.items():
                    if clave in rango: return valor
                return 0

            puntos_m = calcular_puntos(request.POST.get('entrada_matutina'))
            puntos_v = calcular_puntos(request.POST.get('entrada_vespertina'))
            total_puntos = puntos_m + puntos_v

            if asistencia_id:
                asistencia = get_object_or_404(Asistencia, id=asistencia_id)
                msg = "¡Registro FF actualizado!"
            else:
                asistencia = Asistencia()
                asistencia.sucursal = "FastFood"
                msg = "¡Nuevo registro FF capturado!"

            asistencia.empleado = Empleado.objects.get(id=empleado_id)
            asistencia.fecha = request.POST.get('fecha')
            # IMPORTANTE: Guardar en .estatus para que la nómina lo vea
            asistencia.estatus = request.POST.get('estatus_jornada') 
            asistencia.horas = float(total_puntos) 
            asistencia.puesto = request.POST.get('puesto')
            asistencia.bonificacion = float(request.POST.get('bonificacion') or 0)
            asistencia.descuento = float(request.POST.get('descuento') or 0)
            asistencia.observaciones = request.POST.get('observaciones')
            
            asistencia.save()
            messages.success(request, msg)
            return redirect('asistencias_ff')
        except Exception as e:
            messages.error(request, f"Error en FastFood: {e}")
            # Si hay error, regresamos a la vista normal para no devolver None
            return redirect('asistenciasff')

    # --- 2. LÓGICA GET (ESTO SIEMPRE SE EJECUTA SI NO ES POST) ---
    # Asegúrate de que estas líneas estén alineadas al primer nivel de la función
    hoy_str = datetime.now().strftime('%Y-%m-%d')
    registros = Asistencia.objects.filter(sucursal="FastFood").order_by('-fecha', '-id')[:20]

    context = {
        'lista_puestos': puestos_salarios_ff.keys(),
        'empleados': Empleado.objects.filter(estatus='Activo'),
        'registros': registros,
        'hoy': hoy_str,
        'puestos_json': json.dumps(puestos_salarios_ff), 
    }
    
    # ESTE ES EL RETURN QUE TE FALTABA O ESTABA MAL IDENTADO
    return render(request, 'AttendanceFF.html', context)

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
    fecha_inicio = request.GET.get('inicio')
    fecha_fin = request.GET.get('fin')
    sucursal_filtro = request.GET.get('sucursal')
    nombre_filtro = request.GET.get('nombre')
    
    resultados_nomina = []

    puestos_salarios = {
        "Gerente (12 Horas)": 600.00, "Chef de Línea": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00, "Encargado Cocina (Matutino 9 horas)": 378.00,
        "Encargado Cocina (Matutino 12 horas)": 504.00, "Encargado de Cocina (JONH)": 519.00,
        "Cocina y Barra (6 hrs)": 236.50, "Cocina y Barra (9 hrs)": 354.50,
        "Caja (6 horas)": 236.50, "Caja (9 horas)": 354.50,
        "Barra (6 horas) Entregas": 236.50, "Barra (9 horas) Entregas": 354.50,
        "Fin de Semana": 473.00, "Encargado Victoria (6 Horas)": 316.00,
        "Encargado Victoria (12 Horas)": 632.00, "Encargado Sucursales (6 Horas)": 262.00,
        "Encargado Sucursales (9 Horas)": 393.00, "Freidor (6 horas)": 248.00,
        "Freidor (9 horas)": 372.00, "Despacho (6 horas)": 236.50,
        "Despacho (9 horas)": 354.75, "Benny": 171.00
    }

    if fecha_inicio and fecha_fin:
        filtros_asistencia = Q(fecha__range=[fecha_inicio, fecha_fin])
        
        if sucursal_filtro and sucursal_filtro != "TODAS":
            filtros_asistencia &= Q(sucursal__iexact=sucursal_filtro)
            
        if nombre_filtro:
            filtros_asistencia &= (Q(empleado__nombre__icontains=nombre_filtro) | 
                                   Q(empleado__apellido_paterno__icontains=nombre_filtro))

        empleados_ids = Asistencia.objects.filter(filtros_asistencia).values_list('empleado_id', flat=True).distinct()

        for emp_id in empleados_ids:
            empleado = Empleado.objects.get(id=emp_id)
            
            # Obtenemos asistencias según el filtro
            if sucursal_filtro and sucursal_filtro != "TODAS":
                asistencias = Asistencia.objects.filter(filtros_asistencia, empleado=empleado).order_by('fecha')
            else:
                asistencias = Asistencia.objects.filter(fecha__range=[fecha_inicio, fecha_fin], empleado=empleado).order_by('fecha')

            puestos_lista = [a.puesto for a in asistencias if a.puesto]
            puesto_principal = Counter(puestos_lista).most_common(1)[0][0] if puestos_lista else "Sin Puesto"
            salario_descanso_base = puestos_salarios.get(puesto_principal, empleado.sueldo_base or 0)

            pago_base_acumulado = 0
            total_retardos = 0
            total_bonos = 0
            total_descuentos_manuales = 0

            dias_map = {d: {'horas': 0, 'estatus': '---'} for d in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]}
            dias_semana_esp = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

            for reg in asistencias:
                salario_dia = puestos_salarios.get(reg.puesto, empleado.sueldo_base or 0)
                # IMPORTANTE: Aseguramos que el estatus no sea None
                estatus_limpio = reg.estatus.upper() if reg.estatus else ""
                
                # --- 1. LÓGICA DE PAGOS ---
                if any(x in estatus_limpio for x in ["ACTIVO", "NORMAL"]):
                    pago_base_acumulado += salario_dia
                elif "DESCANSO TRABAJADO" in estatus_limpio or "FESTIVO TRABAJADO" in estatus_limpio:
                    pago_base_acumulado += (salario_dia * 2)
                elif "DESCANSO" in estatus_limpio:
                    pago_base_acumulado += salario_dia

                # --- 2. LÓGICA DE RETARDOS (Sincronizada) ---
                if reg.horas:
                    total_retardos += int(reg.horas)

                # --- 3. BONOS Y DESCUENTOS ---
                # Usamos float y manejamos el None para evitar que se rompa el cálculo
                total_bonos += float(reg.bonificacion or 0)
                total_descuentos_manuales += float(reg.descuento or 0)

                # Guardar datos para la tabla HTML
                nombre_dia = dias_semana_esp[reg.fecha.weekday()]
                dias_map[nombre_dia] = {
                    'horas': reg.horas or 0,
                    'estatus': estatus_limpio
                }

            # --- 4. CÁLCULOS FINALES ---
            # El descuento por retardo se calcula al final de procesar todos los días
            desc_por_retardos = calcular_descuento_retardos(total_retardos, salario_descanso_base)
            
            # La cuota de uniforme se resta una sola vez por periodo (si aplica)
            cuota_uniforme = getattr(empleado, 'cuota_uniforme', 0) or 0

            # FÓRMULA FINAL: (Base + Bonos) - (Descuentos Manuales + Retardos + Uniforme)
            total_neto = (pago_base_acumulado + total_bonos) - (total_descuentos_manuales + desc_por_retardos + cuota_uniforme)

            resultados_nomina.append({
                'nombre': f"{empleado.nombre} {empleado.apellido_paterno}",
                'puesto_principal': puesto_principal,
                'dias': [dias_map[d] for d in dias_semana_esp],
                'pago_base': pago_base_acumulado,
                'retardos': total_retardos,
                'desc_retardos': desc_por_retardos,
                'bonos': total_bonos,
                'descuentos': total_descuentos_manuales,
                'uniforme': cuota_uniforme,
                'total_neto': total_neto,
            })

    return render(request, 'Paysheet.html', {
        'nominas': resultados_nomina,
        'inicio': fecha_inicio,
        'fin': fecha_fin,
        'sucursal_seleccionada': sucursal_filtro,
        'nombre_busqueda': nombre_filtro
    })

def obtener_datos_nomina_total(inicio, fin, nombre_busqueda=None, sucursal_sel=None):
    from collections import Counter # Asegúrate de tener esta importación al inicio del archivo

    puestos_salarios = {
        "Gerente (12 Horas)": 600.00, "Chef de Línea": 531.57,
        "Encargado Cocina (Matutino 6 horas)": 252.00, "Encargado Cocina (Matutino 9 horas)": 378.00,
        "Encargado Cocina (Matutino 12 horas)": 504.00, "Encargado de Cocina (JONH)": 519.00,
        "Cocina y Barra (6 hrs)": 236.50, "Cocina y Barra (9 hrs)": 354.50,
        "Caja (6 horas)": 236.50, "Caja (9 horas)": 354.50,
        "Barra (6 horas) Entregas": 236.50, "Barra (9 horas) Entregas": 354.50,
        "Fin de Semana": 473.00, "Encargado Victoria (6 Horas)": 316.00,
        "Encargado Victoria (12 Horas)": 632.00, "Encargado Sucursales (6 Horas)": 262.00,
        "Encargado Sucursales (9 Horas)": 393.00, "Freidor (6 horas)": 248.00,
        "Freidor (9 horas)": 372.00, "Despacho (6 horas)": 236.50,
        "Despacho (9 horas)": 354.75, "Benny": 171.00
    }

    datos_completos = []
    
    # Filtro base para obtener empleados
    filtros_base = Q(fecha__range=[inicio, fin])
    if sucursal_sel and sucursal_sel != "TODAS":
        filtros_base &= Q(sucursal__iexact=sucursal_sel)
    if nombre_busqueda:
        filtros_base &= (Q(empleado__nombre__icontains=nombre_busqueda) | Q(empleado__apellido_paterno__icontains=nombre_busqueda))

    empleados_ids = Asistencia.objects.filter(filtros_base).values_list('empleado_id', flat=True).distinct()

    for emp_id in empleados_ids:
        empleado = Empleado.objects.get(id=emp_id)
        
        # Aplicamos la misma lógica de "ver todo su sueldo" si no hay filtro de sucursal
        if sucursal_sel and sucursal_sel != "TODAS":
            asistencias = Asistencia.objects.filter(filtros_base, empleado=empleado).order_by('fecha')
        else:
            asistencias = Asistencia.objects.filter(fecha__range=[inicio, fin], empleado=empleado).order_by('fecha')

        # Determinar puesto principal para descuento de retardos
        puestos_lista = [a.puesto for a in asistencias if a.puesto]
        puesto_principal = Counter(puestos_lista).most_common(1)[0][0] if puestos_lista else "Sin Puesto"
        salario_descanso_base = puestos_salarios.get(puesto_principal, empleado.sueldo_base or 0)

        pago_base_acumulado = 0
        total_retardos = 0
        total_bonos = 0
        total_descuentos_manuales = 0

        for reg in asistencias:
            salario_dia = puestos_salarios.get(reg.puesto, empleado.sueldo_base or 0)
            estatus_limpio = reg.estatus.upper() if reg.estatus else ""
            
            if any(x in estatus_limpio for x in ["ACTIVO", "NORMAL"]):
                pago_base_acumulado += salario_dia
            elif "DESCANSO TRABAJADO" in estatus_limpio or "FESTIVO TRABAJADO" in estatus_limpio:
                pago_base_acumulado += (salario_dia * 2)
            elif "DESCANSO" in estatus_limpio:
                pago_base_acumulado += salario_dia

            if reg.entrada:
                total_retardos += obtener_valor_retardo(reg.entrada)
            
            total_bonos += float(reg.bonificacion or 0)
            total_descuentos_manuales += float(reg.descuento or 0)

        desc_por_retardos = calcular_descuento_retardos(total_retardos, salario_descanso_base)
        total_neto = (pago_base_acumulado + total_bonos) - (total_descuentos_manuales + desc_por_retardos)

        datos_completos.append({
            'nombre': f"{empleado.nombre} {empleado.apellido_paterno}",
            'puesto_principal': puesto_principal,
            'pago_base': pago_base_acumulado,
            'bonos': total_bonos,
            'descuentos': total_descuentos_manuales + desc_por_retardos, # Sumamos ambos tipos de descuento
            'uniforme': 0,
            'total_neto': total_neto
        })

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
    empleados = Empleado.objects.filter(estatus='Activo')
    context = {'empleados': empleados}
    
    emp_id = request.GET.get('empleado')
    f_inicio = request.GET.get('fecha_inicio')
    f_fin = request.GET.get('fecha_fin')

    if emp_id and f_inicio and f_fin:
        asistencias = Asistencia.objects.filter(
            empleado_id=emp_id, 
            fecha__range=[f_inicio, f_fin]
        ).order_by('fecha')
        
        # Lógica de cálculo (resumida del script de Tkinter)
        total_pago = 0
        total_retardos = 0
        for asis in asistencias:
            # Aquí aplicarías tus reglas de PUESTOS_SALARIOS
            # Simplificado para el ejemplo:
            asis.pago_calculado = 350.00 # Aquí va tu lógica de PUESTOS_SALARIOS.get(...)
            valor_retardo = getattr(asis, 'retardo', 0)
            total_pago += asis.pago_calculado
            total_retardos += asis.retardo if asis.retardo else 0

        context.update({
            'asistencias': asistencias,
            'fecha_inicio': f_inicio,
            'fecha_fin': f_fin,
            'resumen': {
                'total_pagar': total_pago,
                'total_retardos': total_retardos,
                'total_horas': sum(8 for _ in asistencias), # Ejemplo
                'total_bonif': 0
            }
        })

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