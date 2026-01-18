#!/usr/bin/env python3
"""
项目完整性检查脚本
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def check_imports():
    """检查所有核心模块导入"""
    print("🔍 检查模块导入...")
    
    try:
        from src.utils import (
            get_config, 
            setup_logger, 
            SHENWAN_L1_INDUSTRIES,
            DEFAULT_BENCHMARK
        )
        print("  ✅ utils 模块")
    except Exception as e:
        print(f"  ❌ utils 模块: {e}")
        return False
        
    try:
        from src.data import (
            get_db_manager,
            RawData,
            CalculatedIndicator,
            IndustryScore
        )
        print("  ✅ data 模块")
    except Exception as e:
        print(f"  ❌ data 模块: {e}")
        return False
        
    try:
        from src.core import (
            IndicatorCalculator,
            ScoringEngine,
            DataService,
            BacktestEngine,
            DataScheduler
        )
        print("  ✅ core 模块")
    except Exception as e:
        print(f"  ❌ core 模块: {e}")
        return False
        
    try:
        from src.cli import cli
        print("  ✅ CLI 模块")
    except Exception as e:
        print(f"  ❌ CLI 模块: {e}")
        return False
    
    print("  ✅ UI 模块 (跳过 streamlit 检查)")
    
    return True

def check_config_files():
    """检查配置文件"""
    print("\n🔍 检查配置文件...")
    
    config_files = [
        "config/config.yaml.example",
        "config/scoring_weights.yaml",
        "config/industry_qualitative.yaml",
        ".env.example"
    ]
    
    all_exist = True
    for config_file in config_files:
        path = Path(config_file)
        if path.exists():
            print(f"  ✅ {config_file}")
        else:
            print(f"  ❌ {config_file} 不存在")
            all_exist = False
    
    return all_exist

def check_code_structure():
    """检查代码结构"""
    print("\n🔍 检查代码结构...")
    
    required_dirs = [
        "src/utils",
        "src/data",
        "src/core",
        "src/cli",
        "src/ui",
        "config",
        "docs",
        "scripts"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ❌ {dir_path}/ 不存在")
            all_exist = False
    
    return all_exist

def check_syntax():
    """检查Python语法"""
    print("\n🔍 检查Python语法...")
    
    import py_compile
    
    py_files = list(Path("src").rglob("*.py"))
    py_files.extend(list(Path("scripts").rglob("*.py")))
    py_files.append(Path("main.py"))
    
    errors = []
    for py_file in py_files:
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append((py_file, e))
    
    if errors:
        print(f"  ❌ 发现 {len(errors)} 个语法错误:")
        for file, error in errors:
            print(f"     {file}: {error}")
        return False
    else:
        print(f"  ✅ 所有 {len(py_files)} 个文件语法正确")
        return True

def main():
    print("=" * 60)
    print("Industry Screener - 项目完整性检查")
    print("=" * 60)
    
    checks = [
        ("模块导入", check_imports),
        ("配置文件", check_config_files),
        ("代码结构", check_code_structure),
        ("语法检查", check_syntax)
    ]
    
    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
    
    print("\n" + "=" * 60)
    print("检查结果总结")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:15} {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 所有检查通过!项目状态正常。")
        return 0
    else:
        print("\n⚠️ 部分检查失败,请检查上述错误。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
