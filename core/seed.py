"""Datos de demostración (ficticios) para Bilbao y alrededores."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from core import db
from core.events import EMBUDOS

SP, SS, SPP, FD, MR, SE = ("sin_pilas", "sin_sonido", "sin_piezas_pequenas", "facil_desinfectar",
                           "movilidad_reducida", "sensorial")

PUNTOS = [
    ("Punto Deusto · Centro cívico", "Deusto", "Junto al centro cívico (ubicación aproximada)", "L-V 17:00-20:00", 43.2712, -2.9468),
    ("Punto Santutxu · Plaza del mercado", "Santutxu", "Plaza del mercado (ubicación aproximada)", "L-S 10:00-13:00", 43.2555, -2.9195),
    ("Punto Rekalde · Biblioteca", "Rekalde", "Frente a la biblioteca (ubicación aproximada)", "M-J 16:30-19:30", 43.2539, -2.9461),
    ("Punto Otxarkoaga · Ludoteca", "Otxarkoaga", "Ludoteca del barrio (ubicación aproximada)", "L-V 16:00-19:00", 43.2675, -2.9035),
]

ENTIDADES = [
    ("REYES-DEUSTO", "Servicios Sociales de Base de Deusto (demo)", "Servicios sociales", "ssb.deusto@ejemplo.org"),
    ("REYES-CARITAS", "Asociación de apoyo familiar Auzolan (demo)", "ONG", "familias@auzolan.ejemplo.org"),
    ("REYES-REKALDE", "CEIP Rekalde Goikoa (demo)", "Colegio", "orientacion@rekalde.ejemplo.org"),
]

ORGANIZACIONES = [
    ("ORG-LAGUNAK", "Asociación Lagunak (demo)", "ONG", "Itziar M.", "lagunak@ejemplo.org", "Santutxu"),
    ("ORG-ETXEBERRI", "Centro de menores Etxe Berri (demo)", "Centro de menores", "Javier R.", "etxeberri@ejemplo.org", "Otxarkoaga"),
    ("ORG-ITSASALDEA", "Hospital pediátrico Itsasaldea (ficticio)", "Hospital", "Unidad de Pediatría", "pediatria@itsasaldea.ejemplo.org", "Deusto"),
    ("ORG-GOIKOA", "Colegio Santutxu Goikoa (demo)", "Centro educativo", "Equipo de orientación", "goikoa@ejemplo.org", "Santutxu"),
]

EMPRESAS = [
    ("Industrias Lantegi Berria (empresa ficticia)", "Ane Etxeberria", "rsc@lantegiberria.ejemplo.com", "Industria"),
    ("Kafe Txokoa Distribución (empresa ficticia)", "Mikel Arana", "personas@kafetxokoa.ejemplo.com", "Distribución"),
]

# nombre, descripción, categoría, edad_min, edad_max, intereses, restricciones, peso_kg, publicado_en_stock
JUGUETES = [
    ("Dinosaurio de peluche grande", "Tiranosaurio de peluche suave de 40 cm, lavable a máquina.", "peluche", 0, 6, ["dinosaurios", "peluches"], [SP, SS, SPP, SE], 0.4, True),
    ("Set de figuras de dinosaurios", "12 figuras de plástico rígido de 8 a 15 cm con un pequeño volcán de cartón.", "muneco", 4, 10, ["dinosaurios", "animales"], [SP, SS, FD], 0.7, True),
    ("Puzle de dinosaurios de 100 piezas", "Puzle ilustrado con escena del Jurásico. Caja con una esquina aplastada.", "puzle", 6, 10, ["dinosaurios", "puzles"], [SP, SS, MR], 0.5, False),
    ("Kit de excavación de fósiles", "Bloque de yeso con réplicas de huesos de dinosaurio y herramientas para desenterrarlas.", "ciencia", 6, 12, ["dinosaurios", "ciencia", "exploración"], [SP, SS], 0.8, True),
    ("Libro ilustrado de dinosaurios", "Libro de tapa dura con solapas sobre los dinosaurios más conocidos.", "libro", 4, 9, ["dinosaurios", "lectura"], [SP, SS, SPP, MR], 0.6, False),
    ("Dinosaurios apilables de madera", "Seis dinosaurios de madera barnizada para apilar y encajar. Piezas grandes.", "construccion", 2, 5, ["dinosaurios", "construcción"], [SP, SS, SPP, FD], 0.6, True),
    ("Garaje de madera con 4 coches", "Garaje de dos plantas con rampa y ascensor manual. Incluye cuatro coches de madera.", "vehiculo", 3, 7, ["coches"], [SP, SS, FD], 2.5, True),
    ("Camión de bomberos con escalera", "Camión de plástico resistente con escalera giratoria. Sin luces ni sonido.", "vehiculo", 3, 8, ["coches", "oficios"], [SP, SS, FD], 0.9, False),
    ("Circuito de tren de madera", "40 piezas de vías, puente y dos locomotoras de madera.", "vehiculo", 3, 8, ["trenes", "construcción"], [SP, SS, FD], 1.8, True),
    ("Avión de juguete con hélice", "Avión de plástico con hélice que gira al empujarlo.", "vehiculo", 3, 7, ["aviones"], [SP, SS, FD], 0.5, False),
    ("Coche teledirigido todoterreno", "Coche de radiocontrol con suspensión. Funciona con pilas AA (no incluidas, compartimento con tornillo).", "vehiculo", 7, 12, ["coches"], [FD], 1.2, True),
    ("Barco pirata con figuras", "Barco con vela de tela, cañón de juguete y cuatro figuras de piratas.", "muneco", 4, 10, ["piratas", "barcos"], [SP, SS], 1.5, False),
    ("Bloques de construcción grandes", "60 bloques grandes de plástico para manos pequeñas. Fuera de catálogo.", "construccion", 1, 5, ["construcción"], [SP, SS, SPP, FD], 1.6, True),
    ("Juego de construcción magnética", "40 piezas magnéticas de colores para crear figuras en 3D.", "construccion", 4, 10, ["construcción"], [SP, SS, FD], 1.2, True),
    ("Robot para montar con engranajes", "Robot de piezas con engranajes y motor a pilas. Caja dañada, contenido precintado.", "ciencia", 8, 14, ["robots", "construcción", "ciencia"], [], 0.9, False),
    ("Castillo para montar de 300 piezas", "Castillo medieval con caballeros, torre y puente levadizo.", "construccion", 8, 14, ["construcción", "caballeros", "fantasía"], [SP, SS], 1.1, False),
    ("Muñeca de trapo con vestidos", "Muñeca de tela cosida con tres vestidos intercambiables.", "muneco", 3, 8, ["muñecos"], [SP, SS, SPP], 0.4, True),
    ("Bebé de juguete con carrito", "Bebé de vinilo con carrito plegable y biberón.", "muneco", 3, 7, ["bebés", "muñecos"], [SP, SS, FD], 1.8, True),
    ("Cocinita de madera con accesorios", "Cocinita con horno, fregadero y 12 accesorios de madera.", "muneco", 3, 7, ["cocina", "oficios"], [SP, SS, FD], 6.0, False),
    ("Granja con animales de madera", "Granja de madera con diez animales grandes.", "muneco", 2, 6, ["granja", "animales"], [SP, SS, SPP, FD], 1.4, True),
    ("Maletín de médico", "Maletín con fonendoscopio, jeringuilla sin aguja y termómetro de plástico.", "muneco", 3, 7, ["oficios"], [SP, SS, FD], 0.6, False),
    ("Teatro de marionetas de dedo", "Diez marionetas de dedo de animales y un pequeño teatrillo de cartón.", "muneco", 3, 8, ["marionetas", "lectura"], [SP, SS], 0.3, False),
    ("Set de figuras de superhéroes", "Cinco figuras articuladas de superhéroes genéricos (sin marca).", "muneco", 4, 10, ["superhéroes"], [SP, SS, FD], 0.5, False),
    ("Oso de peluche clásico", "Oso de peluche de 35 cm con lazo cosido.", "peluche", 0, 8, ["peluches", "animales"], [SP, SS, SPP, SE], 0.35, True),
    ("Unicornio de peluche", "Unicornio de peluche con crin de lana.", "peluche", 2, 8, ["peluches", "fantasía", "animales"], [SP, SS, SPP, SE], 0.4, True),
    ("Ballena de peluche", "Ballena azul de peluche suave, 30 cm.", "peluche", 0, 6, ["peluches", "mar", "animales"], [SP, SS, SPP, SE], 0.4, False),
    ("Parchís y oca 2 en 1", "Tablero reversible con fichas y dados. Caja con tara estética.", "juego_mesa", 5, 99, ["juegos de mesa"], [SP, SS, MR], 0.8, True),
    ("Juego de memoria de animales", "48 cartas gruesas con parejas de animales.", "juego_mesa", 3, 8, ["juegos de mesa", "animales"], [SP, SS, SPP, MR], 0.4, False),
    ("Dominó de madera", "28 fichas de madera con puntos grabados.", "juego_mesa", 4, 99, ["juegos de mesa", "números"], [SP, SS, MR, FD], 0.5, True),
    ("Juego de magia con 50 trucos", "Caja de magia con varita, cartas y libro de instrucciones.", "juego_mesa", 7, 14, ["magia"], [SP, SS, MR], 0.7, True),
    ("Ajedrez de madera", "Tablero plegable y piezas de madera.", "juego_mesa", 7, 99, ["juegos de mesa"], [SP, SS, MR], 0.9, False),
    ("Puzle del sistema solar de 200 piezas", "Puzle de los planetas con póster informativo.", "puzle", 7, 12, ["espacio", "puzles"], [SP, SS, MR], 0.6, True),
    ("Puzle de suelo de la granja", "24 piezas grandes de cartón grueso.", "puzle", 3, 6, ["granja", "animales", "puzles"], [SP, SS, SPP, MR], 0.7, True),
    ("Puzle del mapa de Europa de 500 piezas", "Puzle con países, capitales y monumentos.", "puzle", 10, 99, ["puzles", "exploración"], [SP, SS, MR], 0.8, False),
    ("Cuentos clásicos ilustrados", "Recopilación de doce cuentos populares en tapa dura.", "libro", 3, 8, ["lectura", "fantasía"], [SP, SS, SPP, MR], 0.7, True),
    ("Libro de experimentos sencillos", "50 experimentos con materiales de casa.", "libro", 7, 12, ["ciencia", "lectura"], [SP, SS, SPP, MR], 0.5, True),
    ("Atlas ilustrado de animales", "Atlas de gran formato con animales de los cinco continentes.", "libro", 6, 12, ["animales", "lectura", "naturaleza"], [SP, SS, SPP, MR], 0.9, False),
    ("Libro de tela para bebé", "Libro blando con texturas y colores contrastados.", "bebe", 0, 2, ["sensorial", "lectura"], [SP, SS, SPP, SE, MR], 0.2, True),
    ("Xilófono de madera", "Xilófono de ocho notas con dos baquetas.", "musica", 2, 6, ["música"], [SP, SPP, MR, FD], 0.6, True),
    ("Teclado musical infantil", "Teclado de 32 teclas con ritmos. Funciona con pilas.", "musica", 4, 10, ["música"], [MR], 1.0, False),
    ("Set de percusión infantil", "Maracas, pandereta y tambor pequeño.", "musica", 3, 8, ["música", "baile"], [SP, MR], 0.8, True),
    ("Balón de fútbol talla 4", "Balón cosido de talla 4, fuera de catálogo.", "deporte", 6, 12, ["fútbol", "deporte"], [SP, SS, FD], 0.4, True),
    ("Canasta de baloncesto ajustable", "Canasta con pie regulable de 1,2 a 1,8 m y balón.", "deporte", 5, 12, ["baloncesto", "deporte"], [SP, SS], 3.5, False),
    ("Patines en línea con protecciones", "Patines ajustables (tallas 30-33) con rodilleras y coderas.", "deporte", 7, 13, ["deporte"], [SP, SS], 2.2, True),
    ("Comba y raquetas de playa", "Comba con mangos de madera y dos palas con pelota.", "deporte", 5, 12, ["deporte", "agua"], [SP, SS], 0.6, False),
    ("Cometa de colores", "Cometa de nailon con cordel y carrete.", "deporte", 6, 14, ["deporte", "naturaleza"], [SP, SS], 0.3, False),
    ("Caja de acuarelas y pinceles", "24 colores, tres pinceles y bloc de papel.", "manualidades", 6, 14, ["dibujo"], [SP, SS, MR], 0.4, True),
    ("Maletín de dibujo con 80 piezas", "Ceras, rotuladores, lápices de colores y témperas en maletín.", "manualidades", 5, 12, ["dibujo"], [SP, SS, MR], 0.9, True),
    ("Set de plastilina con moldes", "Ocho colores de plastilina y moldes de animales.", "manualidades", 3, 8, ["manualidades"], [SP, SS, MR, FD], 0.7, True),
    ("Kit para hacer pulseras", "Hilos de colores y abalorios para hacer pulseras.", "manualidades", 7, 13, ["manualidades"], [SP, SS, MR], 0.3, False),
    ("Pizarra magnética doble cara", "Pizarra de tiza y rotulador con letras y números magnéticos grandes.", "manualidades", 3, 8, ["dibujo", "números"], [SP, SS, SPP, FD, MR], 2.0, True),
    ("Sonajeros de colores", "Pack de tres sonajeros de plástico sin piezas sueltas.", "bebe", 0, 1, ["sensorial"], [SP, SPP, FD, SE, MR], 0.2, True),
    ("Cubos apilables con texturas", "Ocho cubos blandos con texturas para apilar.", "bebe", 0, 2, ["sensorial", "construcción"], [SP, SS, SPP, FD, SE, MR], 0.5, True),
    ("Gimnasio de actividades para bebé", "Manta acolchada con arco y figuras colgantes cosidas.", "bebe", 0, 1, ["sensorial"], [SP, SPP, SE], 1.5, False),
    ("Mordedor de silicona", "Mordedor de silicona alimentaria, apto para lavavajillas.", "bebe", 0, 1, ["sensorial"], [SP, SS, SPP, FD, SE, MR], 0.1, False),
    ("Disfraz de astronauta", "Mono de astronauta con casco de espuma (talla 5-7 años).", "disfraz", 5, 7, ["disfraces", "espacio"], [SP, SS], 0.5, True),
    ("Disfraz de caballero con capa", "Túnica, capa y escudo de espuma.", "disfraz", 4, 8, ["disfraces", "caballeros"], [SP, SS], 0.5, False),
    ("Disfraz de bombero", "Chaqueta y casco de bombero de plástico ligero.", "disfraz", 3, 6, ["disfraces", "oficios"], [SP, SS], 0.5, True),
    ("Capa y antifaz de superhéroe", "Capa de tela con cierre de velcro y antifaz.", "disfraz", 3, 8, ["disfraces", "superhéroes"], [SP, SS, SPP], 0.2, False),
    ("Proyector de estrellas y planetas", "Lámpara que proyecta constelaciones en el techo. Funciona con pilas.", "ciencia", 4, 10, ["espacio"], [SPP, FD], 0.6, True),
    ("Cohete espacial para montar", "Cohete de 120 piezas con astronautas y plataforma de lanzamiento.", "construccion", 5, 10, ["espacio", "construcción"], [SP, SS], 0.8, False),
    ("Kit de ciencia: volcanes y cristales", "Experimentos de química segura con guía ilustrada.", "ciencia", 8, 14, ["ciencia"], [SP, SS], 0.9, True),
    ("Kit de explorador de bichos", "Lupas, caja observatorio y guía de insectos.", "ciencia", 5, 10, ["naturaleza", "exploración", "ciencia"], [SP, SS, FD], 0.4, True),
    ("Juego de imanes y circuitos", "Experimentos de electricidad con pilas y bombillas.", "ciencia", 8, 14, ["ciencia"], [SS], 0.6, False),
    ("Juego de estrategia y comercio", "Juego de mesa de estrategia para 3-6 jugadores.", "juego_mesa", 12, 99, ["juegos de mesa"], [SP, SS, MR], 1.0, True),
    ("Kit de programación sin pantallas", "Tarjetas y un pequeño robot de madera que sigue instrucciones.", "ciencia", 6, 12, ["robots", "números"], [SS], 0.7, False),
    ("Pack de novelas juveniles de aventuras", "Tres novelas juveniles de aventuras y misterio.", "libro", 11, 16, ["lectura", "exploración"], [SP, SS, SPP, MR], 0.9, True),
    ("Porterías de fútbol plegables", "Dos porterías plegables con conos y balón blando.", "deporte", 4, 12, ["fútbol", "deporte"], [SP, SS], 1.5, False),
    ("Ukelele infantil", "Ukelele de madera de 53 cm con funda.", "musica", 6, 14, ["música"], [SP, MR], 0.6, True),
]

CARTAS = [
    (6, "Queridos Reyes Magos: este año me he portado bien. Me encantan los dinosaurios y pintar con mi abuela."),
    (8, "Hola Reyes, quiero algo para jugar al fútbol en el parque con mis amigos del barrio."),
    (9, "Me gustaría un libro de animales porque de mayor quiero ser veterinaria."),
    (7, "Os pido un juego para jugar todos juntos en casa los domingos."),
    (4, "Quiero un peluche para dormir abrazado porque a veces me da miedo la noche."),
    (5, "Me gustan mucho los trenes y los coches. Gracias por venir."),
    (6, "Me gustaría un disfraz de astronauta para ir a la luna."),
    (8, "Quiero aprender a tocar música como mi tía [nombre]."),
    (10, "Querido Baltasar: me gustan los puzles difíciles y la ciencia."),
    (4, "Quiero una cocinita para hacer comiditas a mi hermano [nombre]."),
    (5, "Me gusta construir torres muy altas y que no se caigan."),
    (7, "Os pido algo para pintar, que se me acabaron las pinturas del cole."),
]

FUENTES = ["qr-punto-deusto", "qr-punto-santutxu", "linkedin", "entidad-caritas", "instagram", "directo"]


def _f(d: datetime) -> str:
    return d.isoformat(timespec="seconds")


def cargar(semilla: int = 2026) -> None:
    rnd = random.Random(semilla)
    ahora = datetime.now().replace(microsecond=0)
    inicio = ahora - timedelta(days=42)

    for p in PUNTOS:
        db.insertar("puntos", dict(zip(["nombre", "barrio", "direccion", "horario", "lat", "lon"], p)))
    for e in ENTIDADES:
        db.insertar("entidades", dict(zip(["codigo", "nombre", "tipo", "email"], e)))
    for o in ORGANIZACIONES:
        db.insertar("organizaciones", dict(zip(["codigo", "nombre", "tipo", "contacto", "email", "barrio"], o)))
    emp_ids = [db.insertar("empresas", dict(zip(["nombre", "contacto", "email", "sector"], e))) for e in EMPRESAS]

    fin = "2027-01-06"
    camp_ids = [
        db.insertar("campanas", {"codigo": "LANTEGI-2026", "nombre": "Campaña Reyes 2026 · Lantegi Berria",
                                 "empresa_id": emp_ids[0], "objetivo_juguetes": 120, "aportacion": 1500.0,
                                 "fecha_inicio": _f(inicio - timedelta(days=7))[:10], "fecha_fin": fin,
                                 "zona": "Deusto y Rekalde", "estado": "activa", "creado": _f(inicio)}),
        db.insertar("campanas", {"codigo": "TXOKOA-2026", "nombre": "Campaña Reyes 2026 · Kafe Txokoa",
                                 "empresa_id": emp_ids[1], "objetivo_juguetes": 60, "aportacion": 800.0,
                                 "fecha_inicio": _f(inicio)[:10], "fecha_fin": fin,
                                 "zona": "Santutxu y Otxarkoaga", "estado": "activa", "creado": _f(inicio)}),
    ]

    # Costes semanales por campaña (alimentan coste por juguete y destino de la aportación)
    for semana in range(6):
        fecha = _f(inicio + timedelta(days=7 * semana + 5))
        for cid in camp_ids:
            for concepto, (a, b) in {"Recogida": (10, 15), "Entrega": (12, 17), "Revisión": (6, 9),
                                     "Gestión": (4, 6)}.items():
                db.insertar("costes", {"campana_id": cid, "concepto": concepto, "importe": round(rnd.uniform(a, b), 2),
                                       "fecha": fecha, "nota": "Datos de demostración"})

    # Necesidad aprobada del colegio (destino de parte de las entregas)
    nec_id = db.insertar("necesidades", {
        "organizacion_id": 4, "nombre_entidad": ORGANIZACIONES[3][1], "tipo": "Centro educativo",
        "contacto": ORGANIZACIONES[3][3], "email": ORGANIZACIONES[3][4], "codigo": "ORG-GOIKOA",
        "ninos": db.a_json({"3-5": 6, "6-8": 8}), "categorias": "[]", "restricciones": "[]", "juguetes_por_nino": 1,
        "fecha_limite": _f(ahora - timedelta(days=10))[:10], "entrega": "Punto de encuentro", "propuesta": "{}",
        "estado": "aprobada", "demo": 1, "creado": _f(ahora - timedelta(days=30))})

    # Juguetes: primera copia de cada plantilla + segunda copia de una de cada tres
    lotes = [(t, 1) for t in JUGUETES] + [(t, 2) for i, t in enumerate(JUGUETES) if i % 3 == 0]
    ciclo_segundas = ["entregado", "revision", "entregado", "pedido_activo", "temprano", "entregado",
                      "eleccion", "pedido_activo", "entregado", "online", "eleccion", "rechazado"]
    cartas_ids: list[int] = []
    for edad, texto in CARTAS:
        cartas_ids.append(db.insertar("cartas", {"entidad_id": rnd.randint(1, 3), "nino_ref": f"N-{rnd.randint(1000, 9999)}",
                                                 "edad": edad, "texto_anon": texto, "intereses": "[]", "categorias": "[]",
                                                 "rechazos": "[]", "objetos": "[]", "modo": "reglas", "demo": 1,
                                                 "creado": _f(inicio + timedelta(days=rnd.randint(3, 30)))}))
    n_segunda = 0
    for idx, (t, copia) in enumerate(lotes):
        nombre, desc, cat, emin, emax, intereses, restr, peso, en_stock = t
        if copia == 1:
            destino = "publicado" if en_stock else "entregado"
        else:
            destino = ciclo_segundas[n_segunda % len(ciclo_segundas)]
            n_segunda += 1
        estado_fisico = rnd.choice(["Nuevo con caja", "Nuevo sin caja", "Fuera de catálogo", "Tara estética",
                                    "Fuera de catálogo"])
        punto_id = rnd.randint(1, 4)
        es_empresa = rnd.random() < 0.25
        # fechas: las entregadas empezaron antes; las que esperan respuesta del donante, hace poco
        if destino == "entregado":
            d0 = inicio + timedelta(days=rnd.randint(0, 24), hours=rnd.randint(9, 19))
        elif destino in ("temprano", "online"):
            d0 = ahora - timedelta(days=rnd.randint(0, 1), hours=rnd.randint(1, 8))
        elif destino == "eleccion":
            d0 = ahora - timedelta(days=rnd.randint(3, 6), hours=rnd.randint(1, 8))
        elif destino == "revision":
            d0 = ahora - timedelta(days=rnd.randint(6, 9), hours=rnd.randint(1, 8))
        else:
            d0 = inicio + timedelta(days=rnd.randint(4, 28), hours=rnd.randint(9, 19))
        codigo = db.nuevo_codigo("FB-DON", "donaciones")
        modo = "domicilio" if rnd.random() < 0.45 else "punto"
        don = {"codigo": codigo, "tipo": "empresa" if es_empresa else "particular",
               "email": f"donante{idx}@correo.ejemplo", "punto_id": punto_id, "estado": "registrada", "demo": 1,
               "creado": _f(d0), "campana_id": None}
        if es_empresa:
            emp = EMPRESAS[rnd.randint(0, 1)]
            don.update({"empresa_nombre": emp[0], "contacto": emp[1], "email": emp[2], "producto": nombre,
                        "unidades": 1, "motivo": "Fuera de catálogo", "edad_texto": f"{emin}-{emax}",
                        "entrega_modo": "recogida_empresa"})
        don_id = db.insertar("donaciones", don)
        hist = [("registrada", d0)]
        estado_don = "registrada"
        reloj = [d0]

        def paso(estado: str, h1: int, h2: int, lista: list = hist) -> datetime:
            t_ = reloj[0] + timedelta(hours=rnd.randint(h1, h2))
            if t_ > ahora - timedelta(minutes=20):
                t_ = max(reloj[0] + timedelta(minutes=5), ahora - timedelta(minutes=rnd.randint(20, 300)))
            reloj[0] = t_
            lista.append((estado, t_))
            return t_

        ped_pasos: list[str] = []      # pasos del pedido, en orden
        estado_jug = "en_revision"
        motivo = None
        if es_empresa:
            if destino in ("temprano", "online"):
                if modo == "domicilio":
                    paso("recogida_programada", 2, 10)
                    estado_don = "recogida_programada"
            elif destino in ("eleccion", "revision"):
                paso("recibida", 20, 48)
                estado_don = "recibida"
            elif destino == "rechazado":
                paso("recibida", 20, 48)
                paso("rechazada", 4, 30)
                estado_don, estado_jug, motivo = "rechazada", "rechazado", "Pieza suelta pequeña sin sujeción"
            else:
                paso("recibida", 20, 48)
                paso("revisada", 4, 30)
                paso("publicada", 2, 12)
                estado_don, estado_jug = "publicada", "publicado"
                if destino in ("entregado", "pedido_activo"):
                    ped_pasos = ["solicitado", "revisado"]
        else:
            if destino in ("temprano", "online"):
                pass                                           # esperando la revisión online de las fotos
            elif destino == "rechazado":
                paso("rechazada_online", 3, 30)
                estado_don, estado_jug = "rechazada_online", "rechazado"
                motivo = "Las fotos no permiten comprobar el estado del juguete"
            else:
                paso("publicada", 3, 30)
                estado_don, estado_jug = "publicada", "publicado"
                if destino != "publicado":
                    if destino == "eleccion":
                        reloj[0] = ahora - timedelta(hours=rnd.randint(30, 60))
                    paso("emparejada", 24, 96)
                    estado_don = "emparejada"
                    ped_pasos = ["solicitado"]
                    db.actualizar("donaciones", don_id, {"plazo_eleccion": _f(reloj[0] + timedelta(days=3))})
                if destino in ("revision", "pedido_activo", "entregado"):
                    eleccion = "recogida_programada" if modo == "domicilio" else "llevar_a_punto"
                    paso(eleccion, 4, 40)
                    db.actualizar("donaciones", don_id, {
                        "entrega_modo": modo, "franja_horaria": "Tarde (16-20 h)" if modo == "domicilio" else None,
                        "direccion": "Dirección de demostración" if modo == "domicilio" else None})
                    paso("recibida", 12, 48)
                    estado_don = "recibida"
                    ped_pasos.append("en_recogida")
                if destino in ("pedido_activo", "entregado"):
                    paso("revisada", 3, 24)
                    estado_don = "revisada"
                    ped_pasos.append("revisado")

        jug_id = db.insertar("juguetes", {
            "nombre": nombre, "descripcion": desc, "categoria": cat, "edad_min": emin, "edad_max": emax,
            "intereses": db.a_json(intereses), "restricciones": db.a_json(restr), "estado_fisico": estado_fisico,
            "punto_id": punto_id, "peso_kg": peso, "fotos": "[]", "estado": estado_jug, "donacion_id": don_id,
            "demo": 1, "creado": _f(d0)})

        if ped_pasos:
            a_org = rnd.random() < 0.3
            edad = max(emin, min(emax, rnd.randint(emin, min(emax, 12))))
            punto = PUNTOS[punto_id - 1]
            ped_campana = camp_ids[0] if rnd.random() < 0.62 else camp_ids[1]
            modo_ped = "punto" if rnd.random() < 0.6 else "domicilio"
            ped = {"codigo": db.nuevo_codigo("FB-PED", "pedidos"), "juguete_id": jug_id,
                   "destino": "organizacion" if a_org else "familia", "edad": edad, "franja": db.franja_de_edad(edad),
                   "modo_entrega": modo_ped, "punto_id": punto_id,
                   "barrio": punto[1], "estado": "solicitado", "campana_id": ped_campana, "demo": 1,
                   "creado": _f(hist[-1][1])}
            if a_org:
                ped.update({"organizacion_id": 4, "necesidad_id": nec_id, "email": ORGANIZACIONES[3][4]})
            else:
                ent = rnd.randint(1, 3)
                familia = rnd.randint(1, 26)
                ped.update({"entidad_id": ent, "familia_ref": f"F-DEMO-{familia}",
                            "nino_ref": f"N-DEMO-{familia}-{rnd.randint(1, 2)}", "email": ENTIDADES[ent - 1][3],
                            "carta_id": rnd.choice(cartas_ids)})
            ped_id = db.insertar("pedidos", ped)
            db.actualizar("juguetes", jug_id, {"campana_id": ped_campana, "estado": "reservado"})
            # fechas del pedido: las mismas que los pasos de la donación que lo provocan
            fechas_don = dict(hist)
            hist_ped = []
            for p in ped_pasos:
                if p == "solicitado":
                    fecha = fechas_don.get("emparejada") or paso("asignada", 6, 72)
                    if es_empresa:
                        estado_don = "asignada"
                elif p == "en_recogida":
                    fecha = fechas_don.get("recogida_programada") or fechas_don.get("llevar_a_punto")
                else:
                    fecha = fechas_don.get("revisada") if not es_empresa else reloj[0] + timedelta(minutes=10)
                hist_ped.append((p, fecha))
            if "revisado" in ped_pasos:
                resto = ["preparado", "en_camino" if modo_ped == "domicilio" else "listo_punto", "entregado"]
                if destino == "pedido_activo":
                    resto = resto[: rnd.randint(0, 2)]
                for p in resto:
                    hist_ped.append((p, paso(p, 6, 40, [])))
            for estado, fecha in hist_ped:
                db.insertar("historial", {"objeto": "pedido", "objeto_id": ped_id, "estado": estado, "fecha": _f(fecha),
                                          "nota": "Datos de demostración"})
            db.actualizar("pedidos", ped_id, {"estado": hist_ped[-1][0]})
            if hist_ped[-1][0] == "entregado":
                hist.append(("entregada", hist_ped[-1][1]))
                estado_don = "entregada"
                db.actualizar("juguetes", jug_id, {"estado": "entregado"})

        for estado, fecha in hist:
            db.insertar("historial", {"objeto": "donacion", "objeto_id": don_id, "estado": estado, "fecha": _f(fecha),
                                      "nota": "Datos de demostración"})
        db.actualizar("donaciones", don_id, {"estado": estado_don, **({"motivo_rechazo": motivo} if motivo else {})})

    # Eventos del embudo (sesiones simuladas con orígenes variados)
    for s in range(160):
        publico = rnd.choices(list(EMBUDOS), weights=[30, 8, 35, 10, 17])[0]
        src = rnd.choices(FUENTES, weights=[18, 10, 14, 16, 12, 30])[0]
        t_ = inicio + timedelta(days=rnd.uniform(0, 41))
        for paso in EMBUDOS[publico]:
            db.insertar("eventos", {"ts": _f(t_), "sesion": f"demo-{s}", "src": src, "publico": publico,
                                    "evento": paso, "objeto": "demo"})
            if rnd.random() > 0.62:
                break
            t_ += timedelta(minutes=rnd.randint(1, 15))

    for asunto, dest in [("Hemos registrado tu donación", "donante3@correo.ejemplo"),
                         ("Pedido registrado", ENTIDADES[0][3]),
                         ("Tu juguete ya tiene nuevo dueño", "donante7@correo.ejemplo")]:
        db.insertar("notificaciones", {"destinatario": dest, "asunto": f"{asunto} (demo)",
                                       "cuerpo": "Mensaje de ejemplo generado por los datos de demostración.",
                                       "estado": "En bandeja (SMTP no configurado)", "objeto": "demo",
                                       "creado": _f(ahora - timedelta(days=rnd.randint(1, 10)))})
