use std::env;
use std::fs;
use std::path::Path;
use std::process::Command;
use std::thread;
use std::time::Duration;
use chrono::Local;

fn main() {
    println!("Starting {} listener...", env!("CARGO_PKG_NAME"));
    
    // 自愈机制：检查环境
    if !check_and_fix_environment() {
        eprintln!("Environment check failed!");
        std::process::exit(1);
    }
    
    // 读取配置
    let config = read_config();
    
    // 监听并处理数据（循环监听）
    listen_loop(&config);
}

/// 检查并修复环境
fn check_and_fix_environment() -> bool {
    println!("Checking environment...");
    
    // 检查 Rust 工具链
    if !check_rust_installed() {
        eprintln!("Error: Rust is not installed. Please install Rust from https://rustup.rs/");
        return false;
    }
    
    // 检查 Cargo
    if !check_cargo_installed() {
        eprintln!("Error: Cargo is not installed.");
        return false;
    }
    
    // 检查编译产物
    let exe_name = if cfg!(target_os = "windows") {
        format!("{}.exe", env!("CARGO_PKG_NAME"))
    } else {
        env!("CARGO_PKG_NAME").to_string()
    };
    
    if !Path::new(&exe_name).exists() {
        println!("Binary not found, building...");
        if !build_project() {
            eprintln!("Build failed!");
            return false;
        }
    }
    
    println!("Environment check passed.");
    true
}

/// 检查 Rust 是否已安装
fn check_rust_installed() -> bool {
    Command::new("rustc")
        .arg("--version")
        .output()
        .is_ok()
}

/// 检查 Cargo 是否已安装
fn check_cargo_installed() -> bool {
    Command::new("cargo")
        .arg("--version")
        .output()
        .is_ok()
}

/// 构建项目
fn build_project() -> bool {
    println!("Building project in release mode...");
    let status = Command::new("cargo")
        .args(&["build", "--release"])
        .status();
    
    match status {
        Ok(status) => {
            if status.success() {
                println!("Build completed successfully.");
                true
            } else {
                eprintln!("Build failed with status: {:?}", status);
                false
            }
        }
        Err(e) => {
            eprintln!("Failed to execute cargo build: {}", e);
            false
        }
    }
}

/// 读取配置文件
fn read_config() -> serde_json::Value {
    let config_path = "config.json";
    let config_str = fs::read_to_string(config_path)
        .unwrap_or_else(|e| {
            eprintln!("Failed to read config file: {}", e);
            std::process::exit(1);
        });
    
    serde_json::from_str(&config_str)
        .unwrap_or_else(|e| {
            eprintln!("Failed to parse config: {}", e);
            std::process::exit(1);
        })
}

/// 循环监听并处理数据
fn listen_loop(config: &serde_json::Value) {
    let upper_file = config["listen_upper_file"]
        .as_str()
        .unwrap_or("../data/upper_data.json");
    
    let output_file = config["output_file"]
        .as_str()
        .unwrap_or("./output.json");
    
    let node_name = config["node_name"]
        .as_str()
        .unwrap_or("unknown");
    
    let process_flag = format!("_processed_{}", node_name);
    
    println!("Listening to: {}", upper_file);
    println!("Output to: {}", output_file);
    println!("Process flag: {}", process_flag);
    
    log_message(&format!("Node started: {}", node_name));
    log_message(&format!("Listening: {}", upper_file));
    
    loop {
        // 检查输入文件是否存在
        if !Path::new(upper_file).exists() {
            thread::sleep(Duration::from_millis(200));
            continue;
        }
        
        // 读取输入数据
        let data_str = match fs::read_to_string(upper_file) {
            Ok(s) => s,
            Err(e) => {
                log_message(&format!("Error reading input file: {}", e));
                thread::sleep(Duration::from_millis(200));
                continue;
            }
        };
        
        // 解析 JSON
        let mut data: serde_json::Value = match serde_json::from_str(&data_str) {
            Ok(d) => d,
            Err(e) => {
                log_message(&format!("JSON parse error: {}", e));
                thread::sleep(Duration::from_secs(1));
                continue;
            }
        };
        
        // 检查是否已处理
        if let Some(flag) = data.get(&process_flag) {
            if flag.as_bool().unwrap_or(false) {
                thread::sleep(Duration::from_millis(200));
                continue;
            }
        }
        
        // 应用过滤器
        if let Some(filter) = config.get("filter") {
            if !apply_filter(&data, filter) {
                thread::sleep(Duration::from_millis(200));
                continue;
            }
        }
        
        log_message("Processing data...");
        
        // 调用主程序处理
        let exe_name = if cfg!(target_os = "windows") {
            format!("{}.exe", env!("CARGO_PKG_NAME"))
        } else {
            env!("CARGO_PKG_NAME").to_string()
        };
        
        let input_json = serde_json::to_string(&data).unwrap_or_else(|_| "{}".to_string());
        
        let output = Command::new(&exe_name)
            .arg(&input_json)
            .output();
        
        match output {
            Ok(out) => {
                if out.status.success() {
                    let result = String::from_utf8_lossy(&out.stdout);
                    
                    // 写入输出文件
                    if let Err(e) = fs::write(output_file, result.as_ref()) {
                        log_message(&format!("Error writing output: {}", e));
                    } else {
                        log_message("Processing completed successfully");
                        
                        // 标记为已处理
                        if let Some(obj) = data.as_object_mut() {
                            obj.insert(process_flag.clone(), serde_json::Value::Bool(true));
                        }
                        
                        // 更新输入文件
                        if let Ok(updated_json) = serde_json::to_string_pretty(&data) {
                            let _ = fs::write(upper_file, updated_json);
                        }
                    }
                } else {
                    let error = String::from_utf8_lossy(&out.stderr);
                    log_message(&format!("Processing failed: {}", error));
                }
            }
            Err(e) => {
                log_message(&format!("Failed to execute {}: {}", exe_name, e));
            }
        }
        
        thread::sleep(Duration::from_millis(200));
    }
}

/// 应用过滤器
fn apply_filter(data: &serde_json::Value, filter: &serde_json::Value) -> bool {
    // TODO: 实现过滤逻辑
    // 根据 filter 配置决定是否处理该数据
    if let Some(obj) = filter.as_object() {
        for (key, value) in obj {
            if let Some(data_value) = data.get(key) {
                if data_value != value {
                    return false;
                }
            } else {
                return false;
            }
        }
    }
    true
}

/// 记录日志
fn log_message(message: &str) {
    let timestamp = Local::now().format("%Y-%m-%d %H:%M:%S");
    let log_line = format!("[{}] {}", timestamp, message);
    println!("{}", log_line);
    
    // 写入日志文件
    let log_dir = "logs";
    if !Path::new(log_dir).exists() {
        let _ = fs::create_dir_all(log_dir);
    }
    
    let log_file = Path::new(log_dir).join("listener.log");
    if let Ok(mut file) = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_file)
    {
        use std::io::Write;
        let _ = writeln!(file, "{}", log_line);
    }
}
