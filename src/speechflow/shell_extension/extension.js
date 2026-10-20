import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

Gio._promisify(Gio.SocketClient.prototype, 'connect_async', 'connect_finish');
Gio._promisify(Gio.OutputStream.prototype, 'write_all_async', 'write_all_finish');
Gio._promisify(Gio.DataInputStream.prototype, 'read_line_async', 'read_line_finish_utf8');

const RETRY_SECONDS = 3;
const COMMAND_TIMEOUT_SECONDS = 10;
const LANGUAGES = [['es', 'Español'], ['en', 'Inglés'], ['auto', 'Automático']];
const ICON_NORMAL = 'audio-input-microphone-symbolic';
const ICON_PAUSED = 'microphone-disabled-symbolic';

/**
 * Icono, clase CSS y texto según el último `status` (o null sin conexión).
 * El primer caso que se cumple gana, en el orden de la SPEC 31.
 */
function describe(status) {
    if (status === null)
        return {icon: ICON_NORMAL, css: 'speechflow-offline', text: 'SpeechFlow no está en ejecución'};
    if (status.paused)
        return {icon: ICON_PAUSED, css: 'speechflow-paused', text: 'En pausa'};
    if (status.state === 'recording')
        return {icon: ICON_NORMAL, css: 'speechflow-recording', text: 'Grabando'};
    if (status.state === 'transcribing')
        return {icon: ICON_NORMAL, css: 'speechflow-transcribing', text: 'Transcribiendo'};
    if (status.model?.status === 'loading')
        return {icon: ICON_NORMAL, css: 'speechflow-loading', text: 'Cargando el modelo…'};
    if (status.device?.connected === false)
        return {icon: ICON_NORMAL, css: 'speechflow-warning', text: 'Micrófono desconectado'};
    return {icon: ICON_NORMAL, css: null, text: 'Listo'};
}

function isCancelled(error) {
    return error instanceof GLib.Error && error.matches(Gio.IOErrorEnum, Gio.IOErrorEnum.CANCELLED);
}

