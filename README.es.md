# LüJi · Una trayectoria profesional que sigue creciendo

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · Español

**Convierte tu agente en un asesor de desarrollo profesional que conecte tu experiencia, las acciones de hoy y tus próximos rumbos.**

![Ejemplo ficticio de conversación y registros profesionales de LüJi](assets/readme-preview.jpg)

```text
Instala lvji-career-kit desde https://github.com/siliviasilivia85-lang/lvji-career-kit y ayúdame a ordenar una experiencia.
```

[Instalación y entornos compatibles](references/install.md) · Instala una vez y después conversa con naturalidad.

## Por qué LüJi

Muchas veces empezamos a pensar en serio en nuestro siguiente paso profesional cuando el trabajo actual ya no nos deja espacio para crecer.

Entonces todo llega a la vez: recuperar proyectos antiguos, rehacer el currículum, elegir un rumbo y preparar entrevistas. Hemos trabajado y aprendido mucho, pero los registros están dispersos y cuesta explicar qué hemos construido con esa experiencia. Si queremos explorar varios tipos de puesto, necesitamos además distintas versiones del currículum. Es fácil acabar buscando empleo por la urgencia de cambiar, antes de haber comprendido hacia dónde queremos ir.

Un currículum puede cambiar en unos días. Una práctica sólida y una capacidad que podamos llevar a otro contexto necesitan más tiempo. A medida que la IA transforma los límites y las exigencias del trabajo, el desarrollo profesional necesita un lugar en nuestra vida cotidiana, mucho antes de una búsqueda urgente de empleo.

**LüJi te ayuda a construir una trayectoria de crecimiento con continuidad: recuperar lo aprendido, dar a tus posibilidades futuras un lugar en las acciones de hoy y llevar sus resultados a tu próxima decisión.**

Ofrece al agente que ya utilizas un método, herramientas para archivos locales y vistas de tus registros, para que pueda acompañarte como asesor de desarrollo profesional. La experiencia queda en archivos legibles que puedes revisar, corregir y conservar. Con el tiempo, la preparación deja de ser una serie de esfuerzos aislados y se convierte en un proceso que puedes retomar y hacer crecer.

## Conectar el pasado, el presente y el futuro

### Pasado: reconocer lo que has construido

El trabajo, los proyectos, los estudios y los aprendizajes merecen conservarse y revisitarse. LüJi los organiza en registros pequeños y con nombre propio, mantiene los originales y sus fuentes, y permite añadir detalles que habías olvidado. A partir de ellos, el agente puede ayudarte a reconocer experiencia, preferencias y capacidades transferibles. También puedes elegir un camino que se aleje de lo que has hecho hasta ahora.

### Presente: dar al crecimiento un lugar en una semana real

Seguir creciendo tiene que ser compatible con la vida que ya tienes: hay trabajo pendiente, el tiempo disponible es limitado y surgen imprevistos. LüJi parte de tus circunstancias y del tiempo que realmente puedes dedicar, y convierte ideas en proyectos, resultados intermedios y acciones diarias, semanales y mensuales. Cuando algo no avanza, puedes reducir el siguiente paso, cambiar el ritmo y decidir qué merece continuar.

### Futuro: dejar que varios rumbos compartan la misma experiencia

Puedes tener más de un objetivo profesional. Muchas de las capacidades que requieren se solapan: un proyecto, un aprendizaje o una práctica de trabajo pueden prepararte para distintas posibilidades. LüJi ayuda a ver esas conexiones y a traducir lo que pide cada objetivo en capacidades y acciones presentes, sin empezar desde cero para cada puesto.

Cuando decidas buscar empleo, podrás seleccionar lo más relevante de tu experiencia y tus resultados, preparar currículums para distintos puestos o empresas, ensayar entrevistas y registrar candidaturas, conversaciones y comentarios recibidos. Esa información vuelve al presente para ayudarte a revisar tus decisiones y ajustar lo que haces después.

