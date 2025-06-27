import sys
import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QProgressBar, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QPixmap, QCursor, QIcon
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QSettings, QTimer, pyqtSlot

class PrintRedirector(QObject):
    texto_recibido = pyqtSignal(str)
    def write(self, texto):
        if texto.strip():
            self.texto_recibido.emit(texto.strip())
    def flush(self):
        pass

class AsistenteVisual(QWidget):
    estado_cambiado = pyqtSignal(bool)  # True = activo, False = inactivo
    cerrar_signal = pyqtSignal()
    def __init__(self, nombre_asistente="ASISTENTE"):
        super().__init__()
        BASEDIR = os.path.dirname(os.path.abspath(__file__))
        self.icono_tray_azul = QIcon(os.path.join(BASEDIR, "img", "icono_tray_azul.png"))
        self.icono_tray_rojo = QIcon(os.path.join(BASEDIR, "img", "icono_tray_rojo.png"))
        # Configuración para guardar/restaurar posición
        self.settings = QSettings("TuNombreDeApp", "AsistenteVisual")
        pos = self.settings.value("posicion", None)
        if pos:
            self.move(pos)

        self.estado = "inactivo"
        tcirculo = 80
        
        ancho, alto = 400, 200
        self.setFixedSize(ancho, alto)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Imagen visor 
        self.visor = QLabel(self)
        pixmap_visor = QPixmap("img/visor.png").scaled(310, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.visor.setPixmap(pixmap_visor)
        self.visor.move(80, 25)

        # Texto del asistente
        titulo = f"{nombre_asistente.upper()} - ASISTENTE VIRTUAL"
        self.texto = QLabel(titulo, self)
        self.texto_original = ""
        self.marquesina_offset = 0
        self.marquesina_timer = QTimer(self)
        self.marquesina_timer.timeout.connect(self.actualizar_marquesina)
        self.marquesina_timer.start(150)
        self.texto.setStyleSheet("color: white; font-size: 12px; background-color: rgba(1,120,185,50); padding: 4px;")
        self.texto.setGeometry(130, 43, 245, 25)

        # Botón de estado (círculo) escalado
        self.btn_estado = QLabel(self)
        pixmap_azul = QPixmap("img/circulo_azul.png").scaled(tcirculo, tcirculo, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap_brillante = QPixmap("img/circulo_brillante.png").scaled(tcirculo, tcirculo, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pixmap_azul = pixmap_azul
        self.pixmap_brillante = pixmap_brillante
        self.btn_estado.setPixmap(self.pixmap_azul)
        self.btn_estado.setGeometry(30, 20, tcirculo, tcirculo)
        self.btn_estado.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_estado.mousePressEvent = self.toggle_estado

        # Botón cerrar
        self.cerrar_btn = QLabel(" ", self)
        self.cerrar_btn.setStyleSheet("color: white; font-size: 16px; background-color: rgba(0,0,0,0); padding: 2px;")
        self.cerrar_btn.setGeometry(ancho - 75, 33, 50, 5)
        self.cerrar_btn.setToolTip("Cerrar")
        self.cerrar_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.cerrar_btn.mousePressEvent = self.cerrar_app

        # Traer widgets al frente
        self.btn_estado.raise_()
        self.cerrar_btn.raise_()
        self.texto.raise_()

        # Permitir mover la ventana arrastrando el fondo
        self.drag_position = None
        self.visor.mousePressEvent = self.mouse_press
        self.visor.mouseMoveEvent = self.mouse_move
        
        # Redirigir print al visor de texto
        self.redirector = PrintRedirector()
        self.redirector.texto_recibido.connect(self.mostrar_texto)

        # Barra de progreso para carga (inicialmente oculta)
        self.barra_carga = QProgressBar(self)
        self.barra_carga.setGeometry(130, 73, 245, 10)
        self.barra_carga.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 0px;
                text-align: center;
                font-size: 10px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #01e2e5;
            }
        """)
        self.barra_carga.setMinimum(0)
        self.barra_carga.setMaximum(100)
        self.barra_carga.setValue(0)
        self.barra_carga.hide()
        
        
        # Barra tipo ecualizador (horizontal)
        self.barra_sonido = QProgressBar(self)
        self.barra_sonido.setGeometry(130, 73, 245, 10)
        self.barra_sonido.setRange(0, 100)
        self.barra_sonido.setValue(0)
        self.barra_sonido.setTextVisible(False)
        self.barra_sonido.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 0px;
                background-color: #3d748e;
            }
            QProgressBar::chunk {
                background-color: #01e2e5;
            }
        """)
        self.barra_sonido.hide()

        # Timer para animar la barra de sonido
        self.timer_ecualizador = QTimer(self)
        self.timer_ecualizador.timeout.connect(self.animar_ecualizador)
        
        # Variables para la animación
        self.ecualizador_valor = 0
        self.ecualizador_subiendo = True
        
        # Iniciar el tray icon
        self.iniciar_tray_icon()

    def actualizar_barra(self, valor):
        self.barra_carga.setValue(valor)
        self.barra_carga.show()

    def toggle_estado(self, event):
        if self.estado == "inactivo":
            self.estado = "activo"
            self.btn_estado.setPixmap(self.pixmap_brillante)
            self.texto.setText("Escuchando...")
            self.tray_icon.setIcon(self.icono_tray_azul)
            self.estado_cambiado.emit(True)
        else:
            self.estado = "inactivo"
            self.btn_estado.setPixmap(self.pixmap_azul)
            self.texto.setText("Modo inactivo.")
            self.tray_icon.setIcon(self.icono_tray_rojo)
            self.estado_cambiado.emit(False)

    def cerrar_app(self, event):
        self.settings.setValue("posicion", self.pos())
        self.cerrar_signal.emit()

    def mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            
    def imprimir(self, texto):
        self.texto.setText(texto)

    def mostrar_texto(self, texto):
        self.texto_original = texto + "   "  # espacio entre ciclos
        self.marquesina_offset = 0
        self.texto.setText(self.texto_original)

    def actualizar_marquesina(self):
        if len(self.texto_original) <= 50:
            return  # no hace falta mover texto corto
        desplazado = self.texto_original[self.marquesina_offset:] + self.texto_original[:self.marquesina_offset]
        self.texto.setText(desplazado)
        self.marquesina_offset = (self.marquesina_offset + 1) % len(self.texto_original)

    def animar_ecualizador(self):
        if self.ecualizador_subiendo:
            self.ecualizador_valor += 5
            if self.ecualizador_valor >= 100:
                self.ecualizador_valor = 100
                self.ecualizador_subiendo = False
        else:
            self.ecualizador_valor -= 5
            if self.ecualizador_valor <= 0:
                self.ecualizador_valor = 0
                self.ecualizador_subiendo = True
        self.barra_sonido.setValue(self.ecualizador_valor)

    @pyqtSlot()
    def iniciar_ecualizador(self):
        # Ocultamos la barra antes de iniciar el delay para que no se muestre antes
        self.barra_sonido.hide()
        # Usamos singleShot para llamar después de 1 segundo (1000 ms) al método que arranca la animación
        QTimer.singleShot(1000, self._start_animacion_ecualizador)

    def _start_animacion_ecualizador(self):
        self.barra_sonido.show()
        self.ecualizador_valor = 10
        self.ecualizador_subiendo = True
        self.timer_ecualizador.start(5)

    @pyqtSlot()
    def detener_ecualizador(self):
        self.timer_ecualizador.stop()
        self.barra_sonido.hide()
        self.barra_sonido.setValue(0)

    def iniciar_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)        
        self.tray_icon.setIcon(self.icono_tray_azul)
        
        # Menú contextual
        menu = QMenu()

        mostrar_action = QAction("Mostrar", self)
        mostrar_action.triggered.connect(self.show)
        menu.addAction(mostrar_action)
        
        ocultar_action = QAction("Ocultar", self)
        ocultar_action.triggered.connect(self.hide)
        menu.addAction(ocultar_action)

        salir_action = QAction("Salir", self)
        salir_action.triggered.connect(self.cerrar_signal.emit)
        menu.addAction(salir_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
        self.tray_icon.setToolTip("Asistente Christine")