const Indicator = GObject.registerClass(
class Indicator extends PanelMenu.Button {
    _init(onCommand, onDevices) {
        super._init(0.0, 'SpeechFlow');
        this._onCommand = onCommand;
        this._onDevices = onDevices;
        this._devicesRequest = 0;
        this._css = null;
        this._icon = new St.Icon({
            icon_name: ICON_NORMAL,
            style_class: 'system-status-icon',
        });
        this.add_child(this._icon);

        this._statusItem = new PopupMenu.PopupMenuItem('', {reactive: false});
        this._detailItem = new PopupMenu.PopupMenuItem('', {reactive: false});
        this._pauseItem = new PopupMenu.PopupMenuItem('');
        this._pauseItem.connect('activate', () => this._onCommand({cmd: this._paused ? 'resume' : 'pause'}));
        this.menu.addMenuItem(this._statusItem);
        this.menu.addMenuItem(this._detailItem);
        this.menu.addMenuItem(this._pauseItem);

        this._languageMenu = new PopupMenu.PopupSubMenuMenuItem('Idioma');
        this._languageItems = new Map();
        for (const [code, name] of LANGUAGES) {
            const item = new PopupMenu.PopupMenuItem(name);
            item.connect('activate', () => this._onCommand({cmd: 'language', value: code}));
            this._languageMenu.menu.addMenuItem(item);
            this._languageItems.set(code, item);
        }
        this.menu.addMenuItem(this._languageMenu);

        this._deviceMenu = new PopupMenu.PopupSubMenuMenuItem('Micrófono');
        this._deviceMenu.menu.connect('open-state-changed', (menu, open) => {
            if (open)
                this._refreshDevices();
        });
        this.menu.addMenuItem(this._deviceMenu);
    }

    _setDeviceMessage(text) {
        this._deviceMenu.menu.removeAll();
        this._deviceMenu.menu.addMenuItem(new PopupMenu.PopupMenuItem(text, {reactive: false}));
    }

    /** Pide `devices` al abrir el submenú; una respuesta tardía de una apertura anterior se descarta. */
    async _refreshDevices() {
        const request = ++this._devicesRequest;
        this._setDeviceMessage('Cargando…');
        const devices = await this._onDevices();
        if (request !== this._devicesRequest)
            return;
        if (devices === null) {
            this._setDeviceMessage('No disponible');
            return;
        }
        this._deviceMenu.menu.removeAll();
        if (devices.length === 0)
            this._setDeviceMessage('Sin dispositivos de entrada');
        for (const device of devices) {
            const item = new PopupMenu.PopupMenuItem(`[${device.index}] ${device.name}`);
            item.setOrnament(device.selected ? PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
            item.connect('activate', () => this._onCommand({cmd: 'device', value: device.index}));
            this._deviceMenu.menu.addMenuItem(item);
        }
    }

    setStatus(status) {
        const view = describe(status);
        this._icon.icon_name = view.icon;
        if (this._css)
            this._icon.remove_style_class_name(this._css);
        this._css = view.css;
        if (this._css)
            this._icon.add_style_class_name(this._css);

        this._paused = Boolean(status?.paused);
        this._statusItem.label.text = view.text;
        this._detailItem.visible = status !== null;
        if (status !== null)
            this._detailItem.label.text = `${status.model?.name ?? '?'} · ${status.model?.compute_device ?? '?'} · ${status.model?.status ?? '?'}`;
        this._pauseItem.visible = status !== null;
        this._pauseItem.label.text = this._paused ? 'Reanudar dictado' : 'Pausar dictado';
        this._languageMenu.visible = status !== null;
        this._deviceMenu.visible = status !== null;
        for (const [code, item] of this._languageItems)
            item.setOrnament(status?.language === code ? PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
    }
});

export default class SpeechFlowExtension extends Extension {
    enable() {
        this._cancellable = new Gio.Cancellable();
        this._retrySource = null;
        this._connection = null;
        this._status = null;
        this._pending = new Set();
        this._indicator = new Indicator(request => this._runCommand(request), () => this._fetchDevices());
        this._indicator.setStatus(null);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
        this._connect();
    }

    disable() {
        this._cancellable?.cancel();
        this._cancellable = null;
        for (const cancellable of this._pending)
            cancellable.cancel();
        this._pending = null;
        if (this._retrySource !== null) {
            GLib.source_remove(this._retrySource);
            this._retrySource = null;
        }
        this._closeConnection();
        this._indicator?.destroy();
        this._indicator = null;
        this._status = null;
    }

    _socketPath() {
        return GLib.build_filenamev([GLib.get_user_runtime_dir(), 'speechflow', 'control.sock']);
    }

    /**
     * Envía una petición por una conexión nueva y devuelve la respuesta ya analizada.
     * Plazo de 10 s; `disable()` la cancela. Lanza si no hay conexión o respuesta.
     */
    async _command(request) {
        const cancellable = new Gio.Cancellable();
        this._pending.add(cancellable);
        let timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, COMMAND_TIMEOUT_SECONDS, () => {
            timer = null;
            cancellable.cancel();
            return GLib.SOURCE_REMOVE;
        });
        let connection = null;
        try {
            const address = Gio.UnixSocketAddress.new(this._socketPath());
            connection = await new Gio.SocketClient().connect_async(address, cancellable);
            await connection.get_output_stream().write_all_async(new TextEncoder().encode(`${JSON.stringify(request)}\n`), GLib.PRIORITY_DEFAULT, cancellable);
            const input = new Gio.DataInputStream({base_stream: connection.get_input_stream()});
            const [line] = await input.read_line_async(GLib.PRIORITY_DEFAULT, cancellable);
            if (line === null)
                throw new Error('el servicio cerró la conexión sin responder');
            return JSON.parse(line);
        } finally {
            if (timer !== null)
                GLib.source_remove(timer);
            this._pending?.delete(cancellable);
            connection?.close_async(GLib.PRIORITY_DEFAULT, null, (source, result) => {
                try {
                    source.close_finish(result);
                } catch (error) {
                    // ya estaba cerrada
                }
            });
        }
    }

    /** Ejecuta un comando desde el menú y avisa con `Main.notify` si falla. */
    async _runCommand(request) {
        try {
            const response = await this._command(request);
            if (!response.ok)
                Main.notify('SpeechFlow', response.error ?? 'error desconocido');
        } catch (error) {
            if (!this._cancellable)  // deshabilitada mientras esperaba
                return;
            Main.notify('SpeechFlow', `No se pudo enviar el comando: ${error.message}`);
        }
    }

    /** Lista de dispositivos de `devices`, o null si no se pudo obtener (se avisa con `Main.notify`). */
    async _fetchDevices() {
        try {
            const response = await this._command({cmd: 'devices'});
            if (response.ok)
                return response.devices ?? [];
            Main.notify('SpeechFlow', response.error ?? 'error desconocido');
        } catch (error) {
            if (this._cancellable)
                Main.notify('SpeechFlow', `No se pudo obtener los micrófonos: ${error.message}`);
        }
        return null;
    }

    _connect() {
        const cancellable = this._cancellable;
        const client = new Gio.SocketClient();
        const address = Gio.UnixSocketAddress.new(this._socketPath());
        client.connect_async(address, cancellable, (source, result) => {
            let connection;
            try {
                connection = source.connect_finish(result);
            } catch (error) {
                if (!isCancelled(error))
                    this._lostConnection();
                return;
            }
            this._connection = connection;
            this._subscribe(connection, cancellable);
        });
    }

    _subscribe(connection, cancellable) {
        const request = new TextEncoder().encode('{"cmd": "subscribe"}\n');
        connection.get_output_stream().write_all_async(request, GLib.PRIORITY_DEFAULT, cancellable, (stream, result) => {
            try {
                stream.write_all_finish(result);
            } catch (error) {
                if (!isCancelled(error))
                    this._lostConnection();
                return;
            }
            const input = new Gio.DataInputStream({base_stream: connection.get_input_stream()});
            this._readLine(connection, input, cancellable);
        });
    }

    _readLine(connection, input, cancellable) {
        input.read_line_async(GLib.PRIORITY_DEFAULT, cancellable, (stream, result) => {
            let line;
            try {
                [line] = stream.read_line_finish_utf8(result);
            } catch (error) {
                if (!isCancelled(error))
                    this._lostConnection();
                return;
            }
            if (line === null) {  // EOF: el servicio se cerró
                this._lostConnection();
                return;
            }
            try {
                const message = JSON.parse(line);
                if (!message.ok) {
                    console.error(`SpeechFlow: suscripción rechazada: ${message.error}`);
                    this._lostConnection();
                    return;
                }
                if (message.event === 'status')
                    this._setStatus(message);
            } catch (error) {
                console.error(`SpeechFlow: línea no válida: ${error}`);
            }
            this._readLine(connection, input, cancellable);
        });
    }

    _setStatus(status) {
        this._status = status;
        this._indicator?.setStatus(status);
    }

    _closeConnection() {
        const connection = this._connection;
        this._connection = null;
        connection?.close_async(GLib.PRIORITY_DEFAULT, null, (source, result) => {
            try {
                source.close_finish(result);
            } catch (error) {
                // ya estaba cerrada
            }
        });
    }

    _lostConnection() {
        if (!this._cancellable || this._cancellable.is_cancelled())
            return;
        this._closeConnection();
        this._setStatus(null);
        if (this._retrySource !== null)
            return;
        this._retrySource = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, RETRY_SECONDS, () => {
            this._retrySource = null;
            if (this._cancellable && !this._cancellable.is_cancelled())
                this._connect();
            return GLib.SOURCE_REMOVE;
        });
    }
}