La continuidad también necesita evidencias reales. Terminar una tarea registra un avance; un trabajo concreto o un resultado, revisado contigo, puede respaldar una afirmación sobre tus capacidades. Las actividades y los resultados confirmados siguen disponibles para la planificación, el currículum y las entrevistas. **Cada práctica deja algo que conservar; cada decisión puede traer una nueva comprensión de tu recorrido.**

Las conexiones se construyen poco a poco y los objetivos pueden cambiar con la experiencia. Los cambios importantes se presentan primero como un borrador concreto para que lo revises y decidas si guardarlo. Puedes explorar sin crear un objetivo, conservar una idea sin iniciar un proyecto y cerrar una etapa sin comprometerte todavía con la siguiente.

## Primeros pasos: empieza por una experiencia

Elige algo que conozcas bien: un proyecto anterior, una etapa de trabajo o una experiencia de aprendizaje. Puede servir una parte de tu currículum, una retrospectiva de proyecto o unas notas. Si no tienes un documento, puedes escribir lo que ocurrió. No hace falta preparar todo tu archivo profesional de una vez.

Si aún no tienes materiales anteriores, empieza por lo que quieres explorar ahora. Podrás añadir tu experiencia más adelante o guardar una idea por separado, sin crear un objetivo ni fijar un calendario.

1. **Crea tu espacio de trabajo.** Descarga el paquete y ábrelo, o autoriza el acceso a su carpeta, en tu agente habitual. Pídele que lea `AGENTS.md` y `SKILL.md` en la raíz, cree un espacio personal y muestre su mapa. Las guías generadas admiten chino (`--language zh`) o inglés (`--language en`); elige una de esas dos opciones, aunque converses en español. Este paso se realiza al empezar; después basta con conversar normalmente. El flujo completo necesita lectura, escritura y ejecución de archivos locales, además de Python 3.10+.
2. **Añade el material de esa experiencia.** Colócalo en `past/materials/` dentro de tu espacio, o en `inbox/` si no sabes dónde clasificarlo. También puedes entregar un archivo adjunto al agente y pedirle que lo importe y organice. Los originales que añadas directamente conservan su nombre y ubicación. Las notas, los PDF, los documentos de Word y las imágenes no necesitan campos internos; la interpretación fiable de los adjuntos depende del agente que utilices.
3. **Revisa el relato junto al agente.** Preparará un borrador de lo que hiciste, tu responsabilidad y los resultados, indicando fuentes e información pendiente. Completa lo que falte y corrige su interpretación. Solo después de aprobar ese borrador se guarda como registro Markdown; los originales siguen disponibles. Puedes editar directamente el texto del registro. Las fechas y los estados de las tareas tienen campos específicos: pedir al agente que los ajuste suele ser la opción más sencilla.
4. **Mira el resultado en la vista general.** Pide al agente que genere y muestre el panel. En Vista general (`总览`), despliega el apartado de experiencia anterior (`来路与当前理解`) y abre el registro guardado y sus fuentes. Corrige lo necesario con el agente o en Markdown y vuelve a generar la página. Actualmente la web permite consultar y seleccionar; los cambios se guardan mediante el agente o los archivos, no directamente en la página.
5. **Elige un siguiente paso útil.** Habla de un proyecto o una acción que encaje con tu situación y tu tiempo disponible. Puede apoyar un objetivo futuro o avanzar de forma independiente. Cuando apruebes guardarlo, podrás consultar las acciones en el plan unificado.

Al terminar deberías poder encontrar el original, entender el registro, saber cómo corregirlo y tener un punto claro desde el que continuar. Para familiarizarte primero con materiales ficticios, pide al agente que siga [la guía de prueba](examples/try-it.md) en un directorio temporal nuevo.

## Dónde poner los materiales

Las rutas siguientes pertenecen a tu espacio profesional. Para empezar, se recomienda `~/lvji-workspace/`, fuera de la carpeta donde se instala el Skill. Los espacios existentes conservan su ubicación confirmada; no se trasladan automáticamente.

