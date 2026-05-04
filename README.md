# Plataforma de email marketing a la medida (HotBoat + Resend)

Repositorio de **especificación y brief** para construir un producto interno de email marketing. El contenido principal es el prompt maestro más abajo (copiable para Cursor, agencias o LLMs).

---

## Prompt maestro

**Contexto**  
Somos HotBoat (turismo/experiencias en Chile). Queremos **construir desde cero un producto interno de email marketing**, no usar solo Klaviyo/Mailchimp como caja negra. La **entrega de correos debe usar la API de Resend**. El **frontend debe inspirarse en Klaviyo** en cuanto a flujos, segmentación, editor de campañas y analítica, pero **podemos añadir funciones específicas** para nuestro negocio.

**Objetivo principal**  
Poder **definir audiencias (segmentos)** según el comportamiento y preferencias reales de los clientes —por ejemplo: qué extras o packs han pedido, cuántas veces han hecho la experiencia HotBoat, tipo de alojamiento, fechas, idioma, origen del lead (anuncio, WhatsApp, web), etc.— y **lanzar campañas y automatizaciones** pensadas para cada tipo de cliente (ej.: primera vez vs recurrente, solo consulta vs ya reservó, upsell de extras, reactivación).

**Stack y restricciones**  
- Envío y dominio: **Resend** (API, dominios verificados, webhooks de eventos si aplica: delivered, bounce, open/click si Resend lo expone en nuestro plan).  
- Backend propio: API REST o similar, base de datos para contactos, eventos, campañas y plantillas.  
- Frontend: SPA moderna (React/Next o equivalente), **UI pulida y “tipo Klaviyo”** (sidebar, listas, filtros, builder visual).  
- Los datos de clientes y reservas deben **integrarse con nuestra fuente de verdad** (CRM interno, PostgreSQL, exports, o API existente): describe en el diseño **cómo se sincronizan o importan** contactos y atributos.

**Inspiración UX (Klaviyo)**  
Que el producto incluya, como mínimo, sensación y capacidades parecidas a:  
- **Campañas de un envío (broadcast)** con programación y vista previa.  
- **Flujos / automatizaciones** basados en disparadores (evento, fecha, entrada a segmento, etc.).  
- **Editor de emails**: bloques (texto, botón, imagen, columnas), variables dinámicas `{{nombre}}`, `{{ultima_reserva}}`, etc.  
- **Listas y segmentos** con constructor visual de condiciones (AND/OR): propiedades del perfil + eventos + agregados (conteos, fechas).  
- **Analítica por campaña y por flujo**: enviados, rebotes, clics (según lo que Resend permita medir o lo que trackeemos con enlaces propios).  
- **Biblioteca de plantillas** y duplicar campañas.

**Funciones “y más” orientadas a HotBoat**  
- Modelo de datos de contacto enriquecido: **atributos derivados** (ej. `veces_hotboat`, `ultima_fecha_visita`, `idioma`, `ha_alojamiento`, `extras_favoritos`, `ticket_medio`, `origen_utm`).  
- Segmentos ejemplo que deben poder construirse sin SQL: “**más de 1 experiencia HotBoat**”, “**nunca ha reservado pero abrió email de precios**”, “**ha comprado extra romántico**”, “**solo alojamiento sin paseo**”, etc.  
- Posibilidad de **sincronizar o etiquetar** desde eventos de negocio (reserva confirmada, pago, cancelación, visita web trackeada).  
- **Preferencias y cumplimiento**: categorías de contenido, opt-in/opt-out por tipo de mensaje, pie legal y enlaces de baja alineados con buenas prácticas.

**No funcionales**  
- Multiusuario con roles (admin, editor, solo lectura) si el alcance lo permite.  
- Auditoría básica (quién envió qué).  
- Escalabilidad razonable para decenas de miles de contactos y envíos por lotes respetando límites de Resend.

**Entregables esperados del equipo / de la IA**  
1. Arquitectura (diagrama lógico: frontend ↔ API ↔ DB ↔ Resend ↔ fuentes de datos).  
2. Modelo de datos (contactos, eventos, segmentos, campañas, plantillas, envíos).  
3. Lista priorizada de **MVP vs fase 2**.  
4. Wireframes o lista de pantallas clave al estilo Klaviyo.  
5. Plan de integración Resend (envío, plantillas, manejo de errores, reintentos).

**Tono**  
Priorizar claridad, segmentación potente y UX profesional; evitar soluciones genéricas que no conecten con datos reales de reservas y preferencias.

---

## Variante corta (título o epic)

> Plataforma interna de email marketing con frontend estilo Klaviyo, envíos via Resend, segmentación profunda por comportamiento y preferencias (HotBoat, extras, recurrencia) y campañas por tipo de cliente.

---

## Cómo usar este repo

1. Clona o abre la carpeta en Cursor.  
2. Pega el **Prompt maestro** en un chat de planificación o en el brief para un proveedor.  
3. Añade anexos: esquema de tu BD actual, campos de `all_appointments` o tablas de clientes, límites de Resend, idiomas soportados.

## Licencia del texto

Uso interno HotBoat / documentación de producto. Ajusta según tu política.
