PARTE 1: Identificar el núcleo 
1. Regla de Negocio: Invariante de Cupos (Cero sobrecupos)
¿Por qué es negocio y no infraestructura?
Esta es una regla de la realidad de la universidad: un proyecto físico solo tiene espacio para "x" número de personas. Debe cumplirse obligatoriamente sin importar si estamos guardando la información en un servidor ultramoderno de Google, en un archivo de Excel o anotándolo en una libreta de papel.

Entidades involucradas y atributos principales:

Entidad Vacancy (Vacante):
id (Identificador único)
available_slots (Número de cupos disponibles)
is_closed (Verdadero/Falso para saber si ya se llenó)

2. Regla de Negocio: Postulación única activa (No duplicar solicitudes)
¿Por qué es negocio y no infraestructura?
Es una política administrativa de la plataforma para mantener el orden y la justicia, evitando que un alumno sature la bandeja de un líder enviando su solicitud 20 veces. Esta prohibición es un acuerdo humano, no tiene nada que ver con qué framework web (Vue.js o React) dibuje la pantalla.

Entidades involucradas y atributos principales:

Entidad Application (Postulación):
id (Identificador de la solicitud)
vacancy_id (A qué vacante aplica)
student_id (Quién la solicita)
status (PENDIENTE, ACEPTADA o RECHAZADA)

3. Regla de Negocio: Restricción de propiedad (El líder no se postula a su propio proyecto)
¿Por qué es negocio y no infraestructura?
Es puro sentido común del dominio: tú no puedes pedir permiso para entrar a un equipo que tú mismo creaste y diriges. Es una norma de comportamiento intrínseca del sistema de reclutamiento, independiente de si usamos bases de datos relacionales (PostgreSQL) o no relacionales (MongoDB).

Entidades involucradas y atributos principales:

Entidad Project (Proyecto):
id (Identificador del proyecto)
leader_id (Identificador del estudiante creador)
Entidad Application (Postulación):
student_id (Para compararlo con el leader_id del proyecto y bloquearlo si son la misma persona).

PARTE 2: Diseño por capas
1. Regla: Invariante de Cupos (Cero sobrecupos)
Entity con validaciones: Vacancy (Vacante).
Validación: Tiene un método decrementar_cupo(). Si los cupos_disponibles son 0, lanza una excepción de dominio (DomainException: "Vacante llena"). Si es mayor a 0, resta 1 y, si llega a 0 en ese momento, cambia el estado is_closed a verdadero.
Use Case: AcceptApplicationUseCase
Entrada: application_id (ID de la solicitud), leader_id (quien acepta).
Salida: Datos de la solicitud actualizada a estado ACEPTADA.
Pasos:
Obtener la solicitud.
Obtener la vacante asociada.
Invocar vacante.decrementar_cupo().
Cambiar estado de la solicitud a ACEPTADA.
Guardar vacante y guardar solicitud en la base de datos.
Interfaz del Repository: IVacancyRepository con los métodos abstractos find_by_id_with_lock(id) y save(vacancy).
Adapter (Implementación): PostgresVacancyRepository. Es una clase que implementa la interfaz conectándose a PostgreSQL mediante consultas SQL o un ORM (como SQLAlchemy).

2. Regla: Postulación única activa (No duplicar solicitudes)
Entity con validaciones: Application (Postulación).
Validación: Al instanciarse (Application.create(...)), la entidad exige nacer obligatoriamente con el estado PENDIENTE.
Use Case: ApplyToVacancyUseCase
Entrada: student_id (ID del alumno), vacancy_id (ID de la vacante).
Salida: La nueva Application creada.
Pasos:
Consultar a través de la interfaz si el estudiante ya tiene una solicitud activa en esa vacante.
Si la respuesta es afirmativa, abortar lanzando un error.
Si no existe, crear la entidad Application.
Guardar la nueva solicitud en la base de datos.
Interfaz del Repository: IApplicationRepository con el método abstracto has_active_application(student_id, vacancy_id) -> bool y save(application).
Adapter (Implementación): PostgresApplicationRepository, que ejecuta un SELECT COUNT(...) en la base de datos PostgreSQL para verificar duplicados.