| Lo que tienes | Dónde ponerlo |
| --- | --- |
| Currículums anteriores, certificados, materiales de trabajo o proyectos, notas de aprendizaje | `past/materials/`; puedes crear subcarpetas por tema |
| Materiales compartidos de tu actividad actual | `present/materials/` |
| Materiales de un proyecto concreto en curso | `present/items/<item>/materials/` |
| Investigación sobre rumbos profesionales o descripciones de puesto aún sin asignar | `future/materials/` |
| JD, capturas o comentarios de un rumbo o una oportunidad de una empresa | Su propia carpeta `materials/` |
| Contenido que todavía no sabes clasificar | `inbox/` |

`MAP.md` es el mapa de tus archivos para consulta personal; `AGENT-MAP.md` orienta al agente para localizar solo lo que necesita en esa tarea. Ambos se generan a partir del mismo catálogo. Puedes añadir archivos por tu cuenta: la siguiente vez que abordes una cuestión relacionada, el agente comprobará los cambios en esa zona, leerá lo necesario y revisará contigo lo que conviene organizar. Detectar un archivo, comprenderlo y confirmar una experiencia son pasos distintos.

La entrada del espacio en inglés es `START-HERE.md`; en chino, `从这里开始.md`. Las guías de las secciones y los mapas se generan en chino o inglés. Las carpetas físicas mantienen los nombres `past/`, `present/` y `future/` para que cambiar de idioma o de agente no rompa las referencias. Tus propios nombres de archivo y subcarpetas pueden estar en español u otro idioma.

No hay un monitor de archivos en segundo plano. El agente comprueba la carpeta pertinente cuando se plantea una tarea relacionada. Un `README.md` que tú añadas dentro de una carpeta de materiales también es material; solo se excluyen las guías generadas que la herramienta reconoce como propias.

[Mapa para usuarios, en inglés](references/map.en.md) · [Mapa para el agente, en inglés](references/agent-map.en.md) · [Capacidades del entorno y alternativas](references/hosts.md)

## Un panel, cuatro vistas

El panel principal se genera en **`views/overview.html`** dentro de tu espacio de trabajo. Abre ese archivo y cambia entre sus cuatro pestañas; todas utilizan la misma instantánea de los registros.

| Vista | Qué muestra | Cómo continuar |
| --- | --- | --- |
| **Vista general (`总览`)** | Proyectos en curso, acciones de hoy, avances recientes y apartados desplegables para proyectos terminados o en pausa, ideas y revisiones de etapa | Abre registros y fuentes; la experiencia anterior aparece en `来路与当前理解` |
| **Plan unificado (`统一计划`)** | Lista diaria, calendario semanal, calendario mensual y vista anual, con sus notas y registros | Cambia de escala y consulta acciones; pide al agente que ajuste la planificación |
| **Rumbos (`所向`)** | Direcciones profesionales en horizontal; requisitos, respaldo de evidencias, información disponible y preferencias | Ordena y compara; entra en los detalles de las empresas, los JD y los materiales de currículum y entrevista |
| **Candidaturas (`投递进展`)** | Etapas reales, siguiente paso, historial, comentarios y versión exacta del currículum utilizado cuando se conoce | Consulta todas las oportunidades o filtra por rumbo, empresa, oportunidad o etapa; lo no registrado no se deduce |

Algunos contenidos tienen una entrada propia, pero no constituyen otro panel:

- La **experiencia anterior** se despliega en Vista general; no existe una página principal independiente para el pasado. Los originales y su estado de organización se localizan desde `MAP.md`.
- Los **materiales de entrevista** se abren en los detalles de un rumbo o de una oportunidad de empresa. No hay otra página de inicio para entrevistas.
- Los **currículums web** son archivos HTML con versiones independientes. La versión común de un puesto vive en `future/roles/<role>/common/resumes/<version>/`; la específica de una empresa, en la carpeta `resumes/<version>/` de esa oportunidad. Se accede desde sus versiones existentes. Las seis plantillas son seis diseños, no seis paneles.

Puedes filtrar, ordenar y abrir detalles dentro de la página. Para cambiar un texto, una fecha o un estado, indica al agente qué quieres ajustar, revisa el cambio, apruébalo y vuelve a generar la instantánea. También puedes editar el Markdown. El control opcional para pedir cambios al agente copia una solicitud; no tienes que copiar instrucciones desde la web en el uso cotidiano. Actualmente no hay escritura directa en los registros ni planificación guardada mediante arrastrar y soltar.

