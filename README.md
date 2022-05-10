# WhatsApp-project

La mensajería tiene un importante papel en nuestros días. Empezando con los correos electrónicos
hasta las aplicaciones de mensajes más completas. Se quisiera además que el servicio de mensajería
no dependiera de un ente centralizado que regula los perfiles y potencialmente “lee” nuestras
conversaciones. En lugar de esto se desea proveer de una arquitectura descentralizada y segura, en
la que, cualquiera pueda recibir y mandar mensajes con la garantía de que solo lo podrán ver los
involucrados en la conversación.

Existen dos entidades fundamentales en la realización del proyecto: cliente y gestor de entidades.

**Cliente**

El cliente es la entidad encargada de mandar y recibir mensajes. La primera vez que un usuario se
añade a la red, debe identificarse para luego adicionar contactos y crear chats. La información de las
conversaciones se almacena en los clientes y no puede suceder que si el destinatario no está
conectado al sistema el remitente no pueda mandar el mensaje. La comunicación debe poderse
realizar en todo momento sin que se utilice un servicio diferente para el almacenamiento. Esta
funcionalidad debe recaer completamente en los clientes. La implementación de este cliente debe
venir acompañada con una aplicación gráfica que permita una mejor interacción con el sistema.

**Gestor de identidades**

Un gestor de identidades es un servicio en el que los usuarios crean sus cuentas para guardar
información que luego puede ser consumida por otras aplicaciones. Esta información solo puede ser
consultada por el propio usuario, o por lo aplicación previa consulta al mismo. Este elemento
facilita que los usuarios finales puedan utilizar un servicio como este sin preocuparse por las
interioridades del sistema. Este elemento no puede representar un punto de falla única en su
sistema.