3. Regla: Restricción de propiedad (El líder no se postula)
Entity con validaciones: Project (Proyecto).
Validación: Tiene un método validar_candidato(student_id). Si el student_id es exactamente igual a su leader_id, lanza una excepción (DomainException: "El líder no puede postularse").
Use Case: ApplyToVacancyUseCase (Se ejecuta en el mismo flujo de postulación).
Entrada: student_id, project_id.
Salida: Pasa al siguiente paso (crear la postulación).
Pasos:
Obtener el proyecto de la base de datos.
Invocar proyecto.validar_candidato(student_id).
Si la validación pasa, continuar con el flujo normal de crear la postulación.
Interfaz del Repository: IProjectRepository con el método abstracto find_by_id(id).
Adapter (Implementación): PostgresProjectRepository, que recupera los datos del proyecto desde la base de datos.

Diagrama de Capas (Dirección de Dependencias)
[ CAPA 4: INFRAESTRUCTURA Y FRAMEWORKS ]
(Vue.js, FastAPI, PostgreSQL, Render)
                  │
                  │ Llama a / Implementa
                  ▼
[ CAPA 3: ADAPTADORES DE INTERFAZ ]
(Controllers REST, PostgresVacancyRepository, DTOs)
                  │
                  │ Depende de / Usa
                  ▼
[ CAPA 2: CASOS DE USO / APLICACIÓN ]
(AcceptApplicationUseCase, IVacancyRepository - Interfaz)
                  │
                  │ Depende de / Usa
                  ▼
[ CAPA 1: DOMINIO / NÚCLEO ]
(Entidades: Vacancy, Application, Project y Reglas de Negocio)

* Nota de arquitectura: La capa 1 no tiene ninguna flecha 
  saliendo de ella. Es independiente de todo el sistema.

PARTE 4: Swap de infraestructura
¿Tuvimos que cambiar el Use Case o la Entity?
No. Absolutamente ni una sola línea de código cambió en las capas internas.

El código original del AcceptApplicationUseCase y de las entidades Vacancy y Application permanece idéntico.

¿Por qué funcionó esto sin romperse?
Porque el caso de uso depende de la abstracción (IVacancyRepository), no del detalle tecnológico. Al caso de uso no le importa si los datos vienen de la RAM, de un archivo JSON, o de PostgreSQL; solo le importa que el objeto que le inyectamos tenga los métodos find_by_id() y save(). Esto demuestra el principio de Inversión de Dependencias (DIP).

Si hubiera tenido que modificar el Use Case para usar JSON, significaría que la Capa 2 (Aplicación) estaba acoplada a la Capa 4 (Infraestructura). La forma de corregirlo siempre es crear una Interfaz en el medio (Capa 2 o 3) y obligar a la infraestructura a cumplir ese contrato.

PARTE 5: Cierre
¿Qué parte de su proyecto les costó más ubicar en una capa?
La integración del motor de recomendaciones y la búsqueda de similitud con embeddings (vectores semánticos). Al principio, definir la coincidencia entre el perfil de un estudiante y los requisitos de un proyecto parecía una regla de negocio pura que debía ir en el Dominio. Sin embargo, la ejecución real depende fuertemente de tecnología específica (pgvector en PostgreSQL). Resolvimos el dilema aislando el concepto: creamos un contrato abstracto (IProjectVectorRepository) en la capa de Casos de Uso que define qué necesitamos (buscar proyectos similares), pero empujamos el cómo (la matemática vectorial y la base de datos) a la capa más externa de Infraestructura.

¿Qué ganan con poder cambiar la infraestructura sin tocar el núcleo?
Inmunidad ante la obsolescencia tecnológica y una testeabilidad absoluta. A nivel técnico, esto nos permite correr cientos de pruebas unitarias en milisegundos usando repositorios falsos en memoria, sin depender de levantar contenedores Docker o conexiones a internet. A nivel estratégico, blindamos el verdadero valor de DevConnect Campus (las reglas de cupos, el flujo de postulaciones y los roles); si mañana la universidad decide abandonar Render por AWS, cambiar PostgreSQL por MongoDB, o migrar la interfaz de Vue.js a React, el corazón lógico de nuestro sistema no requerirá modificar ni una sola línea de código.