**Un filtro cambia lo que ves, no los datos incluidos en el archivo.** El panel completo puede contener todos los registros leídos al generarse. Para compartir información, prepara un documento independiente con un alcance explícito; una página filtrada no es un enlace que aísle los datos de ese puesto.

Las entradas, la generación y las operaciones disponibles se describen en [la guía de visualización](references/views.md). El código de la plantilla está en `assets/md_workspace.html`; necesita los datos del espacio para convertirse en una página utilizable. No es necesario abrir la plantilla para buscar tus registros.

## Currículums y preparación de entrevistas

Pide un currículum para un tipo de puesto o para una empresa concreta. El agente selecciona experiencia real y resultados confirmados, separa con claridad los apartados de educación, trabajo, proyectos y capacidades, y conserva sus fuentes. Los requisitos de un JD o las respuestas de una entrevista simulada no se convierten en experiencia tuya.

Hay seis diseños propios: perfil con columna lateral (`profile-split`, el predeterminado), archivo de evidencias (`evidence-archive`), columna única clásica (`classic-single`), texto sencillo (`ats-minimal`), proyectos primero (`project-first`) y experiencia laboral primero (`experience-first`). Puedes pedir una galería ficticia antes de elegir: muestra la misma experiencia en los seis diseños, con el retrato A, el retrato B o sin foto. Después indica al agente qué diseño prefieres y utiliza tus propios datos y fotografía.

La galería también enlaza siete referencias externas de currículums web en GitHub, con ejemplos oficiales y licencias. Son referencias, no plantillas ya instaladas. Los retratos generados con IA solo se utilizan en demostraciones identificadas como ficticias; un currículum real utiliza la fotografía que tú elijas o no lleva foto. La elección de diseño no está vinculada al género.

Cada generación crea una versión independiente. Una vez que revises y apruebes ese HTML exacto, Chrome/Chromium, si ya está instalado, puede exportar la misma versión a PDF. Un recibo de exportación registra su integridad y la vincula a los archivos congelados. Un PDF antiguo o añadido manualmente sin recibo se muestra como `unverified`. Las actualizaciones del motor de diseño no invalidan un HTML histórico que no ha cambiado; los cambios en las fuentes profesionales se informan por separado, para distinguir una versión antigua intacta de un borrador actual que necesita revisión.

El historial de una candidatura puede referenciar el archivo exacto que utilizaste. Si no se sabe cuál fue, queda como «no registrado»: nunca se supone que enviaste el más reciente. Los relatos para entrevistas, la preparación de cada ronda, la práctica y los comentarios reales reutilizan las mismas evidencias de base. El agente no envía candidaturas ni contacta con empresas.

Los flujos detallados están en [currículums](references/resume.md) y [entrevistas](references/interview.md). Estas referencias operativas están actualmente en chino; el agente las sigue y responde en tu idioma.

## Explora la demostración ficticia

La captura muestra una conversación identificada como ficticia. La demo conecta experiencia, exploración de rumbos, acciones posibles y aprendizaje guardado; los planes, las oportunidades y los currículums muestran los resultados. La web no ejecuta un agente en línea ni guarda datos de visitantes.

Quien mantenga el proyecto puede generar un sitio estático:

```text
python3 scripts/demo_site.py --output _site
```

Utiliza un directorio de salida nuevo. Solo se exportan páginas ficticias de lectura y recursos locales, sin rutas de la máquina, espacios personales ni historial de ejecución. Tras crear el repositorio, selecciona GitHub Actions como origen de Pages y ejecuta manualmente el [flujo de publicación](.github/workflows/pages.yml). Publica solo `_site/`, no todo el repositorio ni un espacio profesional. Tener el flujo preparado no significa que ya exista un sitio publicado.

## Conservar un recorrido que puedas retomar

