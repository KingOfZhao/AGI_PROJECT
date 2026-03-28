#!/bin/bash
# AMD GPU Kernel Challenge 参赛推演启动脚本
# 一键启动本地模型进行优化方案推演
# 作者: Zhao Dylan
# 日期: 2026-03-24

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="/Users/administruter/Desktop/AGI_PROJECT"
cd "$PROJECT_DIR"

# 打印带颜色的标题
print_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}AMD GPU Kernel Challenge 参赛推演启动器${NC}              ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  竞赛: AMD Developer Challenge February 2026            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  硬件: AMD Instinct MI355X (CDNA4, gfx950)             ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  参赛者: Zhao Dylan                                     ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}[1/5]${NC} 检查依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python3 未安装${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python3: $(python3 --version)${NC}"
    
    # 检查Ollama
    if ! command -v ollama &> /dev/null; then
        echo -e "${YELLOW}⚠ Ollama 未安装，将无法使用本地模型${NC}"
        echo -e "${YELLOW}  安装命令: brew install ollama${NC}"
    else
        echo -e "${GREEN}✓ Ollama 已安装${NC}"
        
        # 检查模型
        if ollama list | grep -q "qwen2.5-coder:14b"; then
            echo -e "${GREEN}✓ Qwen2.5-Coder:14b 模型已安装${NC}"
        else
            echo -e "${YELLOW}⚠ Qwen2.5-Coder:14b 模型未安装${NC}"
            echo -e "${YELLOW}  正在拉取模型...${NC}"
            ollama pull qwen2.5-coder:14b
        fi
    fi
    
    # 检查数据库
    if [ -f "$PROJECT_DIR/memory.db" ]; then
        echo -e "${GREEN}✓ 数据库文件存在${NC}"
    else
        echo -e "${YELLOW}⚠ 数据库文件不存在，将自动创建${NC}"
    fi
    
    echo ""
}

# 显示菜单
show_menu() {
    echo -e "${BLUE}[2/5]${NC} 选择推演模式:"
    echo ""
    echo -e "  ${GREEN}1)${NC} MXFP4 GEMM 优化推演 (当前: 24.016µs, 目标: 8.094µs)"
    echo -e "  ${GREEN}2)${NC} MLA Decode 优化推演 (当前: 223.601µs, 目标: 32.972µs)"
    echo -e "  ${GREEN}3)${NC} MXFP4 MoE 优化推演 (当前: 185.393µs, 目标: 109.793µs)"
    echo -e "  ${GREEN}4)${NC} 全部算子推演 (推荐)"
    echo -e "  ${GREEN}5)${NC} 仅注入AMD知识节点"
    echo -e "  ${GREEN}6)${NC} 退出"
    echo ""
    echo -ne "${CYAN}请选择 [1-6]:${NC} "
}

# 选择推演轮次
select_rounds() {
    echo ""
    echo -e "${BLUE}[3/5]${NC} 选择推演轮次:"
    echo ""
    echo -e "  ${GREEN}1)${NC} 快速推演 (1轮) - 快速验证"
    echo -e "  ${GREEN}2)${NC} 标准推演 (3轮) - 推荐"
    echo -e "  ${GREEN}3)${NC} 深度推演 (5轮) - 全面分析"
    echo -e "  ${GREEN}4)${NC} 极限推演 (10轮) - 最详细"
    echo ""
    echo -ne "${CYAN}请选择 [1-4]:${NC} "
}

# 执行推演
run_reasoning() {
    local kernel=$1
    local rounds=$2
    
    echo ""
    echo -e "${BLUE}[4/5]${NC} 启动推演..."
    echo -e "${YELLOW}算子: $kernel${NC}"
    echo -e "${YELLOW}轮次: $rounds${NC}"
    echo ""
    
    # 执行Python脚本
    python3 amd_race_launcher.py --kernel "$kernel" --rounds "$rounds"
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ 推演完成!${NC}"
    else
        echo ""
        echo -e "${RED}✗ 推演失败 (退出码: $exit_code)${NC}"
        exit $exit_code
    fi
}

# 显示结果
show_results() {
    echo ""
    echo -e "${BLUE}[5/5]${NC} 推演结果:"
    echo ""
    
    # 查找最新的推演结果
    local result_dir="$PROJECT_DIR/docs/AMD_推演结果"
    if [ -d "$result_dir" ]; then
        echo -e "${GREEN}📁 结果目录:${NC} $result_dir"
        echo ""
        
        # 列出最新的文件
        echo -e "${CYAN}最新生成的文件:${NC}"
        ls -lt "$result_dir" | head -n 6 | tail -n 5 | awk '{print "  - " $9}'
        echo ""
        
        # 统计节点数
        local db_path="$PROJECT_DIR/memory.db"
        if [ -f "$db_path" ]; then
            local node_count=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM proven_nodes WHERE domain IN ('gpu_kernel_optimization', 'code_implementation')" 2>/dev/null || echo "0")
            echo -e "${GREEN}💾 数据库节点数:${NC} $node_count 个 (GPU优化相关)"
        fi
        
        echo ""
        echo -e "${CYAN}下一步操作:${NC}"
        echo -e "  1. 查看优化清单: ${YELLOW}cat $result_dir/*_checklist.md${NC}"
        echo -e "  2. 查看详细结果: ${YELLOW}cat $result_dir/*.json | jq${NC}"
        echo -e "  3. 实现优化代码并测试"
        echo -e "  4. 提交到AMD Leaderboard"
    else
        echo -e "${YELLOW}⚠ 结果目录不存在${NC}"
    fi
    
    echo ""
}

# 主函数
main() {
    print_header
    check_dependencies
    
    # 显示菜单并获取选择
    show_menu
    read choice
    
    case $choice in
        1)
            kernel="mxfp4_gemm"
            ;;
        2)
            kernel="mla_decode"
            ;;
        3)
            kernel="mxfp4_moe"
            ;;
        4)
            kernel="all"
            ;;
        5)
            echo ""
            echo -e "${BLUE}[4/5]${NC} 注入AMD知识节点..."
            python3 amd_race_launcher.py --inject-nodes
            echo ""
            echo -e "${GREEN}✓ 知识节点注入完成!${NC}"
            echo ""
            exit 0
            ;;
        6)
            echo ""
            echo -e "${CYAN}再见!${NC}"
            echo ""
            exit 0
            ;;
        *)
            echo ""
            echo -e "${RED}✗ 无效选择${NC}"
            echo ""
            exit 1
            ;;
    esac
    
    # 选择轮次
    select_rounds
    read rounds_choice
    
    case $rounds_choice in
        1)
            rounds=1
            ;;
        2)
            rounds=3
            ;;
        3)
            rounds=5
            ;;
        4)
            rounds=10
            ;;
        *)
            echo ""
            echo -e "${RED}✗ 无效选择，使用默认值 (3轮)${NC}"
            rounds=3
            ;;
    esac
    
    # 执行推演
    run_reasoning "$kernel" "$rounds"
    
    # 显示结果
    show_results
    
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}推演完成! 祝您在AMD挑战赛中取得好成绩!${NC}              ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 运行主函数
main
