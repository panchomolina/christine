#!/bin/bash

ASISTENTE_DIR="$HOME/asistente"
DESKTOP_FILE="$HOME/.local/share/applications/christine.desktop"
RULES_FILE="/etc/udev/rules.d/90-brillo.rules"
REPO_URL="https://github.com/panchomolina/christine.git"

function instalar() {
    echo "🔧 Instalando Christine..."

    # Instalar dependencias del sistema
    sudo apt update
    sudo apt install -y git python3 python3-pip python3-venv mpg123 pulseaudio-utils ffmpeg unzip wget

    # Clonar o actualizar el repositorio
    if [ -d "$ASISTENTE_DIR" ]; then
        echo "📂 La carpeta ~/asistente ya existe. ¿Deseas actualizarla desde GitHub?"
        read -rp "Escribe 's' para sí o cualquier otra tecla para omitir: " ACTUALIZAR
        if [ "$ACTUALIZAR" = "s" ]; then
            cd "$ASISTENTE_DIR" && git pull
        else
            echo "🟡 Usando la versión local existente..."
            cd "$ASISTENTE_DIR" || exit
        fi
    else
        echo "🔄 Clonando el asistente desde GitHub..."
        git clone "$REPO_URL" "$ASISTENTE_DIR"
        cd "$ASISTENTE_DIR" || exit
    fi

    # Crear entorno virtual
    echo "🐍 Creando entorno virtual..."
    python3 -m venv asistente_env
    source asistente_env/bin/activate

    # Instalar requerimientos
    if [ -f "requirements.txt" ]; then
        echo "📦 Instalando dependencias de Python..."
        pip install -r requirements.txt
    else
        echo "⚠️ No se encontró requirements.txt. Revisa tu repositorio."
        exit 1
    fi

    # Descargar modelo Vosk
    mkdir -p modelos_vosk
    cd modelos_vosk || exit
    if [ ! -d "vosk-model-es-0.42" ]; then
        echo "📥 Descargando modelo de voz..."
        wget https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip
        echo "📦 Descomprimiendo modelo..."
        unzip vosk-model-es-0.42.zip
        rm vosk-model-es-0.42.zip
    else
        echo "✅ Modelo Vosk ya existe, omitiendo descarga."
    fi
    cd ..

    # Crear acceso directo
    echo "🖼️ Creando acceso directo..."
    mkdir -p ~/.local/share/applications

    ICONO="$ASISTENTE_DIR/img/circulo_brillante.png"

    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Christine
Comment=Asistente virtual con visor
Exec=$ASISTENTE_DIR/asistente.sh
Icon=$ICONO
Terminal=false
Type=Application
Categories=Utility;
EOF

    chmod +x "$DESKTOP_FILE"
    chmod +x "$ASISTENTE_DIR/asistente.sh"

    # Opción para configurar brillo
    echo "💡 ¿Deseas configurar el brillo sin contraseña? (Requiere reinicio)"
    read -rp "Escribe 's' para sí o cualquier otra tecla para omitir: " CONFIG_BRILLO

    if [ "$CONFIG_BRILLO" = "s" ]; then
        CONTROLADOR=$(ls /sys/class/backlight | head -n 1)
        if [ -z "$CONTROLADOR" ]; then
            echo "⚠️ No se detectó el controlador de brillo. Omitido."
        else
            echo "🔐 Aplicando permisos para $CONTROLADOR..."
            sudo bash -c "echo 'SUBSYSTEM==\"backlight\", KERNEL==\"$CONTROLADOR\", RUN+=\"/bin/chmod 0666 /sys/class/backlight/$CONTROLADOR/brightness\"' > $RULES_FILE"
            sudo udevadm control --reload-rules
            sudo udevadm trigger
        fi
    fi

    echo "✅ Instalación completa."
    echo "🔄 Si no ves el ícono, reinicia Cinnamon con: cinnamon --replace &"
    echo "   o reinicia sesión."
}

function desinstalar() {
    echo "⚠️ Esto eliminará Christine completamente."
    read -rp "¿Estás seguro? (s para sí): " CONFIRMAR
    if [ "$CONFIRMAR" != "s" ]; then
        echo "❌ Cancelado."
        exit 0
    fi

    echo "🧹 Eliminando archivos..."
    rm -rf "$ASISTENTE_DIR"
    rm -f "$DESKTOP_FILE"

    if [ -f "$RULES_FILE" ]; then
        echo "🧽 Quitando configuración de brillo..."
        sudo rm -f "$RULES_FILE"
        sudo udevadm control --reload-rules
        sudo udevadm trigger
    fi

    echo "✅ Desinstalación completa. Puedes reiniciar Cinnamon si lo deseas."
}

# Entrada principal
if [[ "$1" == "--uninstall" || "$1" == "-u" ]]; then
    desinstalar
else
    instalar
fi
