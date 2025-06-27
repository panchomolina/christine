# Christine 🤖 – Asistente virtual para Linux Mint (y derivados)

Christine es un asistente de voz **100 % local** que usa Vosk para reconocimiento de voz,
PyQt5 como visor y `pico2wave`/`mpg123` (o `gTTS`) para la respuesta hablada.  
Funciona sin conexión a Internet y está pensado para equipos modestos.

---

## ✨ Características

- Escucha por voz activable/desactivable y respuestas habladas.
- Visor gráfico con estado, mensajes y notificaciones.
- Comandos básicos de sistema (volumen, brillo, abrir apps, etc.).
- Fácil de instalar mediante un único script (`instalar_christine.sh`).
- Opcional: regla *udev* para controlar el brillo sin _sudo_.
- Desinstalación limpia con `./instalar_christine.sh --uninstall`.

---

## 📋 Requisitos

| Software | Versión mínima | Comentario |
|----------|----------------|------------|
| Debian/Ubuntu/Linux Mint | 20.04 +    | Probado en Mint 21.3 |
| Python   | 3.8 +          | Se crea un **entorno virtual** |
| Git      | 2.x            | Solo para clonar/actualizar |
| Paquetes del sistema | `mpg123`, `pulseaudio-utils`, `ffmpeg`, `unzip`, `wget` |

> El script instala automáticamente todos los paquetes del sistema.

---

## ⚡ Instalación rápida

```bash
# 1. Instalar Git si no lo tienes
sudo apt install git -y

# 2. Clonar el repositorio
git clone https://github.com/panchomolina/christine.git
cd christine

# 3. Dar permisos y lanzar el instalador
chmod +x instalar_christine.sh
./instalar_christine.sh

Al terminar verás el icono de Christine en tu menú.
Si no aparece, ejecuta:

cinnamon --replace &

o reinicia la sesión.

🔄 Actualizar a la última versión
cd ~/asistente
git pull           # descarga los cambios
./instalar_christine.sh   # reconstruye entorno y dependencias si es necesario

🧹 Desinstalación
./instalar_christine.sh --uninstall

Esto borra ~/asistente, el lanzador .desktop y la regla de brillo (si la activaste).

📁 Estructura del proyecto
christine/
├── instalar_christine.sh   # Script principal (instala / desinstala)
├── asistente.sh            # Lanzador interno del asistente
├── requirements.txt        # Dependencias de Python
├── main.py                 # Núcleo de Christine
├── asistente_visual.py     # Visor PyQt5
├── img/
│   └── circulo_brillante.png
└── .gitignore              # Excluye modelos Vosk, entorno virtual, cachés…

🔧 Personaliza Christine

    Vosk: si quieres otro idioma, cambia la URL del modelo en el script.
    Comandos: edita comandos.py para agregar nuevas acciones.
    Icono: sustituye img/circulo_brillante.png por tu propio PNG.

📝 Licencia

Este proyecto se distribuye bajo la MIT License.
Consulta el archivo LICENSE para más detalles.

🙏 Agradecimientos

    Vosk por su modelo de reconocimiento de voz offline.
    La comunidad de Linux Mint por una distro cómoda para desarrollar.
