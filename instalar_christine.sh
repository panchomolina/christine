#!/bin/bash

ASISTENTE_DIR="$HOME/asistente"
DESKTOP_FILE="$HOME/.local/share/applications/christine.desktop"
RULES_FILE="/etc/udev/rules.d/90-brillo.rules"

function instalar() {
    echo "🔧 Instalando Christine..."

    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv mpg123 pulseaudio-utils ffmpeg unzip wget

    echo "📁 Creando carpeta del asistente en $ASISTENTE_DIR..."
    mkdir -p "$ASISTENTE_DIR"
    cd "$ASISTENTE_DIR" || exit

    echo "🐍 Creando entorno virtual..."
    python3 -m venv asistente_env
    source asistente_env/bin/activate

    if [ -f "requirements.txt" ]; then
        echo "📦 Instalando dependencias de Python..."
        pip install -r requirements.txt
    else
        echo "⚠️ No se encontró requirements.txt. Copia los archivos antes de continuar."
        exit 1
    fi

    mkdir -p modelos_vosk
    cd modelos_vosk || exit
    echo "📥 Descargando modelo de voz..."
    wget https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip
    unzip vosk-model-es-0.42.zip
    rm vosk-model-es-0.42.zip
    cd ..

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

    echo "💡 ¿Deseas configurar el brillo sin contraseña? (Requiere reinicio)"
    read -rp "Escribe 's' para sí o cualquier otra tecla para omitir: " CONFIG_BRILLO

    if [ "$CONFIG_BRILLO" = "s" ]; then
        CONTROLADOR=$(ls /sys/class/backlight | head -n 1)
        if [ -z "$CONTROLADOR" ]; then
            echo "⚠️ No se detectó el controlador de brillo. Omitido."
        else
            sudo bash -c "echo 'SUBSYSTEM==\"backlight\", KERNEL==\"$CONTROLADOR\", RUN+=\"/bin/chmod 0666 /sys/class/backlight/$CONTROLADOR/brightness\"' > $RULES_FILE"
            sudo udevadm control --reload-rules
            sudo udevadm trigger
        fi
    fi

    echo "✅ Instalación completa. Si no ves el icono, reinicia Cinnamon con:"
    echo "   cinnamon --replace &"
}

function desinstalar() {
    echo "⚠️ Esto eliminará Christine del sistema."

    read -rp "¿Estás seguro? (s para sí): " CONFIRMAR
    if [ "$CONFIRMAR" != "s" ]; then
        echo "❌ Cancelado."
        exit 0
    fi

    echo "🧹 Eliminando archivos..."
    rm -rf "$ASISTENTE_DIR"
    rm -f "$DESKTOP_FILE"

    if [ -f "$RULES_FILE" ]; then
        echo "🧽 Eliminando regla de brillo..."
        sudo rm -f "$RULES_FILE"
        sudo udevadm control --reload-rules
        sudo udevadm trigger
    fi

    echo "✅ Desinstalación completa."
    echo "🔄 Puedes reiniciar Cinnamon con: cinnamon --replace &"
}

# Menú o argumento
if [[ "$1" == "--uninstall" || "$1" == "-u" ]]; then
    desinstalar
else
    instalar
fi
