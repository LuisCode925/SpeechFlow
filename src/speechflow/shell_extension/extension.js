import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

const RETRY_SECONDS = 3;
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
    _init() {
        super._init(0.0, 'SpeechFlow');
        this._css = null;
        this._icon = new St.Icon({
            icon_name: ICON_NORMAL,
            style_class: 'system-status-icon',
        });
        this.add_child(this._icon);
    }

    setStatus(status) {
        const view = describe(status);
        this._icon.icon_name = view.icon;
        if (this._css)
            this._icon.remove_style_class_name(this._css);
        this._css = view.css;
        if (this._css)
            this._icon.add_style_class_name(this._css);
    }
});

export default class SpeechFlowExtension extends Extension {
    enable() {
        this._cancellable = new Gio.Cancellable();
        this._retrySource = null;
        this._connection = null;
        this._status = null;
        this._indicator = new Indicator();
        this._indicator.setStatus(null);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
        this._connect();
    }

    disable() {
        this._cancellable?.cancel();
        this._cancellable = null;
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