```text
lvji-career-kit/               El paquete Skill descargado
├── README.md / README.en.md   Guías en chino e inglés
├── README.ja.md / README.ko.md   Guías en japonés y coreano
├── README.es.md              Esta guía en español
├── SKILL.md / AGENTS.md       Entradas para el agente
├── references/                Flujos según la tarea
├── prompts/                   Orientación para perfil, brechas, entrevistas y revisión
├── scripts/                   Herramientas locales de biblioteca estándar
├── assets/                    Plantillas editables y retratos ficticios de demostración
└── examples/                  Pequeños materiales de prueba ficticios

~/lvji-workspace/             Archivos personales separados del Skill instalado; no se distribuyen
├── START-HERE.md          Entrada en inglés; en chino: 从这里开始.md
├── MAP.md / AGENT-MAP.md  Dos mapas del mismo catálogo
├── inbox/                 Originales aún sin clasificar
├── past/                  Experiencia y aprendizaje anteriores
├── present/               Proyectos, acciones, planes, registros, ideas y revisiones
├── future/roles/          Rumbos → empresas → oportunidades
├── views/overview.html    Panel que se puede volver a generar
└── .luji/                 Borradores, historial y configuración de navegación derivada
```

Una experiencia o una acción tienen un único archivo principal. Los distintos rumbos y las escalas diaria, semanal, mensual y anual se refieren a esos mismos registros, sin mantener planes contradictorios.

Una idea puede quedarse en `present/notes/` como `note`. Una revisión en `present/stages/`, de tipo `stage-summary`, reúne lo que ocurrió, los resultados reales, los cambios de criterio y lo que quizá quieras continuar. Referencia los registros existentes en lugar de moverlos o duplicarlos. Guardar una revisión no cierra automáticamente proyectos ni programa la etapa siguiente.

En una conversación nueva, abre tu espacio de trabajo. Sus archivos de entrada permiten localizar el Skill y el contexto guardado. Si mueves el paquete, pide al agente que vuelva a conectarlo siguiendo [el flujo de configuración de navegación](references/navigation.md). La identidad y los registros profesionales permanecen en su sitio. El agente retoma resúmenes guardados; no presume recordar conversaciones que nunca se guardaron.

Puedes editar directamente el cuerpo de los registros. Las fechas y los estados de las acciones proceden de los metadatos `scheduled_for`, `due_on` y `status`. Cambiar una fecha solo en el texto no reprograma la acción. Pide al agente un ajuste preciso o edita el campo correspondiente, conservando los identificadores, los valores JSON válidos y el historial.

## Requisitos y límites actuales

Las herramientas locales requieren Python 3.10+ y no necesitan claves de modelo ni paquetes de Python de terceros. La conversación y la comprensión de adjuntos las aporta tu agente habitual; el paquete no incluye un servicio de modelo independiente. Guardar archivos localmente no significa que el modelo del entorno anfitrión funcione sin conexión. Las vistas pueden mostrarse en un panel integrado, en la conversación o en un navegador, según las capacidades disponibles.

Esta es una **traducción del README**, no una localización completa del producto al español. Puedes conversar con el agente en español. Las guías, mapas y entradas generadas del espacio admiten actualmente chino o inglés (`zh`/`en`), los textos fijos del panel siguen principalmente en chino y buena parte de las referencias operativas también están en chino. Las capacidades y alternativas de visualización de cada entorno se explican en [la guía del entorno anfitrión](references/hosts.md).

No hay recordatorios en segundo plano, monitorización continua ni sincronización de páginas en tiempo real incorporados. Las notificaciones y la voz dependen del entorno. Los formatos antiguos del espacio se conservan y no se migran automáticamente. Las comprobaciones automáticas, las pruebas aisladas de agentes, las verificaciones en navegador y las pruebas de primer uso se explican en [TESTING.md](TESTING.md); no se han probado todos los entornos ni todos los sistemas operativos.

Todos los ejemplos son ficticios. Los espacios personales y los historiales de ejecución quedan fuera de las publicaciones del código fuente. Consulta [ASSETS.md](ASSETS.md) para conocer la procedencia de los recursos y [LICENSE](LICENSE) para la licencia MIT, que permite el uso comercial.
