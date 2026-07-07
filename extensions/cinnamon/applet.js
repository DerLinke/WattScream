const Applet = imports.ui.applet;
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const St = imports.gi.St;
const PopupMenu = imports.ui.popupMenu;

class WattScreamApplet extends Applet.TextIconApplet {
    constructor(metadata, orientation, panel_height, instance_id) {
        super(orientation, panel_height, instance_id);
        
        this.set_applet_icon_symbolic_name("power-profile-power-saver-symbolic");
        this.set_applet_label("... W");
        this.set_applet_tooltip("wattScream - Garagen-Leistung");
        
        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menuManager.addMenu(this.menu);
        
        this.menuItem = new PopupMenu.PopupMenuItem("Lade Daten...", { reactive: false });
        this.menu.addMenuItem(this.menuItem);
        
        this._updateDisplay();
        
        this._updateId = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
            this._updateDisplay();
            return GLib.SOURCE_CONTINUE;
        });
    }
    
    on_applet_clicked(event) {
        this.menu.toggle();
    }
    
    on_applet_removed_from_panel() {
        if (this._updateId) {
            GLib.Source.remove(this._updateId);
            this._updateId = null;
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
                
                this.set_applet_label(`${cur} W`);
                this.menuItem.label.setText(`Heute: ${today} kWh | Seit Boot: ${boot} kWh`);
            } else {
                this.set_applet_label("No Daemon");
                this.menuItem.label.setText("Daemon inaktiv (/run/wattscream.json fehlt)");
            }
        } catch (e) {
            this.set_applet_label("Error");
            this.menuItem.label.setText(`Fehler: ${e.message}`);
        }
    }
}

function main(metadata, orientation, panel_height, instance_id) {
    return new WattScreamApplet(metadata, orientation, panel_height, instance_id);
}
