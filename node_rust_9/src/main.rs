mod packet;

use std::env;
use std::fs;
use packet::OutputPacket;

fn main() {
    // 获取当前可执行文件所在目录
    let exe_path = env::current_exe().expect("Failed to get executable path");
    let node_dir = exe_path.parent().expect("Failed to get parent directory");
    
    // 读取配置文件
    let config_path = node_dir.join("config.json");
    let config_str = fs::read_to_string(&config_path)
        .unwrap_or_else(|e| {
            eprintln!("Failed to read config file: {}", e);
            std::process::exit(1);
        });
    
    let config: serde_json::Value = serde_json::from_str(&config_str)
        .unwrap_or_else(|e| {
            eprintln!("Failed to parse config: {}", e);
            std::process::exit(1);
        });

    // 从命令行参数获取输入数据
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        let error_packet = OutputPacket::error("no input");
        println!("{}", serde_json::to_string(&error_packet).unwrap());
        std::process::exit(1);
    }

    let input_str = &args[1];
    
    // 解析输入数据
    let input_data: serde_json::Value = match serde_json::from_str(input_str) {
        Ok(data) => data,
        Err(e) => {
            let error_packet = OutputPacket::error(&format!("Invalid JSON input: {}", e));
            println!("{}", serde_json::to_string(&error_packet).unwrap());
            std::process::exit(1);
        }
    };

    // 调用处理函数
    let result = process(&input_data);

    // 构建输出数据包
    let output_type = config["output_type"].as_str().unwrap_or("");
    
    // 如果需要添加 type 字段
    if !output_type.is_empty() {
        let mut output_json = serde_json::to_value(OutputPacket::success(result)).unwrap();
        if let Some(obj) = output_json.as_object_mut() {
            obj.insert("type".to_string(), serde_json::Value::String(output_type.to_string()));
        }
        println!("{}", serde_json::to_string(&output_json).unwrap());
    } else {
        println!("{}", serde_json::to_string(&OutputPacket::success(result)).unwrap());
    }
}

/// 节点核心处理逻辑
/// 
/// # 参数
/// * `data` - 输入的 JSON 数据
/// 
/// # 返回
/// 处理后的数据（Option<serde_json::Value>）
/// 
/// # 示例
/// ```rust
/// // 在此实现你的业务逻辑
/// fn process(data: &serde_json::Value) -> Option<serde_json::Value> {
///     // 提取数据字段
///     let input = data.get("data")?;
///     
///     // 进行处理...
///     // 例如：数据转换、计算、API 调用等
///     
///     Some(processed_result)
/// }
/// ```
fn process(data: &serde_json::Value) -> Option<serde_json::Value> {
    // TODO: 在此实现你的业务逻辑
    // 默认返回输入数据中的 data 字段
    data.get("data").cloned()
}
