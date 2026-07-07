import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

export default class WattScreamExtension extends Extension {
    enable() {
        this._indicator = new PanelMenu.Button(0.0, this.metadata.name, false);
        
        let box = new St.BoxLayout({ style_class: 'panel-status-menu-box' });
        
        this._icon = new St.Icon({
            gicon: Gio.Icon.new_for_string('power-profile-power-saver-symbolic'),
            style_class: 'system-status-icon'
        });
        box.add_child(this._icon);
        
        this._label = new St.Label({
            text: '... W',
            y_align: Clutter.ActorAlign.CENTER
        });
        box.add_child(this._label);
        
        this._indicator.add_child(box);
        
        this._menuItem = new PopupMenu.PopupMenuItem('Lade Daten...', { reactive: false });
        this._indicator.menu.addMenuItem(this._menuItem);
        
        Main.panel.addToStatusArea(this.uuid, this._indicator);
        
        this._updateId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
            this._updateDisplay();
            return GLib.SOURCE_CONTINUE;
        });
        
        this._updateDisplay();
    }
    
    disable() {
        if (this._updateId) {
            GLib.Source.remove(this._updateId);
            this._updateId = null;
        }
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }
    
    _updateDisplay() {
        try {
            let runtimeDir = GLib.get_user_runtime_dir();
            let paths = [
                '/run/wattscream.json',
                GLib.build_filenamev([runtimeDir, 'wattscream.json'])
            ];
            
            let file = null;
            let success = false;
            let contents = null;
            
            for (let path of paths) {
                let f = Gio.File.new_for_path(path);
                if (f.query_exists(null)) {
                    let [s, c] = f.load_contents(null);
                    if (s) {
                        file = f;
                        success = s;
                        contents = c;
                        break;
                    }
                }
            }
            
            if (success && contents) {
                let decoder = new TextDecoder('utf-8');
                let data = JSON.parse(decoder.decode(contents));
                
                let cur = data.current_w !== undefined ? data.current_w.toFixed(1) : '?';
                let today = data.today_wh !== undefined ? (data.today_wh / 1000.0).toFixed(2) : '?';
                let boot = data.boot_wh !== undefined ? (data.boot_wh / 1000.0).toFixed(2) : '?';
                
                this._label.set_text(`${cur} W`);
                this._menuItem.label.set_text(`Heute: ${today} kWh | Seit Boot: ${boot} kWh`);
            } else {
                this._label.set_text('No Daemon');
                this._menuItem.label.set_text('Daemon inaktiv (/run/wattscream.json fehlt)');
            }
        } catch (e) {
            this._label.set_text('Error');
            this._menuItem.label.set_text(`Fehler: ${e.message}`);
        }
    }
}
