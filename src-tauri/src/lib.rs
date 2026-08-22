use std::io::{Read, Write};
use std::net::TcpStream;
use std::sync::Mutex;
use std::time::Duration;

use tauri::Manager;
use tauri::menu::{
    AboutMetadataBuilder, MenuBuilder, MenuItemBuilder, SubmenuBuilder,
};
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

struct BackendState {
    port: u16,
    child: Option<tauri_plugin_shell::process::CommandChild>,
    backend_ready: bool,
}

fn check_health(port: u16) -> bool {
    let addr = format!("127.0.0.1:{}", port);
    let mut stream = match TcpStream::connect_timeout(
        &addr.parse().unwrap(),
        Duration::from_secs(2),
    ) {
        Ok(s) => s,
        Err(_) => return false,
    };

    let request = format!(
        "GET /api/health HTTP/1.0\r\nHost: 127.0.0.1:{}\r\nConnection: close\r\n\r\n",
        port
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }

    let mut response = String::new();
    if stream.read_to_string(&mut response).is_err() {
        return false;
    }

    response.contains("200 OK")
}

fn spawn_backend(app: &tauri::AppHandle) -> Result<u16, String> {
    let shell = app.shell();
    let sidecar_command = shell
        .sidecar("open-resume-backend")
        .map_err(|e| format!("Backend executable not found: {}", e))?;

    let (mut rx, child) = sidecar_command
        .spawn()
        .map_err(|e| format!("Failed to start backend service: {}", e))?;

    let port: u16 = loop {
        match rx.blocking_recv() {
            Some(CommandEvent::Stdout(line)) => {
                let line_str = String::from_utf8_lossy(&line);
                if let Some(port_str) = line_str.strip_prefix("PORT=") {
                    break port_str
                        .trim()
                        .parse()
                        .map_err(|e| format!("Invalid port number: {}", e))?;
                }
            }
            Some(CommandEvent::Stderr(line)) => {
                eprintln!(
                    "[open-resume-backend] {}",
                    String::from_utf8_lossy(&line).trim()
                );
            }
            Some(CommandEvent::Terminated(status)) => {
                return Err(format!(
                    "Backend process exited unexpectedly with status {:?}",
                    status.code
                ));
            }
            None => {
                return Err("Backend process closed stdout before printing PORT=".to_string());
            }
            _ => {}
        }
    };

    {
        let state = app.state::<Mutex<BackendState>>();
        let mut bs = state.lock().unwrap();
        bs.port = port;
        bs.child = Some(child);
    }

    let mut healthy = false;
    for _ in 0..60 {
        if check_health(port) {
            healthy = true;
            break;
        }
        std::thread::sleep(Duration::from_millis(500));
    }

    if !healthy {
        let state = app.state::<Mutex<BackendState>>();
        let mut bs = state.lock().unwrap();
        if let Some(child) = bs.child.take() {
            let _ = child.kill();
        }
        return Err("Backend service is not responding after 60 retries".to_string());
    }

    {
        let state = app.state::<Mutex<BackendState>>();
        let mut bs = state.lock().unwrap();
        bs.backend_ready = true;
    }

    Ok(port)
}

fn kill_backend(state: &Mutex<BackendState>) {
    let mut bs = state.lock().unwrap();
    if let Some(child) = bs.child.take() {
        let _ = child.kill();
    }
}

fn show_splash_error(splash: &tauri::WebviewWindow, msg: &str) {
    let escaped = msg.replace('\\', "\\\\").replace('\'', "\\'");
    let _ = splash.eval(&format!(
        "document.getElementById('error-msg').textContent = '{}'; \
         document.getElementById('error').classList.add('visible'); \
         document.getElementById('spinner').classList.add('hidden');",
        escaped
    ));
}

