from django.db import models


class Empleado(models.Model):
    codigo_empleado = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    apellido_materno = models.CharField(max_length=100, blank=True, null=True)
    puesto = models.CharField(max_length=100)
    sueldo_base = models.FloatField()
    estatus = models.CharField(max_length=20, default='Activo')
    fecha_baja = models.DateField(null=True, blank=True)
    # Cambio sugerido: Asegúrate de tener instalada la librería Pillow (pip install Pillow)
    foto = models.ImageField(upload_to='media/empleados/fotos/', null=True, blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.codigo_empleado} - {self.nombre} {self.apellido_paterno}"

class Asistencia(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField()
    entrada = models.TimeField(blank=True, null=True)
    salida = models.TimeField(blank=True, null=True)
    estatus = models.CharField(max_length=50, blank=True, null=True)
    horas = models.FloatField(blank=True, null=True)
    # --- AGREGA ESTOS CAMPOS PARA QUE NO TRUENE EL GUARDADO ---
    puesto = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    bonificacion = models.FloatField(default=0.0)
    descuento = models.FloatField(default=0.0)
    sucursal = models.CharField(max_length=100, blank=True, null=True)
    salida_matutina = models.TimeField(null=True, blank=True)
    salida_vespertina = models.TimeField(null=True, blank=True)
    retardo = models.IntegerField(default=0) # O el nombre exacto que desees

    def __str__(self):
        return f"{self.fecha} - {self.empleado.nombre}"

class Usuario(models.Model):
    # Nota: Django ya tiene un sistema de usuarios (User). 
    # Si quieres uno personalizado, este es el modelo:
    usuario = models.CharField(max_length=50, unique=True)
    contrasena = models.CharField(max_length=128) # Almacena hashes, no texto plano
    rol = models.CharField(max_length=50)

class ConfigNomina(models.Model):
    bono_puntualidad = models.FloatField(default=0.0)
    pago_hora_extra = models.FloatField(default=0.0)
    descuento_retardo = models.FloatField(default=0.0)

class Nomina(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    sueldo_base = models.FloatField()
    horas_extra = models.FloatField(default=0.0)
    incidencias = models.FloatField(default=0.0)
    total = models.FloatField()

class Documento(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='documentos')
    nombre_archivo = models.CharField(max_length=255)
    # Tip: Es mejor guardar la fecha de subida automáticamente para la tabla del modal
    archivo = models.FileField(upload_to='empleados/pdfs/')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_archivo} ({self.empleado.nombre})"