fn build_menu(app: &tauri::App) -> Result<tauri::menu::Menu<tauri::Wry>, tauri::Error> {
    let about = AboutMetadataBuilder::new()
        .name(Some("Open Resume".to_string()))
        .version(Some("0.1.0".to_string()))
        .website(Some("https://github.com/anomalyco/open-resume".to_string()))
        .website_label(Some("GitHub".to_string()))
        .build();

    let file_menu = SubmenuBuilder::new(app, "File")
        .close_window()
        .separator()
        .quit()
        .build()?;

    let edit_menu = SubmenuBuilder::new(app, "Edit")
        .undo()
        .redo()
        .separator()
        .cut()
        .copy()
        .paste()
        .separator()
        .select_all()
        .build()?;

    let view_menu = SubmenuBuilder::new(app, "View")
        .item(&MenuItemBuilder::with_id("reload", "Reload").build(app)?)
        .separator()
        .item(
            &MenuItemBuilder::with_id("toggle_devtools", "Toggle Developer Tools")
                .build(app)?,
        )
        .build()?;

    let help_menu = SubmenuBuilder::new(app, "Help")
        .about_with_text("About Open Resume", Some(about))
        .build()?;

    MenuBuilder::new(app)
        .item(&file_menu)
        .item(&edit_menu)
        .item(&view_menu)
        .item(&help_menu)
        .build()
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .manage(Mutex::new(BackendState {
            port: 0,
            child: None,
            backend_ready: false,
        }))
        .setup(|app| {
            let menu = build_menu(app)?;
            app.set_menu(menu)?;

            let handle = app.handle().clone();

            let splash_url = if cfg!(debug_assertions) {
                tauri::WebviewUrl::External("http://localhost:5173/splash.html".parse().unwrap())
            } else {
                tauri::WebviewUrl::App("splash.html".into())
            };

            let _splash = tauri::WebviewWindowBuilder::new(app, "splash", splash_url)
                .title("Open Resume")
                .inner_size(420.0, 320.0)
                .resizable(false)
                .decorations(false)
                .center()
                .skip_taskbar(true)
                .visible(true)
                .build()?;

            let splash_handle = handle.clone();
            std::thread::spawn(move || {
                match spawn_backend(&splash_handle) {
                    Ok(port) => {
                        let sh = splash_handle.clone();
                        let sh2 = sh.clone();
                        let _ = sh.run_on_main_thread(move || {
                            if let Some(splash) =
                                sh2.get_webview_window("splash")
                            {
                                let _ = splash.close();
                            }

                            let main_url = if cfg!(debug_assertions) {
                                format!("http://localhost:5173/?port={}", port)
                            } else {
                                "index.html".to_string()
                            };

                            let init_script =
                                format!("window.__BACKEND_PORT__ = {};", port);

                            match tauri::WebviewWindowBuilder::new(
                                &sh2,
                                "main",
                                tauri::WebviewUrl::App(main_url.into()),
                            )
                            .title("Open Resume")
                            .inner_size(1200.0, 800.0)
                            .min_inner_size(1024.0, 700.0)
                            .center()
                            .maximized(true)
                            .initialization_script(&init_script)
                            .build()
                            {
                                Ok(main) => {
                                    let _ = main.set_focus();
                                }
                                Err(e) => {
                                    eprintln!("Failed to create main window: {}", e);
                                }
                            }
                        });
                    }
                    Err(msg) => {
                        let msg_clone = msg.clone();
                        let sh = splash_handle.clone();
                        let sh2 = sh.clone();
                        let _ = sh.run_on_main_thread(move || {
                            if let Some(splash) =
                                sh2.get_webview_window("splash")
                            {
                                show_splash_error(&splash, &msg_clone);
                            }
                            eprintln!("{}", msg_clone);
                        });
                    }
                }
            });

            app.on_menu_event(move |app, event| {
                match event.id().as_ref() {
                    "reload" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.eval("window.location.reload();");
                        }
                    }
                    "toggle_devtools" => {
                        if let Some(window) = app.get_webview_window("main") {
                            window.open_devtools();
                        }
                    }
                    _ => {}
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                match window.label().as_ref() {
                    "splash" => {
                        let state = window.state::<Mutex<BackendState>>();
                        let bs = state.lock().unwrap();
                        if !bs.backend_ready {
                            drop(bs);
                            kill_backend(&state);
                            std::process::exit(0);
                        }
                    }
                    "main" => {
                        kill_backend(&window.state::<Mutex<BackendState>>());
                    }
                    _ => {}
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}